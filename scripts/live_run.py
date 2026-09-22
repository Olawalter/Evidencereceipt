#!/usr/bin/env python3
"""Run EvidenceReceipt on GenLayer StudioNet with real transactions.

    python scripts/live_run.py <address> --raw-base <url> --phase cases
    python scripts/live_run.py <address> --raw-base <url> --phase full

--raw-base is a commit-pinned https://raw.githubusercontent.com/.../fixtures/
URL, so every validator retrieves exactly the committed bytes.

cases: the diagnostic pass. The three policies are created, every catalogue
       case is requested and verified once, and each round's per-node stdout
       ([DISAGREE], [MINE], [DOWNGRADE]) is recorded. Written to
       deploy/diagnostics/.
full:  the live run of record. The same cases, plus the same source read as
       DYNAMIC, a recheck of the unavailable source (and a refused second
       recheck), refusals sent as real transactions, finalization after the
       recheck window, and a re-verification that keeps the first receipt.
       Written to deploy/live_run_transcript.json.

Code-decided outcomes are asserted: the run stops if one differs. Panel-decided
outcomes are recorded with held=true/false and never stop the run. Every
transaction hash is saved before its receipt is awaited, so an interrupted run
resumes without resending anything. Keys come from .data/demo_wallets.json
(gitignored) and are never printed. No method is payable.
"""

from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import studionet_transport  # noqa: E402,F401 - retries RPC transport failures
from genlayer_py import create_account, create_client  # noqa: E402
from genlayer_py.chains import studionet  # noqa: E402
from genlayer_py.types import TransactionStatus  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"
KEYS = ROOT / ".data" / "demo_wallets.json"
RPC = "https://studio.genlayer.com/api"
WAIT = dict(interval=5000, retries=360)
GEN = 10 ** 18
FINALITY_DELAY = 900
T: dict = {}
OUT = ROOT / "deploy" / "live_run_transcript.json"

META = json.loads((FIXTURES / "policies.json").read_text(encoding="utf-8"))
POLICIES = META["policies"]
HASHES = META["hashes"]
CASES = {}
for _name in ("certification_claims.json", "license_claims.json", "api_capability_claims.json",
              "adversarial_sources.json"):
    for _case in json.loads((FIXTURES / _name).read_text(encoding="utf-8"))["cases"]:
        CASES[_case["case_id"]] = _case
CODE_REASONS = ("SOURCE_ADDRESSES_VERIFIER", "SOURCE_NOT_FOUND", "SOURCE_FORBIDDEN",
                "SOURCE_SERVER_ERROR", "SOURCE_TIMEOUT", "SOURCE_REDIRECTED",
                "SOURCE_INVALID_CONTENT", "SOURCE_UNSUPPORTED_CONTENT")


def log(*parts):
    print(*parts, flush=True)


def save():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(T, indent=2, sort_keys=True, default=str) + "\n",
                   encoding="utf-8", newline="\n")


def die(message: str):
    log("FATAL:", message)
    T["fatal"] = message
    save()
    raise SystemExit(1)


def check(condition, message: str):
    if not condition:
        die(message)


def retry(action, attempts=8, pause=20):
    last = None
    for attempt in range(attempts):
        try:
            return action()
        except Exception as err:          # noqa: BLE001 - transport errors vary
            last = err
            log(f"    transient ({attempt + 1}/{attempts}): {str(err)[:120]}")
            time.sleep(pause)
    raise last


def now_iso(offset: int = 0) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + offset))


def epoch(iso: str) -> int:
    return calendar.timegm(time.strptime(iso, "%Y-%m-%dT%H:%M:%SZ"))


def wait_until(iso: str, why: str, margin: int = 30):
    remaining = epoch(iso) + margin - int(time.time())
    if remaining > 0:
        log(f"  waiting {remaining}s {why}")
        time.sleep(remaining)


