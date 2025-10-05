from pathlib import Path
from typing import List, Iterable, Optional, Sequence
import logging

from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader

logger = logging.getLogger(__name__)

def load_pdf_text_ex(
    pdf_path: str,
    pages: Optional[Sequence[int]] = None,   # e.g., [0,1,2] (0-based)
    max_pages: Optional[int] = None
) -> List[Document]:
    """
    Load PDF text into LangChain Documents (one per page).

    Args:
        pdf_path: Path to the PDF file.
        pages: Optional explicit list of 0-based page indices to keep.
        max_pages: If provided, keep only the first N pages (after filtering).

    Returns:
        List[Document]

    Raises:
        FileNotFoundError: If file doesn't exist.
        RuntimeError: If loading fails.
    """
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF file not found: {path}")

    try:
        loader = PyPDFLoader(str(path))
        docs: List[Document] = loader.load()  # one Document per page

        # Optional filtering
        if pages is not None:
            keep = set(pages)
            docs = [d for i, d in enumerate(docs) if i in keep]
        if max_pages is not None:
            docs = docs[:max_pages]

        # Normalize metadata for reliable citations
        for d in docs:
            md = d.metadata or {}
            md.setdefault("source", str(path))
            md.setdefault("file_name", path.name)
            # LangChain already sets 'page' for PyPDFLoader; ensure it exists
            if "page" not in md and "page_number" in md:
                md["page"] = md["page_number"]
            d.metadata = md

        logger.info("[PDF] Loaded %d pages from '%s'", len(docs), path)
        return docs

    except Exception as e:
        raise RuntimeError(f"Failed to load PDF '{path}': {e}") from e

def load_pdf_text(pdf_path: str, *, num_pages: Optional[int] = None) -> List[Document]:
    """
    Load a PDF into a list of LangChain Document objects (one per page).
    If num_pages is provided, return only the first N pages.
    """
    pages = PyPDFLoader(pdf_path).load()
    if not num_pages or num_pages <= 0:
        return pages
    return pages[:min(num_pages, len(pages))]