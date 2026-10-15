
from answer import answer_question
from retriever import search_rules


# Simple, deterministic checks for our initial RAG evaluation.
TEST_CASES = [
    {
        "question": "Why is a payment marked as SETTLEMENT_MISMATCH?",
        "expected_terms": [
            "settlement amount",
            "payment amount",
            "refund amount",
        ],
    },
    {
        "question": "What does MISSING_PAYMENT mean?",
        "expected_terms": [
            "order",
            "payment record",
        ],
    },
    {
        "question": "What should happen before sensitive corrective actions?",
        "expected_terms": [
            "human approval",
        ],
    },
]


def evaluate_retrieval(question: str, expected_terms: list[str]) -> bool:
    """Check whether retrieved text contains the expected terms."""

    documents = search_rules(question)
    retrieved_text = " ".join(
        document.page_content for document in documents
    ).lower()

    missing_terms = [
        term for term in expected_terms
        if term.lower() not in retrieved_text
    ]

    if missing_terms:
        print(f"Retrieval check FAILED. Missing: {missing_terms}")
        return False

    print("Retrieval check PASSED.")
    return True


def evaluate_answer(question: str, expected_terms: list[str]) -> bool:
    """Check whether the generated answer includes expected terms."""

    answer = answer_question(question)
    print(f"Answer: {answer}")

    missing_terms = [
        term for term in expected_terms
        if term.lower() not in answer.lower()
    ]

    if missing_terms:
        print(f"Answer check FAILED. Missing: {missing_terms}")
        return False

    print("Answer check PASSED.")
    return True


if __name__ == "__main__":
    retrieval_passed = 0
    answer_passed = 0

    for index, test_case in enumerate(TEST_CASES, start=1):
        print(f"\n{'=' * 55}")
        print(f"Test {index}: {test_case['question']}")

        if evaluate_retrieval(
            test_case["question"], test_case["expected_terms"]
        ):
            retrieval_passed += 1

        if evaluate_answer(
            test_case["question"], test_case["expected_terms"]
        ):
            answer_passed += 1

    print(f"\nRetrieval checks: {retrieval_passed}/{len(TEST_CASES)}")
    print(f"Answer checks: {answer_passed}/{len(TEST_CASES)}")
