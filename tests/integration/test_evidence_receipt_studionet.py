"""StudioNet integration: the deployment of record in deploy/deployment.json,
checked over the network.

    python -m pytest tests/integration -v
    EVIDENCE_RECEIPT_LIVE_WRITES=1 python -m pytest tests/integration -v

Read-only by default: the deployed source is byte-identical to
contracts/evidence_receipt.py, the deployed schema exposes every public method
in that file, the views answer, and what the live run recorded reads back -
receipts, digests, policy hashes and the re-verification history. With
EVIDENCE_RECEIPT_LIVE_WRITES=1 one write goes through real consensus: a fresh
wallet creates a policy.
"""

import base64
import hashlib
import json
import os
import pathlib
import re
import sys
import time
import urllib.request

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "contracts" / "evidence_receipt.py"
RECORD = ROOT / "deploy" / "deployment.json"
TRANSCRIPT = ROOT / "deploy" / "live_run_transcript.json"
POLICIES = ROOT / "fixtures" / "policies.json"
RPC = "https://studio.genlayer.com/api"

pytestmark = pytest.mark.skipif(not RECORD.exists(), reason="no deployment recorded")
sys.path.insert(0, str(ROOT / "scripts"))


def rpc(method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    last = None
    for attempt in range(6):
        try:
            request = urllib.request.Request(RPC, data=body, headers={
                "Content-Type": "application/json", "User-Agent": "evidence-receipt-integration"})
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode())
        except Exception as err:          # noqa: BLE001 - transport errors vary
            last = err
            time.sleep(10 * (attempt + 1))
    raise last


@pytest.fixture(scope="module")
def deployment():
    return json.loads(RECORD.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def read(deployment):
    import studionet_transport  # noqa: F401
    from genlayer_py import create_account, create_client
    from genlayer_py.chains import studionet
    client = create_client(chain=studionet, account=create_account())
    return lambda fn, args: client.read_contract(
        address=deployment["contract_address"], function_name=fn, args=args)


@pytest.fixture(scope="module")
def transcript(deployment):
    if not TRANSCRIPT.exists():
        pytest.skip("no live run recorded")
    data = json.loads(TRANSCRIPT.read_text(encoding="utf-8"))
    if data.get("address", "").lower() != deployment["contract_address"].lower():
        pytest.skip("the transcript belongs to another deployment")
    return data


def test_deployed_source_is_the_committed_file(deployment):
    result = rpc("gen_getContractCode", [deployment["contract_address"]])["result"]
    deployed = result.encode() if result.lstrip().startswith("#") else base64.b64decode(result)
    local = CONTRACT.read_bytes()
    assert hashlib.sha256(deployed).hexdigest() == hashlib.sha256(local).hexdigest() \
        == deployment["source_sha256"]


def test_deployed_schema_exposes_every_public_method(deployment):
    schema = rpc("gen_getContractSchema", [deployment["contract_address"]])["result"]
    declared = re.findall(r"@gl\.public\.(?:view|write(?:\.payable)?)\n    def (\w+)\(",
                          CONTRACT.read_text(encoding="utf-8"))
    assert len(declared) == 25
    assert set(declared) <= set(schema["methods"])


def test_views_answer(read):
    config = read("get_config", [])
    assert config["contract_version"] == "0.1.0" and config["receipt_version"] == 1
    assert config["final_results"] == ["SUPPORTED", "PARTIALLY_SUPPORTED", "NOT_SUPPORTED",
                                       "CONTRADICTED", "UNAVAILABLE", "INCONCLUSIVE"]
    assert read("get_receipt", ["VE-999999"])["found"] is False


def test_the_live_receipts_read_back(read, transcript):
    assert transcript["outcomes"]
    for key, row in transcript["outcomes"].items():
        r = read("get_receipt", [row["verification_id"]])
        assert [r["final_result"], r["support_level"], r["reason_code"]] == row["observed"], key
        assert r["record_digest"] == row["record_digest"], key
        assert r["content_digest"] == row["content_digest"], key


def test_every_policy_hash_recomputes(read, transcript):
    for name, policy_id in transcript["policies"].items():
        view = read("get_policy", [policy_id])
        assert view["policy_hash"] == view["recomputed_hash"], name


def test_finalized_receipts_and_history_stand(read, transcript):
    for key, row in transcript.get("finalized", {}).items():
        rid = transcript["requests"][key]
        final = read("get_latest_receipt", [rid])
        assert final["found"] is True and final["state"] == "FINALIZED", key
    history = transcript.get("reverification")
    if history:
        items = read("get_history", [transcript["requests"]["CE01"]])["items"]
        assert [i["verification_id"] for i in items] == [h["verification_id"] for h in history]


@pytest.mark.skipif(os.environ.get("EVIDENCE_RECEIPT_LIVE_WRITES") != "1",
                    reason="writes to the deployment of record are opt-in")
def test_a_write_through_consensus(deployment):
    import studionet_transport  # noqa: F401
    from genlayer_py import create_account, create_client
    from genlayer_py.chains import studionet
    from genlayer_py.types import TransactionStatus
    writer = create_client(chain=studionet, account=create_account())
    spec = json.loads(POLICIES.read_text(encoding="utf-8"))["policies"]["api"]
    spec["name"] = "Integration test policy"
    before = writer.read_contract(address=deployment["contract_address"],
                                  function_name="list_policies", args=[0, 1])["total"]
    tx = writer.write_contract(address=deployment["contract_address"],
                               function_name="create_policy", args=[json.dumps(spec)],
                               consensus_max_rotations=3)
    receipt = writer.wait_for_transaction_receipt(
        transaction_hash=tx, status=TransactionStatus.FINALIZED, interval=5000, retries=240)
    leader = receipt["consensus_data"]["leader_receipt"]
    assert str((leader[0] if isinstance(leader, list) else leader)["execution_result"]) == \
        "SUCCESS"
    after = writer.read_contract(address=deployment["contract_address"],
                                 function_name="list_policies", args=[0, 1])["total"]
    assert after == before + 1
