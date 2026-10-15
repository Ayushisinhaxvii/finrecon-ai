
from pathlib import Path

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter


# Project root: finrecon-ai/
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = PROJECT_ROOT / "docs"


def load_documents():
    """Load Markdown documents from the project's docs folder."""

    if not DOCS_DIR.exists():
        raise FileNotFoundError(f"Documentation folder not found: {DOCS_DIR}")

    loader = DirectoryLoader(
        str(DOCS_DIR),
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        show_progress=False,
    )

    documents = loader.load()

    if not documents:
        raise ValueError(
            f"No Markdown documents found in {DOCS_DIR}. "
            "Add a .md file before building the knowledge base."
        )

    return documents


def split_documents(documents):
    """Split long documents into smaller, searchable text chunks."""

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=700,
        chunk_overlap=100,
        add_start_index=True,
    )

    return splitter.split_documents(documents)


if __name__ == "__main__":
    documents = load_documents()
    chunks = split_documents(documents)

    print(f"Documents loaded: {len(documents)}")
    print(f"Text chunks created: {len(chunks)}")

    for index, chunk in enumerate(chunks[:3], start=1):
        print(f"\n--- Chunk {index} ---")
        print(chunk.page_content[:300])
