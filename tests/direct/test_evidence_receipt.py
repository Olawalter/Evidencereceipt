"""The happy paths and every catalogue case: each case runs through the real
contract and must derive exactly the final result, support level and reason
its catalogue entry expects, with the receipt that goes with it."""

import pytest

from tests.direct.support import (
    CASES, HASHES, answer_for, as_sender, captured_payload, component, create_policy,
    finalize_after_window, later, outcome, request, run_case, stage, verify, warp)

PANEL_CASES = sorted(c for c in CASES if CASES[c]["answer"] is not None)
CODE_CASES = sorted(c for c in CASES if CASES[c]["answer"] is None)


@pytest.mark.parametrize("case_id", PANEL_CASES)
def test_panel_case_derives_its_expected_outcome(court, direct_vm, case_id):
    _rid, receipt = run_case(court, direct_vm, case_id)
    assert outcome(receipt) == CASES[case_id]["expected"]
    assert receipt["panel_state"] == "ASSESSED"


@pytest.mark.parametrize("case_id", CODE_CASES)
def test_code_decided_case_never_asks_the_panel(court, direct_vm, case_id):
    """The panel is not mocked: a model call would fail the round."""
    c = CASES[case_id]
    policy_id = create_policy(court, direct_vm, c["policy"])
    request_id = request(court, direct_vm, policy_id, case_id)
    receipt = verify(court, direct_vm, request_id, None)
    assert outcome(receipt) == c["expected"]
    assert receipt["panel_state"] == "SKIPPED"
    assert all(x["by"] == "CODE" for x in receipt["components"])


def test_a_supported_receipt_carries_its_evidence_and_identity(court, direct_vm):
    request_id, receipt = run_case(court, direct_vm, "CE01")
    assert receipt["source_status"] == "RETRIEVED" and receipt["http_status"] == 200
    assert receipt["evidence_found"] is True
    assert receipt["source"]["raw_sha256"] == HASHES["sources/cert/registry-northwind.html"]
    assert len(receipt["content_digest"]) == 64
    assert receipt["source"]["title"] == \
        "Meridian Certification Registry - certificate MC-27001-4412"
    assert "Design and operation of cloud data analytics services" in \
        receipt["relevant_excerpt"]
    assert len(receipt["relevant_excerpt"]) <= 400
    assert component(receipt, "validity")["state"] == "EXPLICIT"
    assert receipt["policy_hash"] == court.get_policy(receipt["policy_id"])["policy_hash"]
    assert receipt["state"] == "EVALUATED"
    assert court.get_latest_receipt(request_id)["found"] is False


def test_the_digest_ignores_markup_and_is_stable_across_rounds(court, direct_vm, mod):
    _rid, first = run_case(court, direct_vm, "CE01")
    html = mod._normalize("<p>Status</p>\n\n<p>Valid</p>", True)
    assert html == "Status Valid"
    assert mod._normalize("<script>x=1</script><b>Status</b> Valid", True) == "Status Valid"
    request_id = request(court, direct_vm, first["policy_id"], "CE01", requester="bob",
                         claim="Northwind Analytics Ltd is ISO/IEC 27001 certified for cloud "
                               "data analytics.")
    second = verify(court, direct_vm, request_id, answer_for("CE01"))
    assert second["content_digest"] == first["content_digest"]


def test_finalize_after_the_window_and_read_the_final_receipt(court, direct_vm):
    request_id, receipt = run_case(court, direct_vm, "LI01")
    as_sender(direct_vm, "stranger")
    with direct_vm.expect_revert("the recheck window is open until"):
        court.finalize(request_id)
    assert finalize_after_window(court, direct_vm, request_id) == receipt["verification_id"]
    final = court.get_latest_receipt(request_id)
    assert final["state"] == "FINALIZED" and final["final_result"] == "SUPPORTED"
    assert final["freshness"] == {"required": True, "max_age_seconds": 365 * 86400,
                                  "outcome": "CURRENT", "stated_date": "2026-08-14"}
    status = court.get_verification_status(receipt["verification_id"])
    assert status["final"] is True and status["request_status"] == "FINALIZED"


