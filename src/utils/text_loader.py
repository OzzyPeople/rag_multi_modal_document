from pathlib import Path
from typing import List, Iterable, Optional, Sequence
import logging

from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader

logger = logging.getLogger(__name__)

def load_pdf_text(pdf_path: str, *, num_pages: Optional[int] = None) -> List[Document]:
    """
    Load a PDF into a list of LangChain Document objects (one per page).
    If num_pages is provided, return only the first N pages.
    """
    pages = PyPDFLoader(pdf_path).load()
    if not num_pages or num_pages <= 0:
        return pages
    return pages[:min(num_pages, len(pages))]