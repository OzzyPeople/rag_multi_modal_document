# src/utils/helpers.py
from __future__ import annotations
from pathlib import Path
import hashlib
from langchain_chroma import Chroma

COLLECTIONS = ["pdf_text", "pdf_tables", "pdf_images"]

def file_sha256(path: str | Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()

def is_already_indexed(doc_hash: str, persist_dir: str = "chroma_db") -> bool:
    """
    Return True if any collection already has at least one record with metadata doc_hash == <doc_hash>.
    Uses a minimal get (limit=1) to avoid fetching vectors/documents.
    """
    for name in COLLECTIONS:
        store = Chroma(
            collection_name=name,
            persist_directory=persist_dir,
            embedding_function=None,   # we don't embed during existence check
        )
        # Ask for only metadatas to minimize payload; limit=1 = existence check
        res = store._collection.get(
            where={"doc_hash": doc_hash},
            include=["metadatas"],
            limit=1,
        )
        ids = res.get("ids", []) if isinstance(res, dict) else getattr(res, "ids", [])
        if ids:
            return True
    return False