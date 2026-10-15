
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class FinreconState(TypedDict):
    question: str
    retrieved_context: str
    answer: str
    status: str


def retrieve_context(state: FinreconState) -> dict:
    """Retrieve relevant rules from FINRECON documentation."""

    from retriever import search_rules

    documents = search_rules(state["question"])
    context = "\n\n".join(doc.page_content for doc in documents)

    return {"retrieved_context": context}


def prepare_answer(state: FinreconState) -> dict:
    """Return a predefined answer only when its rule is verified."""

    context = state["retrieved_context"].lower()
    question = state["question"].lower()

    if not context.strip():
        return {
            "answer": "No relevant rule was found in the documentation.",
            "status": "NO_CONTEXT",
        }

    if "settlement_mismatch" in question:
        required_terms = [
            "settlement amount",
            "payment amount",
            "refund amount",
        ]

        if all(term in context for term in required_terms):
            return {
                "answer": (
                    "A SETTLEMENT_MISMATCH occurs when the settlement "
                    "amount differs from the payment amount minus "
                    "the refund amount."
                ),
                "status": "SUCCESS",
            }

    if "missing_payment" in question:
        if "no matching payment record" in context:
            return {
                "answer": (
                    "MISSING_PAYMENT means an order exists, but no "
                    "matching payment record is available."
                ),
                "status": "SUCCESS",
            }

    return {
        "answer": (
            "Relevant documentation was retrieved, but the workflow "
            "could not verify a predefined answer. Review the context."
        ),
        "status": "NEEDS_REVIEW",
    }


def build_graph():
    workflow = StateGraph(FinreconState)

    workflow.add_node("retrieve_context", retrieve_context)
    workflow.add_node("prepare_answer", prepare_answer)

    workflow.add_edge(START, "retrieve_context")
    workflow.add_edge("retrieve_context", "prepare_answer")
    workflow.add_edge("prepare_answer", END)

    return workflow.compile()


if __name__ == "__main__":
    app = build_graph()

    result = app.invoke({
        "question": "Why is a payment marked as SETTLEMENT_MISMATCH?",
        "retrieved_context": "",
        "answer": "",
        "status": "PENDING",
    })

    print("Status:", result["status"])
    print("Answer:", result["answer"])
    print("\nRetrieved context:")
    print(result["retrieved_context"])
