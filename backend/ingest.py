
import argparse
import re
import sys
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

CLAUSE_MARKER_RE = re.compile(r"^\[CLAUSE\s+([^\]]+)\]\s*$", re.MULTILINE)
CHROMA_PERSIST_DIR = "./chroma_store"
COLLECTION_NAME = "sebi_icdr_schedule_vi"


def chunk_by_clause(text: str):
    """Split source text into (clause_number, clause_text) chunks on [CLAUSE ...] markers."""
    markers = list(CLAUSE_MARKER_RE.finditer(text))
    if not markers:
        raise ValueError(
            "No [CLAUSE ...] markers found in source file — see the module docstring "
            "for the expected format."
        )
    chunks = []
    for i, marker in enumerate(markers):
        clause_number = marker.group(1).strip()
        start = marker.end()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(text)
        clause_text = text[start:end].strip()
        if clause_text:
            chunks.append((clause_number, clause_text))
    return chunks


def ingest(source_path: str):
    path = Path(source_path)
    if not path.exists():
        print(f"Source file not found: {source_path}", file=sys.stderr)
        sys.exit(1)

    text = path.read_text(encoding="utf-8")
    chunks = chunk_by_clause(text)
    print(f"Parsed {len(chunks)} clause chunks from {source_path}")

    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    embed_fn = embedding_functions.DefaultEmbeddingFunction()
    collection = client.get_or_create_collection(name=COLLECTION_NAME, embedding_function=embed_fn)

    ids = [f"{path.stem}-{i}" for i in range(len(chunks))]
    documents = [chunk_text for _, chunk_text in chunks]
    metadatas = [{"clause_number": clause_number, "source": path.name} for clause_number, _ in chunks]

    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    print(f"Upserted {len(chunks)} chunks into ChromaDB collection '{COLLECTION_NAME}' at {CHROMA_PERSIST_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest SEBI regulation text into ChromaDB.")
    parser.add_argument("--source", required=True, help="Path to a plain-text regulation source file.")
    args = parser.parse_args()
    ingest(args.source)
