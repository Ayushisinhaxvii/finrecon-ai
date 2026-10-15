"""FINRECON AI: investigation chat and human approval workflow."""

import json
from datetime import datetime, timezone

import streamlit as st

from rag.approval_workflow import (
    create_incident_id,
    evaluate_approval,
    get_incident_types,
    get_incidents,
    prepare_proposal,
    save_audit_record,
)
from rag.mcp_agent import investigate_sync, generate_incident_proposal_sync


# ============================================================
# 1. SESSION STATE
# ============================================================


def initialise_state():
    st.session_state.setdefault("finrecon_chat", [])
    st.session_state.setdefault("finrecon_proposal", None)
    st.session_state.setdefault("finrecon_last_result", None)


# ============================================================
# 2. INVESTIGATION CHAT
# ============================================================


def investigate_question(question: str):
    """Run an investigation and retain the conversation."""
    cleaned_question = question.strip()
    if not cleaned_question:
        return

    with st.spinner("Investigating incident evidence..."):
        result = investigate_sync(cleaned_question)

    st.session_state["finrecon_chat"].append(
        {"role": "user", "content": cleaned_question}
    )

    answer = result.get("answer") or result.get("message") or "No answer was returned."
    st.session_state["finrecon_chat"].append(
        {
            "role": "assistant",
            "content": str(answer),
            "status": result.get("status", "UNKNOWN"),
            "tools": result.get("tools_available", []),
            "route": result.get("route", "UNKNOWN"),
        }
    )
    st.session_state["finrecon_last_result"] = result


