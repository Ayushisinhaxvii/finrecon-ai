
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings


# Load the API key from the project-root .env file
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

VECTOR_STORE_DIR = PROJECT_ROOT / "data" / "vector_store"


def load_retriever():
    """Load the saved FAISS index and return a retriever."""

    if not os.getenv("GOOGLE_API_KEY"):
        raise EnvironmentError(
            "GOOGLE_API_KEY is missing. Check your project-root .env file."
        )

    if not (VECTOR_STORE_DIR / "index.faiss").exists():
        raise FileNotFoundError(
            f"FAISS index not found at {VECTOR_STORE_DIR}. "
            "Run rag/vector_store.py first."
        )

    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001"
    )

    vector_store = FAISS.load_local(
        str(VECTOR_STORE_DIR),
        embeddings,
        allow_dangerous_deserialization=True,
    )

    return vector_store.as_retriever(search_kwargs={"k": 3})


def search_rules(question: str):
    """Retrieve the three most relevant document chunks."""

    retriever = load_retriever()
    return retriever.invoke(question)


if __name__ == "__main__":
    question = input("Ask a FINRECON question: ")
    results = search_rules(question)

    if not results:
        print("No relevant documentation found.")
    else:
        for index, document in enumerate(results, start=1):
            print(f"\n--- Result {index} ---")
            print(document.page_content)
            print("Source:", document.metadata.get("source", "Unknown"))
