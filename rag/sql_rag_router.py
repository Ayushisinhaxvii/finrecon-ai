
import json
import sys
from pathlib import Path
from typing import TypedDict

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph

# --------------------------------------------------
# 1. Project paths and configuration
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "dev.duckdb"

load_dotenv(PROJECT_ROOT / ".env")


# --------------------------------------------------
# 2. Workflow state
# --------------------------------------------------

class RouterState(TypedDict):
    question: str
    route: str
    sql_result: str
    retrieved_context: str
    answer: str
    status: str
    requires_human_approval: bool
    structured_output: dict


# --------------------------------------------------
# 3. Classify the question
# --------------------------------------------------

def classify_question(state: RouterState) -> dict:
    question = state["question"].lower()

    sql_terms = [
        "how many", "count", "total", "amount", "sum",
        "which order", "payment_id", "order_id", "incident",
        "incidents", "reconciliation status", "severity",
        "show me", "list", "database", "records",
    ]

    rag_terms = [
        "why", "what does", "what is", "how should",
        "guideline", "rule", "meaning", "explain",
        "cause", "reason",
    ]

    needs_sql = any(term in question for term in sql_terms)
    needs_rag = any(term in question for term in rag_terms)

    if needs_sql and needs_rag:
        route = "BOTH"
    elif needs_sql:
        route = "SQL"
    else:
        route = "RAG"

    return {"route": route}


# --------------------------------------------------
# 4. Run predefined read-only SQL queries
# --------------------------------------------------

def query_database(question: str) -> str:
    # Import locally so other workflow functions remain
    # easy to test without opening the database.
    import duckdb

    q = question.lower()

    if not DB_PATH.exists():
        return f"ERROR: Database not found at {DB_PATH}"

    try:
        # Read-only prevents this workflow from modifying
        # financial tables.
        connection = duckdb.connect(
            str(DB_PATH),
            read_only=True,
        )

        try:
            if "incident" in q or "incidents" in q:
                if "severity" in q or "high" in q or "medium" in q:
                    sql = """
                        SELECT incident_severity, COUNT(*) AS incident_count
                        FROM fct_reconciliation_incidents
                        GROUP BY incident_severity
                        ORDER BY incident_severity
                    """
                elif (
                    "settlement_mismatch" in q
                    or "settlement mismatch" in q
                ):
                    sql = """
                        SELECT incident_type, COUNT(*) AS incident_count
                        FROM fct_reconciliation_incidents
                        WHERE incident_type = 'SETTLEMENT_MISMATCH'
                        GROUP BY incident_type
                    """
                elif (
                    "missing_payment" in q
                    or "missing payment" in q
                ):
                    sql = """
                        SELECT incident_type, COUNT(*) AS incident_count
                        FROM fct_reconciliation_incidents
                        WHERE incident_type = 'MISSING_PAYMENT'
                        GROUP BY incident_type
                    """
                else:
                    sql = """
                        SELECT incident_type, COUNT(*) AS incident_count
                        FROM fct_reconciliation_incidents
                        GROUP BY incident_type
                        ORDER BY incident_type
                    """

            elif (
                "settlement_mismatch" in q
                or "settlement mismatch" in q
            ):
                sql = """
                    SELECT payment_id, order_id, payment_amount,
                           refund_amount, settlement_amount,
                           incident_type, incident_severity
                    FROM fct_reconciliation_incidents
                    WHERE incident_type = 'SETTLEMENT_MISMATCH'
                    LIMIT 50
                """

            elif (
                "missing_payment" in q
                or "missing payment" in q
            ):
                sql = """
                    SELECT payment_id, order_id, order_amount,
                           reconciliation_status
                    FROM fct_reconciliation
                    WHERE reconciliation_status = 'MISSING_PAYMENT'
                    LIMIT 50
                """

            elif (
                "currency_mismatch" in q
                or "currency mismatch" in q
            ):
                sql = """
                    SELECT payment_id, order_id, order_currency,
                           payment_currency, reconciliation_status
                    FROM fct_reconciliation
                    WHERE reconciliation_status = 'CURRENCY_MISMATCH'
                    LIMIT 50
                """

            elif (
                "payment_amount_mismatch" in q
                or "payment amount mismatch" in q
            ):
                sql = """
                    SELECT payment_id, order_id, order_amount,
                           payment_amount, reconciliation_status
                    FROM fct_reconciliation
                    WHERE reconciliation_status = 'PAYMENT_AMOUNT_MISMATCH'
                    LIMIT 50
                """

            elif (
                "reconciliation status" in q
                or "status count" in q
            ):
                sql = """
                    SELECT reconciliation_status, COUNT(*) AS record_count
                    FROM fct_reconciliation
                    GROUP BY reconciliation_status
                    ORDER BY reconciliation_status
                """

            else:
                # Safe default: show status totals rather than
                # generating SQL dynamically from user input.
                sql = """
                    SELECT reconciliation_status, COUNT(*) AS record_count
                    FROM fct_reconciliation
                    GROUP BY reconciliation_status
                    ORDER BY reconciliation_status
                """

            rows = connection.execute(sql).fetchall()
            columns = [
                description[0]
                for description in connection.description
            ]

            results = [
                dict(zip(columns, row))
                for row in rows
            ]

            return json.dumps(
                {
                    "sql": sql.strip(),
                    "row_count": len(results),
                    "results": results,
                },
                indent=2,
                default=str,
            )

        finally:
            connection.close()

    except Exception as exc:
        return f"ERROR: Database query failed: {exc}"


