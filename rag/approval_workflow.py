
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

import duckdb
from langgraph.graph import END, START, StateGraph


# --------------------------------------------------
# 1. Project paths
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "dev.duckdb"

AUDIT_DIR = PROJECT_ROOT / "metadata"
AUDIT_FILE = AUDIT_DIR / "approval_audit.jsonl"

PAGE_SIZE = 50


# --------------------------------------------------
# 2. Workflow state
# --------------------------------------------------

class ApprovalState(TypedDict):
    incident_id: str
    incident_type: str
    proposed_action: str
    evidence: str
    approval_status: str
    human_decision: str
    final_status: str
    message: str


# --------------------------------------------------
# 3. Read-only database functions
# --------------------------------------------------

def get_incident_types() -> list[dict]:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    connection = duckdb.connect(str(DB_PATH), read_only=True)

    try:
        rows = connection.execute("""
            SELECT incident_type, COUNT(*) AS incident_count
            FROM fct_reconciliation_incidents
            GROUP BY incident_type
            ORDER BY incident_type
        """).fetchall()

        return [
            {"incident_type": row[0], "count": row[1]}
            for row in rows
        ]
    finally:
        connection.close()


def get_incidents(incident_type: str) -> list[dict]:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    connection = duckdb.connect(str(DB_PATH), read_only=True)

    try:
        cursor = connection.execute(
            """
            SELECT *
            FROM fct_reconciliation_incidents
            WHERE incident_type = ?
            ORDER BY order_id
            """,
            [incident_type],
        )

        columns = [item[0] for item in cursor.description]

        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]
    finally:
        connection.close()


# --------------------------------------------------
# 4. Stable incident identifier
# --------------------------------------------------

def create_incident_id(incident: dict) -> str:
    incident_type = str(incident.get("incident_type", "UNKNOWN"))
    order_id = str(incident.get("order_id", "NO_ORDER"))
    payment_id = incident.get("payment_id")

    # Include payment ID where available to distinguish incidents.
    payment_part = str(payment_id) if payment_id else "NO_PAYMENT"

    return f"{incident_type}-{order_id}-{payment_part}"


# --------------------------------------------------
# 5. Prepare proposal
# --------------------------------------------------

def prepare_proposal(state: ApprovalState) -> dict:
    incident_type = state["incident_type"].upper()

    actions = {
        "SETTLEMENT_MISMATCH": (
            "Review payment, refund, and settlement records. "
            "Verify the settlement calculation before proposing a correction."
        ),
        "MISSING_PAYMENT": (
            "Investigate the order and payment references. "
            "Check payment ingestion and provider records before proposing a correction."
        ),
        "PAYMENT_AMOUNT_MISMATCH": (
            "Compare the order amount with the payment amount "
            "and verify both source records."
        ),
        "CURRENCY_MISMATCH": (
            "Verify the order and payment currencies against source records."
        ),
    }

    action = actions.get(incident_type)

    if not action:
        return {
            "proposed_action": "",
            "approval_status": "NOT_REQUIRED",
            "final_status": "NEEDS_REVIEW",
            "message": "No predefined action exists for this incident type.",
        }

    return {
        "proposed_action": action,
        "approval_status": "PENDING_APPROVAL",
        "final_status": "AWAITING_HUMAN",
        "message": (
            "Proposal prepared. No financial records have been modified."
        ),
    }


# --------------------------------------------------
# 6. Evaluate a human decision
# --------------------------------------------------

def evaluate_approval(state: ApprovalState) -> dict:
    decision = state["human_decision"].strip().upper()

    # Empty decision means the workflow is waiting for a reviewer.
    if not decision:
        return {
            "approval_status": state["approval_status"],
            "final_status": "AWAITING_HUMAN",
            "message": "Waiting for a human reviewer.",
        }

    # Only proposals awaiting approval can receive a decision.
    if state["approval_status"] != "PENDING_APPROVAL":
        return {
            "approval_status": state["approval_status"],
            "final_status": "NEEDS_REVIEW",
            "message": "No pending proposal is eligible for a decision.",
        }

    if decision == "APPROVE":
        return {
            "approval_status": "APPROVED",
            "final_status": "APPROVED_NOT_EXECUTED",
            "message": (
                "Proposal approved. The financial correction "
                "has NOT been executed."
            ),
        }

    if decision == "REJECT":
        return {
            "approval_status": "REJECTED",
            "final_status": "REJECTED",
            "message": (
                "Proposal rejected. No financial records were modified."
            ),
        }

    # Invalid input must preserve the pending approval state.
    return {
        "approval_status": "PENDING_APPROVAL",
        "final_status": "AWAITING_HUMAN",
        "message": "Invalid decision. Enter APPROVE or REJECT.",
    }


# --------------------------------------------------
# 7. Append to audit log
# --------------------------------------------------

def save_audit_record(record: dict) -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    with AUDIT_FILE.open("a", encoding="utf-8") as file:
        file.write(
            json.dumps(
                record,
                ensure_ascii=False,
                default=str,
            ) + "\n"
        )