def rpc(method: str, params: list):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    request = urllib.request.Request(RPC, data=body, headers={
        "Content-Type": "application/json", "User-Agent": "evidence-receipt-live-run"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode())


def node_lines(tx: str) -> list:
    """Each node's model, vote and stdout tail for one transaction."""
    try:
        result = retry(lambda: rpc("eth_getTransactionByHash", [tx]))["result"]
    except Exception:                     # noqa: BLE001
        return []
    cd = result.get("consensus_data") or {}
    out = []
    for n in (cd.get("leader_receipt") or [])[:1] + (cd.get("validators") or []):
        nc = n.get("node_config") or {}
        out.append({"mode": n.get("mode"), "model": (nc.get("primary_model") or {}).get("model"),
                    "vote": (cd.get("votes") or {}).get(nc.get("address")),
                    "stdout": ((n.get("genvm_result") or {}).get("stdout") or "")[-900:]})
    return out


def leader_result(receipt) -> str:
    leader = receipt["consensus_data"]["leader_receipt"]
    entry = leader[0] if isinstance(leader, list) else leader
    return str(entry["execution_result"])


def votes(receipt) -> list:
    last_round = receipt.get("last_round") or {}
    named = last_round.get("validator_votes_name")
    if named:
        return [str(v) for v in named]
    mapping = (receipt.get("consensus_data") or {}).get("votes") or {}
    return [str(v).upper() for v in mapping.values()]


def accepted(receipt) -> bool:
    cast = [v.upper() for v in votes(receipt)]
    return sum(v.startswith("AGREE") for v in cast) > sum(v.startswith("DISAGREE") for v in cast)


def verify_fixtures(raw: str):
    """Every location a live round reads must serve exactly the local bytes."""
    for rel, digest in sorted(HASHES.items()):
        try:
            with urllib.request.urlopen(raw + rel, timeout=30) as response:
                body = response.read()
        except urllib.error.HTTPError as err:
            die(f"{raw + rel} is not reachable: {err}")
        check(hashlib.sha256(body).hexdigest() == digest,
              f"{raw + rel} does not serve the committed bytes")
    log(f"  verified {len(HASHES)} source locations against local bytes")


class Actor:
    def __init__(self, address: str, name: str, key: str):
        self.name = name
        self.address = address
        self.account = create_account(key)
        self.client = create_client(chain=studionet, account=self.account)
        self.wallet = self.account.address.lower()

    def read(self, fn: str, args: list):
        return retry(lambda: self.client.read_contract(address=self.address, function_name=fn,
                                                       args=args))

    def balance(self) -> int:
        return int(retry(lambda: self.client.get_balance(self.account.address)))

    def funded(self, at_least: int):
        balance = self.balance()
        if balance >= at_least:
            return
        log(f"  funding {self.name} from the faucet (balance {balance})")
        retry(lambda: self.client.fund_account(self.account.address, GEN))
        for _ in range(40):
            if self.balance() > balance:
                return
            time.sleep(5)
        die("the faucet did not fund " + self.name)

    def write(self, step: str, fn: str, args: list, expect: str = "SUCCESS", value: int = 0,
              attempts: int = 3) -> dict:
        """One transaction, recorded under a step name and never resent. A
        round the panel could not agree on is asked again: nothing it did
        applied, and the next round draws a different panel."""
        done = T.setdefault("steps", {})
        if step in done:
            return done[step]
        pending = T.setdefault("pending", {})
        record = {}
        for attempt in range(attempts):
            if step in pending:
                tx = pending[step]
                log(f"  {self.name}.{fn} resuming {tx}")
            else:
                if value:
                    self.funded(value * 2)
                tx = retry(lambda: self.client.write_contract(
                    address=self.address, function_name=fn, args=args, value=value,
                    consensus_max_rotations=3))
                tx = tx if isinstance(tx, str) else tx.hex()
                pending[step] = tx
                save()
                log(f"  {self.name}.{fn} tx {tx}")
            receipt = retry(lambda: self.client.wait_for_transaction_receipt(
                transaction_hash=tx, status=TransactionStatus.FINALIZED, **WAIT))
            result = leader_result(receipt)
            record = {"step": step, "actor": self.name, "method": fn, "tx": tx,
                      "status": str(receipt.get("status_name") or receipt.get("status")),
                      "leader_execution": result, "votes": votes(receipt),
                      "accepted": accepted(receipt)}
            leader = receipt["consensus_data"]["leader_receipt"]
            payload = (leader[0].get("result") or {}).get("payload") \
                if isinstance(leader, list) else None
            if payload is not None:
                record["returned"] = str(payload)[:300]
            if value:
                record["value_atto"] = str(value)
            log(f"    {record['status']} leader {result} votes {record['votes']}")
            del pending[step]
            save()
            if expect != "SUCCESS" or result != "SUCCESS" or record["accepted"]:
                break
            T.setdefault("rejected_rounds", []).append(dict(record, nodes=node_lines(tx)))
            log(f"    the panel did not agree ({attempt + 1}/{attempts}); asking again")
            save()
        done[step] = record
        save()
        check(record["leader_execution"] == expect,
              f"{step}: leader execution {record['leader_execution']}, expected {expect}")
        check(expect != "SUCCESS" or record["accepted"],
              f"{step}: the panel did not agree after {attempts} rounds")
        return record


def actors(address: str) -> dict:
    keys = json.loads(KEYS.read_text(encoding="utf-8"))
    return {name: Actor(address, name, key) for name, key in keys.items()}


def policy_json(name: str) -> str:
    data = json.loads(json.dumps(POLICIES[name]))
    # the policy's own windows stand, except the recheck delay a live run waits out
    data["finality_delay_seconds"] = FINALITY_DELAY
    return json.dumps(data)


def policy(ac: dict, name: str) -> str:
    ids = T.setdefault("policies", {})
    owner = ac["owner"]
    if name not in ids:
        before = owner.read("list_policies", [0, 50])["total"]
        owner.write("create:" + name, "create_policy", [policy_json(name)])
        page = owner.read("list_policies", [0, 50])
        check(page["total"] == before + 1, "create_policy did not add a policy")
        ids[name] = page["items"][-1]
        save()
    return ids[name]


def request_id_of(ac: dict, pid: str, claim: str, url: str) -> str:
    page = ac["stranger"].read("list_requests", [pid, 0, 50])
    for rid in reversed(page["items"]):
        req = ac["stranger"].read("get_request", [rid])
        if req["claim"] == claim and req["source_url"] == url:
            return rid
    die("no request found for " + claim[:40])


def outcome(ac: dict, key: str, vid: str, expected: list, tx: str) -> dict:
    if key in T.get("outcomes", {}):
        return T["outcomes"][key]
    r = ac["stranger"].read("get_receipt", [vid])
    got = [r["final_result"], r["support_level"], r["reason_code"]]
    code = expected[2] in CODE_REASONS
    held = got == expected
    row = {"verification_id": vid, "request_id": r["request_id"], "tx": tx,
           "expected": expected, "observed": got, "decided_by": "CODE" if code else "PANEL",
           "held": held, "source_status": r["source_status"], "http_status": r["http_status"],
           "content_digest": r["content_digest"], "markers": r["markers"],
           "source_shape": r["source_shape"]["state"],
           "components": [[c["component_id"], c["state"], c["by"]] for c in r["components"]],
           "freshness": r["freshness"], "evidence_found": r["evidence_found"],
           "relevant_excerpt": r["relevant_excerpt"], "record_digest": r["record_digest"]}
    if not held:
        row["nodes"] = node_lines(tx)
    T.setdefault("outcomes", {})[key] = row
    save()
    log(f"  {key}: {' / '.join(got)} ({row['decided_by']}) held={held}")
    if code and not held:
        die(f"{key}: code-decided outcome {got}, expected {expected}")
    return r


def ask(ac: dict, key: str, case_id: str, raw: str, claim: str = None,
        stability: str = None) -> str:
    c = CASES[case_id]
    pid = T["policies"][c["policy"]]
    who = ac[c["requester"]]
    claim = claim or c["claim"]
    url = raw + "sources/" + c["source"]
    phash = ac["stranger"].read("get_policy", [pid])["policy_hash"]
    who.write("request:" + key, "request_verification",
              [pid, phash, claim, c["claim_context"], url, stability or c["stability"]])
    rid = request_id_of(ac, pid, claim, url)
    T.setdefault("requests", {})[key] = rid
    save()
    return rid


def run_case(ac: dict, key: str, case_id: str, raw: str, **kwargs) -> str:
    rid = ask(ac, key, case_id, raw, **kwargs)
    who = ac[CASES[case_id]["requester"]]
    step = who.write("verify:" + key, "verify", [rid])
    vid = ac["stranger"].read("get_request", [rid])["standing_id"]
    outcome(ac, key, vid, CASES[case_id]["expected"], step["tx"])
    return rid


def refusals(ac: dict, raw: str):
    """Real transactions the contract must refuse, each with its sentence."""
    reqs = T["requests"]
    stranger = ac["stranger"]
    cert = T["policies"]["certification"]
    phash = stranger.read("get_policy", [cert])["policy_hash"]
    nw = raw + "sources/cert/registry-northwind.html"
    tries = [
        ("refuse:stranger_verifies", stranger, "verify", [reqs["CE02"]],
         "only the requester or the policy owner runs a verification"),
        ("refuse:verify_twice", ac["alice"], "verify", [reqs["CE01"]],
         "only a CREATED or REVERIFY_REQUESTED request awaits verification"),
        ("refuse:duplicate_request", ac["bob"], "request_verification",
         [cert, phash, CASES["CE01"]["claim"], "", nw, "STABLE"], "duplicate verification"),
        ("refuse:invalid_policy_version", ac["bob"], "request_verification",
         [cert, "0" * 64, "A claim about a register.", "", nw, "STABLE"],
         "invalid policy version"),
        ("refuse:private_network_url", ac["bob"], "request_verification",
         [cert, phash, "A claim about a register.", "", "https://192.168.1.10/register",
          "STABLE"], "not an IP literal"),
        ("refuse:non_https_url", ac["bob"], "request_verification",
         [cert, phash, "A claim about a register.", "", "http://example.org/register",
          "STABLE"], "url must use https"),
        ("refuse:stranger_retires_policy", stranger, "retire_policy", [cert],
         "only the policy owner retires it"),
    ]
    # the finalize refusal needs a request whose recheck window is still open now
    open_now = [rid for rid in reqs.values()
                if stranger.read("get_request", [rid])["status"] == "EVALUATED"
                and epoch(stranger.read("get_request", [rid])["settle_at"]) > time.time() + 180]
    if open_now:
        tries.append(("refuse:finalize_inside_window", stranger, "finalize", [open_now[-1]],
                      "the recheck window is open until"))
    else:
        T.setdefault("notes", []).append("no request had an open recheck window when the "
                                         "refusals ran; the finalize-inside-window refusal is "
                                         "covered by the Direct Mode suite only")
    held = []
    for step, who, fn, args, sentence in tries:
        record = who.write(step, fn, args, expect="ERROR")
        check(sentence in record.get("returned", ""), f"{step}: refusal said {record}")
        held.append(step)
    T["refusals"] = held
    save()
    log(f"  {len(held)} refusals held")


def recheck_demo(ac: dict):
    """The requester rechecks one evaluated request once; a second recheck is
    refused; the replaced receipt stays readable."""
    rid = T["requests"]["LI04"]
    who = ac[CASES["LI04"]["requester"]]
    # on a resume the recheck already ran: use the receipt it replaced, as recorded
    before = T.get("recheck", {}).get("replaced")
    if not before:
        before = ac["stranger"].read("get_request", [rid])["standing_id"]
    T["recheck"] = {"replaced": before}
    save()
    step = who.write("recheck:LI04", "recheck", [rid])
    after = ac["stranger"].read("get_request", [rid])["standing_id"]
    outcome(ac, "LI04:recheck", after, CASES["LI04"]["expected"], step["tx"])
    check(ac["stranger"].read("get_receipt", [before])["state"] == "SUPERSEDED_BY_RECHECK",
          "the rechecked receipt was not kept as superseded")
    who.write("refuse:second_recheck", "recheck", [rid], expect="ERROR")
    T["recheck"] = {"replaced": before, "standing": after}
    save()


def settle(ac: dict, keys=None, suffix: str = ""):
    stranger = ac["stranger"]
    keys = keys or sorted(T["requests"])
    settle_at = []
    for k in keys:
        req = stranger.read("get_request", [T["requests"][k]])
        if req["status"] == "EVALUATED":
            settle_at.append(epoch(req["settle_at"]))
    if settle_at:
        wait_until(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(max(settle_at))),
                   "for every recheck window to close")
    for k in keys:
        rid = T["requests"][k]
        if stranger.read("get_request", [rid])["status"] == "EVALUATED":
            stranger.write("finalize:" + k + suffix, "finalize", [rid])
        final = stranger.read("get_latest_receipt", [rid])
        T.setdefault("finalized", {})[k] = {
            "found": final["found"], "verification_id": final.get("verification_id", ""),
            "final_result": final.get("final_result", ""),
            "state": final.get("state", "")}
        save()