# --------------------------------------------------
# 5. Retrieve reconciliation rules from the RAG index
# --------------------------------------------------

def retrieve_documents(question: str) -> str:
    # Support both running this file directly and importing
    # it as part of the rag package.
    try:
        from rag.retriever import search_rules
    except ModuleNotFoundError:
        from retriever import search_rules

    documents = search_rules(question)

    if not documents:
        return ""

    return "\n\n".join(
        document.page_content
        for document in documents
    )


# --------------------------------------------------
# 6. Collect SQL and/or RAG evidence
# --------------------------------------------------

def gather_evidence(state: RouterState) -> dict:
    route = state["route"]

    sql_result = ""
    retrieved_context = ""

    if route in ("SQL", "BOTH"):
        sql_result = query_database(state["question"])

    if route in ("RAG", "BOTH"):
        retrieved_context = retrieve_documents(
            state["question"]
        )

    return {
        "sql_result": sql_result,
        "retrieved_context": retrieved_context,
    }


# --------------------------------------------------
# 7. Generate an answer using Gemini
# --------------------------------------------------

def generate_answer(state: RouterState) -> dict:
    sql_result = state["sql_result"]
    retrieved_context = state["retrieved_context"]

    if (
        state["route"] in ("SQL", "BOTH")
        and sql_result.startswith("ERROR:")
    ):
        return {
            "answer": (
                "The database query failed. "
                "Please review the error before relying on this result."
            ),
            "status": "ERROR",
            "requires_human_approval": False,
        }

    if (
        state["route"] in ("RAG", "BOTH")
        and not retrieved_context.strip()
    ):
        return {
            "answer": (
                "No relevant reconciliation documentation was retrieved. "
                "The result needs manual review."
            ),
            "status": "NEEDS_REVIEW",
            "requires_human_approval": False,
        }

    if (
        state["route"] in ("SQL", "BOTH")
        and not sql_result.strip()
    ):
        return {
            "answer": "No database evidence was available for this question.",
            "status": "NEEDS_REVIEW",
            "requires_human_approval": False,
        }

    evidence = f"""
QUESTION:
{state["question"]}

ROUTE:
{state["route"]}

DATABASE EVIDENCE:
{sql_result if sql_result else "Not requested for this route."}

RECONCILIATION DOCUMENTATION:
{retrieved_context if retrieved_context else "Not requested for this route."}
"""

    try:
        model = ChatGoogleGenerativeAI(
            model="gemini-3.8-flash",
            temperature=0,
        )

        prompt = f"""
You are FINRECON AI, a payment reconciliation investigation assistant.

Answer the user's question using the evidence below.

Rules:
1. Use database results for financial counts, amounts, and records.
2. Use retrieved documentation for business rules and investigation guidance.
3. Never invent missing financial facts or claim that a query returned
   information that is not present in its results.
4. If evidence is insufficient or conflicting, clearly say so.
5. Never claim that you modified or corrected financial records.
6. Sensitive corrective actions require human approval.
7. Give a clear, concise explanation.

EVIDENCE:
{evidence}
"""

        response = model.invoke(prompt)
        answer = response.content

        if isinstance(answer, list):
            answer = "\n".join(
                item.get("text", str(item))
                if isinstance(item, dict)
                else str(item)
                for item in answer
            )

        answer = str(answer).strip()

        if not answer:
            return {
                "answer": "Gemini returned an empty answer.",
                "status": "NEEDS_REVIEW",
                "requires_human_approval": False,
            }

        return {
            "answer": answer,
            "status": "SUCCESS",
            "requires_human_approval": False,
        }

    except Exception as exc:
        return {
            "answer": f"Answer generation failed: {exc}",
            "status": "ERROR",
            "requires_human_approval": False,
        }


# --------------------------------------------------
# 8. Build a predictable structured response
# --------------------------------------------------

def build_structured_output(state: RouterState) -> dict:
    # This is a response-level approval flag.
    # No corrective action is executed by this workflow.
    result = {
        "route": state["route"],
        "status": state["status"],
        "question": state["question"],
        "answer": state["answer"],
        "evidence": {
            "sql_result": state["sql_result"],
            "retrieved_context": state["retrieved_context"],
        },
        "requires_human_approval": state[
            "requires_human_approval"
        ],
    }

    return {"structured_output": result}


# --------------------------------------------------
# 9. Build the LangGraph workflow
# --------------------------------------------------

def build_graph():
    workflow = StateGraph(RouterState)

    workflow.add_node("classify_question", classify_question)
    workflow.add_node("gather_evidence", gather_evidence)
    workflow.add_node("generate_answer", generate_answer)
    workflow.add_node("build_structured_output", build_structured_output)

    workflow.add_edge(START, "classify_question")
    workflow.add_edge("classify_question", "gather_evidence")
    workflow.add_edge("gather_evidence", "generate_answer")
    workflow.add_edge("generate_answer", "build_structured_output")
    workflow.add_edge("build_structured_output", END)

    return workflow.compile()


# --------------------------------------------------
# 10. Run the application
# --------------------------------------------------

if __name__ == "__main__":
    app = build_graph()

    question = input("Ask FINRECON AI: ").strip()

    if not question:
        print("Please enter a question.")
        sys.exit(1)

    initial_state: RouterState = {
        "question": question,
        "route": "",
        "sql_result": "",
        "retrieved_context": "",
        "answer": "",
        "status": "PENDING",
        "requires_human_approval": False,
        "structured_output": {},
    }

    result = app.invoke(initial_state)

    print("\n========== FINRECON AI RESPONSE ==========")
    print(
        json.dumps(
            result["structured_output"],
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )
