
import json

from rag.approval_workflow import (
    prepare_proposal,
    evaluate_approval,
    create_incident_id,
    save_audit_record,
)


def make_state(
    incident_type="SETTLEMENT_MISMATCH",
    decision="",
):
    return {
        "incident_id": "SETTLEMENT_MISMATCH-ORD000907-PAY000724",
        "incident_type": incident_type,
        "proposed_action": "",
        "evidence": '{"order_id": "ORD000907"}',
        "approval_status": "NOT_STARTED",
        "human_decision": decision,
        "final_status": "PENDING",
        "message": "",
    }


def test_approve_does_not_execute_correction():
    state = make_state()
    state.update(prepare_proposal(state))
    state["human_decision"] = "APPROVE"

    result = evaluate_approval(state)

    assert result["approval_status"] == "APPROVED"
    assert result["final_status"] == "APPROVED_NOT_EXECUTED"


def test_reject_proposal():
    state = make_state()
    state.update(prepare_proposal(state))
    state["human_decision"] = "REJECT"

    result = evaluate_approval(state)

    assert result["approval_status"] == "REJECTED"
    assert result["final_status"] == "REJECTED"


def test_invalid_decision_keeps_proposal_pending():
    state = make_state()
    state.update(prepare_proposal(state))
    state["human_decision"] = "APROVE"

    result = evaluate_approval(state)

    assert result["approval_status"] == "PENDING_APPROVAL"
    assert result["final_status"] == "AWAITING_HUMAN"
    assert "Invalid decision" in result["message"]


def test_empty_decision_keeps_proposal_pending():
    state = make_state()
    state.update(prepare_proposal(state))

    result = evaluate_approval(state)

    assert result["approval_status"] == "PENDING_APPROVAL"
    assert result["final_status"] == "AWAITING_HUMAN"
    assert "Waiting for a human reviewer" in result["message"]


def test_unknown_incident_type_needs_review():
    state = make_state(incident_type="UNKNOWN_INCIDENT")

    result = prepare_proposal(state)

    assert result["approval_status"] == "NOT_REQUIRED"
    assert result["final_status"] == "NEEDS_REVIEW"


def test_incident_identifier_is_repeatable():
    incident = {
        "incident_type": "SETTLEMENT_MISMATCH",
        "order_id": "ORD000907",
        "payment_id": "PAY000724",
    }

    first_id = create_incident_id(incident)
    second_id = create_incident_id(incident)

    assert first_id == second_id
    assert first_id == "SETTLEMENT_MISMATCH-ORD000907-PAY000724"


def test_audit_record_is_appended(tmp_path, monkeypatch):
    import rag.approval_workflow as approval

    monkeypatch.setattr(approval, "AUDIT_DIR", tmp_path)
    monkeypatch.setattr(
        approval,
        "AUDIT_FILE",
        tmp_path / "approval_audit.jsonl",
    )

    record = {
        "incident_id": "TEST-001",
        "human_decision": "REJECT",
        "final_status": "REJECTED",
    }

    save_audit_record(record)

    audit_file = tmp_path / "approval_audit.jsonl"
    lines = audit_file.read_text(encoding="utf-8").splitlines()

    assert len(lines) == 1
    assert json.loads(lines[0]) == record