def test_re_verification_adds_a_receipt_and_keeps_the_first(court, direct_vm):
    request_id, first = run_case(court, direct_vm, "AP01")
    finalize_after_window(court, direct_vm, request_id)
    as_sender(direct_vm, "alice")
    assert court.request_reverification(request_id) == "REVERIFY_REQUESTED"
    changed = (b"# Ledgerly API reference - v2.4\n\nOfficial documentation for the Ledgerly "
               b"payments API.\n\n## Webhooks\n\nSettlement webhooks were removed in v2.4 and "
               b"are no longer sent.\n")
    answer = answer_for("AP01")
    answer["subjects"]["feature"] = {"state": "CONTRADICTED", "quotes": [
        {"evidence_id": "S1", "text": "Settlement webhooks were removed in v2.4"}]}
    answer["subjects"]["behaviour"] = {"state": "ABSENT", "quotes": []}
    answer["subjects"]["version"] = {"state": "EXPLICIT", "quotes": [
        {"evidence_id": "S1", "text": "Ledgerly API reference - v2.4"}]}
    second = verify(court, direct_vm, request_id, answer,
                    override={"api/ledgerly-webhooks.md": changed})
    assert second["version"] == 2 and second["final_result"] == "CONTRADICTED"
    assert second["content_digest"] != first["content_digest"]
    finalize_after_window(court, direct_vm, request_id)
    kept = court.get_receipt(first["verification_id"])
    assert kept["final_result"] == "SUPPORTED" and kept["state"] == "FINALIZED"
    assert court.get_latest_receipt(request_id)["verification_id"] == \
        second["verification_id"]
    history = court.get_history(request_id)["items"]
    assert [(h["version"], h["final_result"], h["state"]) for h in history] == \
        [(1, "SUPPORTED", "FINALIZED"), (2, "CONTRADICTED", "FINALIZED")]


def test_a_recheck_replaces_the_standing_receipt_before_finality(court, direct_vm):
    policy_id = create_policy(court, direct_vm, "certification")
    request_id = request(court, direct_vm, policy_id, "CE01")
    down = verify(court, direct_vm, request_id, None,
                  skip=("cert/registry-northwind.html",))
    assert outcome(down) == ["UNAVAILABLE", "UNAVAILABLE", "SOURCE_NOT_FOUND"]
    as_sender(direct_vm, "alice")
    stage(direct_vm, answer_for("CE01"))
    recheck_id = court.recheck(request_id)
    rechecked = court.get_receipt(recheck_id)
    assert rechecked["final_result"] == "SUPPORTED"
    assert rechecked["recheck_of"] == down["verification_id"]
    assert court.get_receipt(down["verification_id"])["state"] == "SUPERSEDED_BY_RECHECK"
    finalize_after_window(court, direct_vm, request_id)
    assert court.get_latest_receipt(request_id)["verification_id"] == recheck_id


def test_views_read_one_receipt_field_group_at_a_time(court, direct_vm):
    _rid, receipt = run_case(court, direct_vm, "AP03")
    vid = receipt["verification_id"]
    assert court.get_claim(vid)["claim"] == CASES["AP03"]["claim"]
    assert court.get_source(vid)["source_status"] == "RETRIEVED"
    assert court.get_result(vid)["final_result"] == "SUPPORTED"
    assert court.get_support_level(vid)["support_level"] == "DIRECT"
    assert court.get_content_digest(vid)["content_digest"] == receipt["content_digest"]
    assert court.get_policy_hash(vid)["policy_version"] == 1
    assert court.get_verification_status(vid)["state"] == "EVALUATED"
    assert captured_payload(direct_vm)["source"]["content_type"] == "application/json"


def test_expired_windows_close_requests(court, direct_vm):
    policy_id = create_policy(court, direct_vm, "certification")
    request_id = request(court, direct_vm, policy_id, "CE01")
    warp(direct_vm, later(3 * 86400 + 1))
    as_sender(direct_vm, "alice")
    with direct_vm.expect_revert("the verification window closed at"):
        court.verify(request_id)
    as_sender(direct_vm, "stranger")
    assert court.expire_request(request_id) == "EXPIRED"
    again = request(court, direct_vm, policy_id, "CE01")
    assert again != request_id