def render_chat():
    st.markdown("### Chat with FINRECON AI")
    st.caption(
        "Ask questions about reconciliation incidents. FINRECON retrieves database "
        "evidence and can use Gemini to explain it; financial records are not changed."
    )

    for message in st.session_state["finrecon_chat"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                if message.get("status") == "ERROR":
                    st.warning("The investigation did not complete successfully.")
                if message.get("route"):
                    st.caption(f"Investigation route: {message['route']}")
                tools = message.get("tools", [])
                if tools:
                    st.caption("Tools used/available: " + ", ".join(tools))

    question = st.chat_input(
        "Ask about incidents, payments, or reconciliation...",
        key="finrecon_chat_input",
    )
    if question:
        try:
            investigate_question(question)
            st.rerun()
        except Exception as exc:
            st.error("The investigation failed. Check the terminal traceback.")
            st.exception(exc)

    if st.session_state["finrecon_chat"]:
        if st.button("Clear conversation", key="clear_finrecon_chat"):
            st.session_state["finrecon_chat"] = []
            st.session_state["finrecon_last_result"] = None
            st.rerun()


# ============================================================
# 3. INCIDENT SELECTION
# ============================================================


def render_incident_selection():
    st.markdown("### Incident investigation and approval")
    st.caption(
        "Select an incident, inspect its database evidence, generate an editable "
        "AI-assisted proposal, and record a human decision."
    )

    try:
        incident_types = get_incident_types()
    except Exception as exc:
        st.error("Could not load incident types from DuckDB.")
        st.exception(exc)
        return None

    if not incident_types:
        st.info("No reconciliation incidents are available.")
        return None

    type_names = [item["incident_type"] for item in incident_types]
    selected_type = st.selectbox(
        "Incident type", options=type_names, key="finrecon_incident_type"
    )

    try:
        incidents = get_incidents(selected_type)
    except Exception as exc:
        st.error("Could not load incidents.")
        st.exception(exc)
        return None

    if not incidents:
        st.info("No incidents were found for this type.")
        return None

    def incident_label(incident):
        return (
            f"Order {incident.get('order_id', 'N/A')} | "
            f"Payment {incident.get('payment_id') or 'N/A'} | "
            f"{incident.get('incident_severity', 'Severity unknown')}"
        )

    selected_index = st.selectbox(
        "Select incident",
        options=list(range(len(incidents))),
        format_func=lambda index: incident_label(incidents[index]),
        key="finrecon_incident_index",
    )
    incident = incidents[selected_index]

    with st.expander("Selected incident record", expanded=True):
        st.json(incident)

    return incident


# ============================================================
# 4. PREPARE AI-ASSISTED PROPOSAL
# ============================================================


def prepare_incident_proposal(incident: dict):
    """Retrieve evidence and prepare a human-review proposal; execute nothing."""
    with st.spinner("Retrieving incident evidence and preparing proposal..."):
        ai_result = generate_incident_proposal_sync(incident)

    # Preserve the selected incident and the actual evidence returned by the investigator.
    evidence_bundle = {
        "selected_incident": incident,
        "investigation_evidence": ai_result.get("tool_evidence", []),
        "investigation_route": ai_result.get("route", "UNKNOWN"),
        "investigation_status": ai_result.get("status", "UNKNOWN"),
    }
    proposed_action = str(ai_result.get("proposed_action") or "").strip()
    if not proposed_action:
        proposed_action = "Manual review required. No financial correction was executed."

    initial_state = {
        "incident_id": create_incident_id(incident),
        "incident_type": str(incident.get("incident_type", "UNKNOWN")),
        "proposed_action": proposed_action,
        "evidence": json.dumps(
            evidence_bundle, ensure_ascii=False, indent=2, default=str
        ),
        "approval_status": "NOT_STARTED",
        "human_decision": "",
        "final_status": "PENDING",
        "message": "",
    }

    proposal = prepare_proposal(initial_state)
    # Use the AI-generated action while retaining the existing approval state machine.
    proposal["proposed_action"] = proposed_action
    proposal["investigation_answer"] = str(ai_result.get("answer", ""))
    proposal["investigation_status"] = ai_result.get("status", "UNKNOWN")
    proposal["investigation_route"] = ai_result.get("route", "UNKNOWN")

    st.session_state["finrecon_proposal"] = {
        **initial_state,
        **proposal,
        "decision_recorded": False,
        "execution_status": "NOT_EXECUTED",
    }


# ============================================================
# 5. DISPLAY AND RECORD APPROVAL
# ============================================================


def render_proposal(incident: dict):
    proposal = st.session_state.get("finrecon_proposal")

    if not proposal:
        if st.button(
            "Investigate and prepare review proposal",
            type="primary",
            key="finrecon_prepare_proposal",
        ):
            try:
                prepare_incident_proposal(incident)
                st.rerun()
            except Exception as exc:
                st.error("Could not prepare the proposal.")
                st.exception(exc)
        return

    current_incident_id = create_incident_id(incident)
    if proposal["incident_id"] != current_incident_id:
        st.warning(
            "A proposal for another incident is currently in review. Finish it or "
            "discard it before reviewing a different incident."
        )
        if st.button("Discard current proposal", key="finrecon_discard_proposal"):
            st.session_state["finrecon_proposal"] = None
            st.rerun()
        return

    if proposal.get("decision_recorded"):
        st.markdown("#### Completed decision")
        st.success(f"Decision recorded: {proposal.get('approval_status', 'UNKNOWN')}")
        st.write("Incident ID:", proposal["incident_id"])
        st.write("Execution status:", proposal.get("execution_status", "NOT_EXECUTED"))
        st.info(
            proposal.get("message")
            or "The decision was recorded. No financial correction was executed."
        )
        if st.button("Start a new review", key="finrecon_new_review"):
            st.session_state["finrecon_proposal"] = None
            st.rerun()
        return

    st.markdown("#### AI investigation findings")
    st.caption(
        f"Status: {proposal.get('investigation_status', 'UNKNOWN')} · "
        f"Route: {proposal.get('investigation_route', 'UNKNOWN')}"
    )
    investigation_answer = proposal.get("investigation_answer", "")
    if investigation_answer:
        st.markdown(investigation_answer)
    else:
        st.warning("The investigator did not return an explanation. Review the evidence manually.")

    st.markdown("#### Review and edit proposal")
    st.write("Incident ID:", proposal["incident_id"])
    st.write("Incident type:", proposal["incident_type"])
    st.write("Approval status:", proposal.get("approval_status", "UNKNOWN"))
    st.warning("Approval records a human decision only. It does not execute a financial correction.")

    if proposal.get("approval_status") != "PENDING_APPROVAL":
        st.warning(
            proposal.get("message", "This proposal is not awaiting human approval.")
        )
        return

    edited_action = st.text_area(
        "Proposed action (editable)",
        value=proposal.get("proposed_action", ""),
        height=130,
        key=f"finrecon_action_{proposal['incident_id']}",
        help="Review and edit this action before submitting your decision.",
    )

    with st.expander("Evidence used for this proposal"):
        try:
            st.json(json.loads(proposal["evidence"]))
        except (ValueError, TypeError):
            st.text(proposal.get("evidence", ""))

    approve_col, reject_col = st.columns(2)
    with approve_col:
        approve_clicked = st.button(
            "Approve proposal",
            type="primary",
            use_container_width=True,
            key=f"finrecon_approve_{proposal['incident_id']}",
        )
    with reject_col:
        reject_clicked = st.button(
            "Reject proposal",
            use_container_width=True,
            key=f"finrecon_reject_{proposal['incident_id']}",
        )

    if not (approve_clicked or reject_clicked):
        return
    if not edited_action.strip():
        st.warning("The proposed action cannot be empty.")
        return

    decision = "APPROVE" if approve_clicked else "REJECT"
    decision_state = {
        **proposal,
        "proposed_action": edited_action.strip(),
        "human_decision": decision,
    }
    result = evaluate_approval(decision_state)
    if result.get("approval_status") not in {"APPROVED", "REJECTED"}:
        st.error(result.get("message", "The decision could not be recorded."))
        return

    try:
        evidence = json.loads(proposal["evidence"])
    except (ValueError, TypeError):
        st.error("Proposal evidence is invalid. The decision was not recorded.")
        return

    audit_record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "incident_id": proposal["incident_id"],
        "incident_type": proposal["incident_type"],
        "proposed_action": edited_action.strip(),
        "human_decision": decision,
        "approval_status": result["approval_status"],
        "final_status": result["final_status"],
        "message": result.get("message", ""),
        "evidence": evidence,
        "investigation_route": proposal.get("investigation_route", "UNKNOWN"),
        "execution_status": "NOT_EXECUTED",
    }

    try:
        save_audit_record(audit_record)
    except Exception as exc:
        st.error(
            "The audit record could not be saved. The interface will not mark "
            "this decision as recorded."
        )
        st.exception(exc)
        return

    st.session_state["finrecon_proposal"] = {
        **decision_state,
        **result,
        "decision_recorded": True,
        "execution_status": "NOT_EXECUTED",
    }
    st.rerun()


# ============================================================
# 6. MAIN INVESTIGATOR PAGE
# ============================================================


def render_investigator():
    """Render the investigation chat and human approval interface."""
    initialise_state()
    st.markdown(
        """
        <div class="hero">
            <div class="eyebrow">ASK · INVESTIGATE · REVIEW</div>
            <div class="hero-title">FINRECON AI Investigator</div>
            <div class="hero-copy">
                Investigate reconciliation incidents using verified database evidence,
                then review and edit proposals before recording human decisions.
            </div>
            <span class="hero-tag">READ-ONLY EVIDENCE · GEMINI · HUMAN REVIEW</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    chat_tab, review_tab = st.tabs(
        ["AI Investigation Chat", "Incident Review & Approval"]
    )
    with chat_tab:
        render_chat()
    with review_tab:
        incident = render_incident_selection()
        if incident is not None:
            render_proposal(incident)
