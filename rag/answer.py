
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from retriever import search_rules


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def answer_question(question: str) -> str:
    """Answer using retrieved FINRECON documentation."""

    if not os.getenv("GOOGLE_API_KEY"):
        raise EnvironmentError("GOOGLE_API_KEY is missing from .env")

    documents = search_rules(question)

    if not documents:
        return "I could not find relevant information in FINRECON documentation."

    context = "\n\n".join(doc.page_content for doc in documents)

    prompt = f"""
You are FINRECON AI, a financial reconciliation assistant.

Answer the user's question using ONLY the context below.
Do not invent financial amounts, IDs, database results, or policies.
If the context does not contain the answer, say so.
Financial facts must be verified from database query results.

Context:
{context}

Question:
{question}

Answer:
"""

    llm = ChatGoogleGenerativeAI(
        model="gemini-3.8-flash",
        temperature=0,
    )

    response = llm.invoke(prompt)
    content = response.content

    if isinstance(content, str):
      return content

    if isinstance(content, list):
     return "\n".join(
        item["text"]
        for item in content
        if isinstance(item, dict) and item.get("type") == "text"
    )

    return str(content)


if __name__ == "__main__":
    question = input("Ask FINRECON AI: ")
    print("\nAnswer:")
    print(answer_question(question))