# --------------------------------------------------
# 8. Build graph
# --------------------------------------------------

def build_approval_graph():
    workflow = StateGraph(ApprovalState)

    workflow.add_node("prepare_proposal", prepare_proposal)
    workflow.add_node("evaluate_approval", evaluate_approval)

    workflow.add_edge(START, "prepare_proposal")
    workflow.add_edge("prepare_proposal", "evaluate_approval")
    workflow.add_edge("evaluate_approval", END)

    return workflow.compile()


# --------------------------------------------------
# 9. Select an incident
# --------------------------------------------------

def select_incident() -> dict:
    types = get_incident_types()

    if not types:
        raise ValueError("No reconciliation incidents found.")

    print("\n--- INCIDENT TYPES ---")

    for index, item in enumerate(types, start=1):
        print(
            f"{index}. {item['incident_type']} "
            f"({item['count']} incidents)"
        )

    while True:
        type_choice = input(
            "\nSelect an incident type number: "
        ).strip()

        if type_choice.isdigit():
            type_index = int(type_choice) - 1

            if 0 <= type_index < len(types):
                break

        print("Invalid incident type number. Try again.")

    selected_type = types[type_index]["incident_type"]
    incidents = get_incidents(selected_type)

    if not incidents:
        raise ValueError("No incidents found for this type.")

    total_pages = (len(incidents) + PAGE_SIZE - 1) // PAGE_SIZE

    while True:
        page_input = input(
            f"Select page (1-{total_pages}): "
        ).strip()

        if page_input.isdigit():
            page = int(page_input)

            if 1 <= page <= total_pages:
                break

        print("Invalid page number. Try again.")

    start = (page - 1) * PAGE_SIZE
    page_incidents = incidents[start:start + PAGE_SIZE]

    print(
        f"\n--- {selected_type}: PAGE {page}/{total_pages} ---"
    )

    for index, incident in enumerate(page_incidents, start=1):
        print(
            f"{index}. Order: {incident.get('order_id')} | "
            f"Payment: {incident.get('payment_id')} | "
            f"Severity: {incident.get('incident_severity')}"
        )

    while True:
        incident_input = input(
            "\nSelect an incident number from this page: "
        ).strip()

        if incident_input.isdigit():
            incident_index = int(incident_input) - 1

            if 0 <= incident_index < len(page_incidents):
                return page_incidents[incident_index]

        print("Invalid incident number. Try again.")


# --------------------------------------------------
# 10. Main program
# --------------------------------------------------

if __name__ == "__main__":
    try:
        incident = select_incident()

        initial_state: ApprovalState = {
            "incident_id": create_incident_id(incident),
            "incident_type": str(
                incident.get("incident_type", "UNKNOWN")
            ),
            "proposed_action": "",
            "evidence": json.dumps(
                incident,
                indent=2,
                ensure_ascii=False,
                default=str,
            ),
            "approval_status": "NOT_STARTED",
            "human_decision": "",
            "final_status": "PENDING",
            "message": "",
        }

        app = build_approval_graph()

        # First invocation prepares the proposal.
        # The empty decision means the reviewer has not responded yet.
        proposal = app.invoke(initial_state)

        print("\n--- PROPOSAL ---")
        print("Incident ID:", proposal["incident_id"])
        print("Incident type:", proposal["incident_type"])
        print("Evidence:", proposal["evidence"])
        print("Proposed action:", proposal["proposed_action"])
        print("Approval:", proposal["approval_status"])
        print("Status:", proposal["final_status"])
        print("Message:", proposal["message"])

        if proposal["approval_status"] != "PENDING_APPROVAL":
            print("Manual investigation is required.")
            raise SystemExit(0)

        while True:
            decision = input(
                "\nEnter human decision (APPROVE/REJECT): "
            ).strip().upper()

            if decision in ("APPROVE", "REJECT"):
                break

            print("Invalid input. Enter APPROVE or REJECT.")

        # Evaluate only after a valid human decision is received.
        final_state = {
            **proposal,
            "human_decision": decision,
        }

        result = app.invoke(final_state)

        print("\n--- FINAL RESULT ---")
        print("Approval:", result["approval_status"])
        print("Status:", result["final_status"])
        print("Message:", result["message"])

        # Persist the final decision and supporting evidence.
        audit_record = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "incident_id": result["incident_id"],
            "incident_type": result["incident_type"],
            "proposed_action": result["proposed_action"],
            "human_decision": decision,
            "approval_status": result["approval_status"],
            "final_status": result["final_status"],
            "evidence": json.loads(result["evidence"]),
        }

        save_audit_record(audit_record)

        print("\n--- AUDIT LOG ---")
        print("Saved to:", AUDIT_FILE)
        print("Financial database remains read-only.")

    except (ValueError, FileNotFoundError) as exc:
        print(f"Workflow could not continue: {exc}")
        raise SystemExit(1)