def reverification(ac: dict):
    """A finalized request opens a second verification event. The source is the
    same pinned bytes, so the new receipt carries the same digest; the first
    receipt stays final and both appear in the history."""
    rid = T["requests"]["CE01"]
    who = ac[CASES["CE01"]["requester"]]
    who.write("reverify:CE01", "request_reverification", [rid])
    step = who.write("verify:CE01:v2", "verify", [rid])
    vid = ac["stranger"].read("get_request", [rid])["standing_id"]
    outcome(ac, "CE01:v2", vid, CASES["CE01"]["expected"], step["tx"])
    settle(ac, ["CE01"], suffix=":v2")
    history = ac["stranger"].read("get_history", [rid])["items"]
    check(len(history) == 2 and [h["state"] for h in history] == ["FINALIZED", "FINALIZED"],
          f"history after re-verification: {history}")
    check(history[0]["content_digest"] == history[1]["content_digest"],
          "the same pinned bytes gave two digests")
    T["reverification"] = history
    save()


def main():
    global OUT
    parser = argparse.ArgumentParser()
    parser.add_argument("address")
    parser.add_argument("--raw-base", required=True)
    parser.add_argument("--phase", choices=("cases", "full"), required=True)
    parser.add_argument("--only", default="", help="cases phase: comma-separated case ids")
    parser.add_argument("--out", default="")
    args = parser.parse_args()
    raw = args.raw_base if args.raw_base.endswith("/") else args.raw_base + "/"
    if args.out:
        OUT = pathlib.Path(args.out)
    elif args.phase == "cases":
        OUT = ROOT / "deploy" / "diagnostics" / ("cases_" + args.address.lower()[:10] + ".json")
    if OUT.exists():
        T.update(json.loads(OUT.read_text(encoding="utf-8")))
    T.update({"address": args.address, "raw_base": raw, "phase": args.phase,
              "network": "studionet"})
    T.setdefault("started_at", now_iso())
    save()
    ac = actors(args.address)
    log("wallets:", ", ".join(f"{n} {a.wallet}" for n, a in ac.items()))
    verify_fixtures(raw)
    only = [c for c in args.only.split(",") if c]
    for name in POLICIES:
        policy(ac, name)
    for case_id in sorted(CASES):
        if only and case_id not in only:
            continue
        run_case(ac, case_id, case_id, raw)
    if args.phase == "full":
        # the same source read as DYNAMIC: its digest is recorded, not compared
        run_case(ac, "CE01:dynamic", "CE01", raw,
                 claim="Northwind Analytics Ltd is ISO/IEC 27001 certified for cloud data "
                       "analytics services.", stability="DYNAMIC")
        recheck_demo(ac)
        refusals(ac, raw)
        settle(ac)
        reverification(ac)
    outcomes = T.get("outcomes", {})
    T["summary"] = {"held": sorted(k for k, v in outcomes.items() if v["held"]),
                    "not_held": sorted(k for k, v in outcomes.items() if not v["held"])}
    T["finished_at"] = now_iso()
    save()
    log("DONE", json.dumps(T["summary"]))


if __name__ == "__main__":
    main()
