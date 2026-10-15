
from pathlib import Path
import sys

from rag.graph_workflow import prepare_answer


def test_settlement_mismatch_answer():
    state = {
        "question": "Why is a payment marked as SETTLEMENT_MISMATCH?",
        "retrieved_context": (
            "The settlement amount differs from the payment amount "
            "minus the refund amount."
        ),
        "answer": "",
        "status": "PENDING",
    }

    result = prepare_answer(state)

    assert result["status"] == "SUCCESS"
    assert "settlement amount" in result["answer"].lower()
    assert "refund amount" in result["answer"].lower()


def test_missing_payment_answer():
    state = {
        "question": "What does MISSING_PAYMENT mean?",
        "retrieved_context": (
            "An order exists, but no matching payment record is available."
        ),
        "answer": "",
        "status": "PENDING",
    }

    result = prepare_answer(state)

    assert result["status"] == "SUCCESS"
    assert "no matching payment record" in result["answer"].lower()


def test_unverified_rule_needs_review():
    state = {
        "question": "Explain an unknown reconciliation rule.",
        "retrieved_context": "Some unrelated documentation.",
        "answer": "",
        "status": "PENDING",
    }

    result = prepare_answer(state)

    assert result["status"] == "NEEDS_REVIEW"


def test_empty_context_returns_no_context():
    state = {
        "question": "Why did this payment fail?",
        "retrieved_context": "",
        "answer": "",
        "status": "PENDING",
    }

    result = prepare_answer(state)

    assert result["status"] == "NO_CONTEXT"
