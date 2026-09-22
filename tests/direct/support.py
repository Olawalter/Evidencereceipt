"""Shared scenario data and mock helpers for the Direct Mode suite.

The suite runs the real contract inside the official genlayer-test direct
runner (SDK resolved from the contract's own pinned runner hash). Only the
external boundaries are mocked, and narrowly:

- web fetches: every file under fixtures/sources is served at BASE + its
  relative path, byte for byte, with a content type by extension; a skipped
  or missing source answers 404 (NOT_FOUND); a URL nothing serves raises in the
  runner, which the contract records as TIMEOUT;
- the one panel prompt, matched on its header, answered with a JSON object.

Nothing in the contract is patched. Every source status, support level and
final result in this suite is produced by the contract's own code.
"""

import calendar
import copy
import json
import pathlib
import re
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTRACT = "contracts/evidence_receipt.py"
MODULE = "_contract_evidence_receipt"
FIXTURES = ROOT / "fixtures"

BASE = "https://sources.example.org/evidence-receipt/"
NOW = "2026-09-15T12:00:00Z"
PANEL_PATTERN = r"(?s)EvidenceReceipt panel"
TYPES = {".html": "text/html; charset=utf-8", ".md": "text/markdown; charset=utf-8",
         ".json": "application/json"}

WALLETS = json.loads((FIXTURES / "wallets.json").read_text(encoding="utf-8"))
META = json.loads((FIXTURES / "policies.json").read_text(encoding="utf-8"))
POLICIES = META["policies"]
HASHES = META["hashes"]
CASES = {}
for _name in ("certification_claims.json", "license_claims.json", "api_capability_claims.json",
              "adversarial_sources.json"):
    for _case in json.loads((FIXTURES / _name).read_text(encoding="utf-8"))["cases"]:
        CASES[_case["case_id"]] = _case


def wallet(name: str) -> str:
    return WALLETS[name]


def as_sender(direct_vm, name: str):
    direct_vm.sender = bytes.fromhex(WALLETS[name][2:])


def epoch(iso: str) -> int:
    return calendar.timegm(time.strptime(iso, "%Y-%m-%dT%H:%M:%SZ"))


def later(seconds: int, start: str = NOW) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch(start) + seconds))


def warp(direct_vm, timestamp: str):
    """Move the transaction clock. genlayer-test 0.29.2's warp() updates the
    VM's datetime but not the SDK's cached gl.message_raw; set both."""
    direct_vm.warp(timestamp)
    gl = sys.modules.get("genlayer.gl")
    if gl is not None and getattr(gl, "message_raw", None) is not None:
        gl.message_raw["datetime"] = timestamp


# -- policies and requests -----------------------------------------------------------

def policy(which: str, **overrides) -> dict:
    data = copy.deepcopy(POLICIES[which])
    data.update(overrides)
    return data


def create_policy(contract, direct_vm, which: str = "certification", owner: str = "owner",
                  **overrides) -> str:
    as_sender(direct_vm, owner)
    return contract.create_policy(json.dumps(policy(which, **overrides)))


def policy_hash(contract, policy_id: str) -> str:
    return contract.get_policy(policy_id)["policy_hash"]


def url_of(rel: str, base: str = BASE) -> str:
    return base + "sources/" + rel


def request(contract, direct_vm, policy_id: str, case_id: str, requester: str = None,
            **overrides) -> str:
    c = CASES[case_id]
    args = {"policy_hash": policy_hash(contract, policy_id), "claim": c["claim"],
            "claim_context": c["claim_context"], "source_url": url_of(c["source"]),
            "content_stability": c["stability"]}
    args.update(overrides)
    as_sender(direct_vm, requester or c["requester"])
    return contract.request_verification(policy_id, args["policy_hash"], args["claim"],
                                         args["claim_context"], args["source_url"],
                                         args["content_stability"])


# -- mocks ------------------------------------------------------------------------------

def serve(direct_vm, url: str, body: bytes, status: int = 200, content_type: str = None):
    headers = {} if content_type is None else {"content-type": content_type}
    direct_vm.mock_web("^" + re.escape(url) + "$", {
        "method": "GET", "response": {"status": status, "headers": headers, "body": body}})


MISSING = sorted({c["source"] for c in CASES.values() if c["source"].startswith("missing/")})


def serve_all(direct_vm, base: str = BASE, skip=(), override=None):
    """Every fixture source; a skipped or missing one answers 404, as a live
    host does. A URL nothing serves raises in the runner - no response - which
    the contract records as TIMEOUT."""
    override = override or {}
    for rel in list(skip) + MISSING:
        serve(direct_vm, base + "sources/" + rel, b"Not Found", status=404,
              content_type="text/plain")
    for path in sorted((FIXTURES / "sources").rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(FIXTURES / "sources").as_posix()
        if rel in skip:
            continue
        serve(direct_vm, base + "sources/" + rel, override.get(rel, path.read_bytes()),
              content_type=TYPES.get(path.suffix))


def mock_panel(direct_vm, answer):
    direct_vm.mock_llm(PANEL_PATTERN, answer if isinstance(answer, str) else json.dumps(answer))


def stage(direct_vm, answer=None, base: str = BASE, skip=(), override=None, extra=()):
    direct_vm.clear_mocks()
    for url, body, status, content_type in extra:
        serve(direct_vm, url, body, status, content_type)
    serve_all(direct_vm, base, skip, override)
    if answer is not None:
        mock_panel(direct_vm, answer)


def answer_for(case_id: str) -> dict:
    return copy.deepcopy(CASES[case_id]["answer"])


def verify(contract, direct_vm, request_id: str, answer=None, actor: str = None,
           **stage_kwargs) -> dict:
    stage(direct_vm, answer, **stage_kwargs)
    if actor is None:
        submitter = contract.get_request(request_id)["submitted_by"]
        direct_vm.sender = bytes.fromhex(submitter[2:])
    else:
        as_sender(direct_vm, actor)
    verification_id = contract.verify(request_id)
    return contract.get_receipt(verification_id)


def run_case(contract, direct_vm, case_id: str, policy_id: str = None) -> tuple:
    c = CASES[case_id]
    policy_id = policy_id or create_policy(contract, direct_vm, c["policy"])
    request_id = request(contract, direct_vm, policy_id, case_id)
    return request_id, verify(contract, direct_vm, request_id, answer_for(case_id))


def component(receipt: dict, component_id: str) -> dict:
    for c in receipt["components"]:
        if c["component_id"] == component_id:
            return c
    raise KeyError(component_id)


def outcome(receipt: dict) -> list:
    return [receipt["final_result"], receipt["support_level"], receipt["reason_code"]]


def finalize_after_window(contract, direct_vm, request_id: str, who: str = "stranger") -> str:
    settle = contract.get_request(request_id)["settle_at"]
    warp(direct_vm, later(1, settle))
    as_sender(direct_vm, who)
    return contract.finalize(request_id)


def captured_payload(direct_vm) -> dict:
    result, _leader_fn, _validator_fn = direct_vm._captured_validators[-1]
    return json.loads(result)


def captured_ctx(direct_vm) -> dict:
    _result, leader_fn, _validator_fn = direct_vm._captured_validators[-1]
    for cell in leader_fn.__closure__ or ():
        value = cell.cell_contents
        if isinstance(value, dict) and "subject_id" in value:
            return value
    raise AssertionError("round context not found")
