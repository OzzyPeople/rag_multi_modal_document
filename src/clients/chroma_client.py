# src/clients/chroma_client.py
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import hashlib
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter


# ------------------------ helpers ------------------------

def _file_sha256(p: str | Path) -> str:
    p = Path(p)
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    # short but collision-resistant enough for ids
    return h.hexdigest()[:16]


def _bbox_sig(bbox: Optional[Tuple[float, float, float, float]]) -> str:
    if not bbox:
        return "none"
    x0, y0, x1, y1 = bbox
    return f"{round(x0)}_{round(y0)}_{round(x1)}_{round(y1)}"


def _bbox_fields(bbox: Optional[Tuple[float, float, float, float]]) -> Dict[str, Optional[float]]:
    if not bbox:
        return {"bbox_x0": None, "bbox_y0": None, "bbox_x1": None, "bbox_y1": None}
    x0, y0, x1, y1 = bbox
    return {
        "bbox_x0": float(x0),
        "bbox_y0": float(y0),
        "bbox_x1": float(x1),
        "bbox_y1": float(y1),
    }


def _sha1_file(p: str | Path) -> str:
    p = Path(p)
    h = hashlib.sha1()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:12]


def _clean_meta(meta: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure Chroma-safe metadata types."""
    out: Dict[str, Any] = {}
    for k, v in (meta or {}).items():
        if isinstance(v, (str, int, float, bool)) or v is None:
            out[k] = v
        else:
            out[k] = str(v)
    return out


def _split_text_docs(docs, *, chunk_size=1200, chunk_overlap=150):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
    )
    return splitter.split_documents(docs)


def _get_store(collection_name: str, embeddings, persist_dir: str) -> Chroma:
    return Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=persist_dir,
    )


# ------------------------ indexers ------------------------

def index_text_docs(
    docs,
    embeddings,
    persist_dir: str = "chroma_db",
    collection_name: str = "pdf_text",
    *,
    pdf_path: str,
    doc_hash: Optional[str] = None,
    doc_tag: Optional[str] = None,
    chunk_size: int = 1200,
    chunk_overlap: int = 150,
):
    """Index text Documents (LangChain) with stable ids."""
    if not docs:
        return None

    dh = doc_hash or _file_sha256(pdf_path)
    chunks = _split_text_docs(docs, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    texts: List[str] = []
    metas: List[Dict[str, Any]] = []
    ids: List[str] = []

    for i, c in enumerate(chunks):
        # PyPDFLoader uses 0-based page; normalize to 1-based
        page0 = int(c.metadata.get("page", 0))
        page = page0 + 1

        ids.append(f"{dh}:text:p{page:04d}:c{i:04d}")

        meta = {
            "type": "text",
            "pdf_path": c.metadata.get("source") or pdf_path,
            "file_name": c.metadata.get("file_name") or Path(pdf_path).name,
            "page": page,
            "page_label": c.metadata.get("page_label"),
            "doc_tag": doc_tag or Path(pdf_path).stem,
            "doc_hash": dh,
        }
        metas.append(_clean_meta(meta))
        texts.append(c.page_content)

    store = _get_store(collection_name, embeddings, persist_dir)
    store.add_texts(texts=texts, metadatas=metas, ids=ids)  # upsert
    return store

def index_table_artifacts(
    tables,
    embeddings,
    persist_dir: str = "chroma_db",
    collection_name: str = "pdf_tables",
    *,
    pdf_path: str,
    doc_hash: Optional[str] = None,
    doc_tag: Optional[str] = None,
):
    """Index table artifacts using preview text; stable ids from page+bbox."""
    if not tables:
        return None

    dh = doc_hash or _file_sha256(pdf_path)
    store = _get_store(collection_name, embeddings, persist_dir)

    texts: List[str] = []
    metas: List[Dict[str, Any]] = []
    ids: List[str] = []

    for i, t in enumerate(tables):
        sig = _bbox_sig(t.bbox)
        # Stable vector id (independent of extractor's random table_id)
        vid = f"{dh}:table:p{t.page:04d}:{sig}:{i:02d}"
        ids.append(vid)

        text = (t.preview_text or "").strip() or f"Table on page {t.page}"
        texts.append(text)

        meta = {
            "type": "table",
            "table_id": t.table_id,        # keep original id for traceability
            "pdf_path": t.pdf_path,
            "file_name": Path(t.pdf_path).name,
            "page": t.page,
            "csv_path": t.csv_path,
            "json_path": t.json_path,
            "bbox_sig": sig,               # string, not tuple
            "doc_tag": doc_tag or Path(pdf_path).stem,
            "doc_hash": dh,
        }
        meta.update(_bbox_fields(t.bbox))
        metas.append(_clean_meta(meta))

    store.add_texts(texts=texts, metadatas=metas, ids=ids)  # upsert
    return store


def index_image_artifacts(
    images,
    embeddings,
    persist_dir: str = "chroma_db",
    collection_name: str = "pdf_images",
    *,
    pdf_path: str,
    doc_hash: Optional[str] = None,
    doc_tag: Optional[str] = None,
):
    """Index image artifacts; text = caption + optional OCR. Stable ids via sha1(file)."""
    if not images:
        return None

    dh = doc_hash or _file_sha256(pdf_path)
    store = _get_store(collection_name, embeddings, persist_dir)

    texts: List[str] = []
    metas: List[Dict[str, Any]] = []
    ids: List[str] = []

    for img in images:
        imsig = _sha1_file(img.png_path)
        vid = f"{dh}:image:p{img.page:04d}:{imsig}"
        ids.append(vid)

        body = (img.caption or "").strip()
        if img.ocr_text:
            body = (body + ("\nOCR: " if body else "OCR: ") + img.ocr_text.strip()).strip()
        if not body:
            body = f"Image on page {img.page} of {Path(img.pdf_path).name}"
        texts.append(body)

        meta = {
            "type": "image",
            "image_id": img.image_id,      # original id from extractor
            "pdf_path": img.pdf_path,
            "file_name": Path(img.pdf_path).name,
            "png_path": img.png_path,
            "page": img.page,
            "bbox_sig": _bbox_sig(img.bbox),
            "has_caption": bool(img.caption),
            "has_ocr": bool(img.ocr_text),
            "doc_tag": doc_tag or Path(pdf_path).stem,
            "doc_hash": dh,
        }
        meta.update(_bbox_fields(img.bbox))
        metas.append(_clean_meta(meta))

    store.add_texts(texts=texts, metadatas=metas, ids=ids)  # upsert
    return store


# ------------------------ orchestrator ------------------------

def index_all_modalities(
    result: Dict[str, Any],
    embeddings,
    persist_dir: str = "chroma_db",
    *,
    doc_hash: Optional[str] = None,
    doc_tag: Optional[str] = None,
) -> Dict[str, Optional[Chroma]]:
    """
    result: dict from ingest_pdf_multimodal(...)
    Returns a dict of Chroma stores (text/tables/images).
    """
    pdf_path = result.get("pdf_path") or ""
    if not pdf_path:
        raise ValueError("result['pdf_path'] is required")

    dh = doc_hash or _file_sha256(pdf_path)
    tag = doc_tag or Path(pdf_path).stem

    stores: Dict[str, Optional[Chroma]] = {}
    stores["text"] = index_text_docs(
        result.get("text"),
        embeddings,
        persist_dir=persist_dir,
        collection_name="pdf_text",
        pdf_path=pdf_path,
        doc_hash=dh,
        doc_tag=tag,
    )
    stores["tables"] = index_table_artifacts(
        result.get("tables"),
        embeddings,
        persist_dir=persist_dir,
        collection_name="pdf_tables",
        pdf_path=pdf_path,
        doc_hash=dh,
        doc_tag=tag,
    )
    stores["images"] = index_image_artifacts(
        result.get("images"),
        embeddings,
        persist_dir=persist_dir,
        collection_name="pdf_images",
        pdf_path=pdf_path,
        doc_hash=dh,
        doc_tag=tag,
    )
    return stores
