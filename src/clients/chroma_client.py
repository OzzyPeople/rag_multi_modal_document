from pathlib import Path
from typing import Any, Dict, List, Tuple
#from langchain_community.vectorstores import Chroma
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

def _bbox_fields(bbox):
    if not bbox:
        return {"bbox_x0": None, "bbox_y0": None, "bbox_x1": None, "bbox_y1": None}
    x0, y0, x1, y1 = bbox
    return {"bbox_x0": float(x0), "bbox_y0": float(y0), "bbox_x1": float(x1), "bbox_y1": float(y1)}

def _split_text_docs(docs, *, chunk_size=1200, chunk_overlap=150):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
    )
    return splitter.split_documents(docs)

def _get_store(collection_name: str, embeddings, persist_dir: str) -> Chroma:
    return Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=persist_dir,
    )

def index_text_docs(
    docs, embeddings, persist_dir="chroma_db", collection_name="pdf_text",
    doc_tag: str | None = None,
):
    if not docs:
        return None
    chunks = _split_text_docs(docs)
    texts = [c.page_content for c in chunks]
    metas, ids = [], []
    for i, c in enumerate(chunks):
        p0 = int(c.metadata.get("page", 0))  # PyPDFLoader is 0-based
        p1 = p0 + 1
        ids.append(f"{doc_tag or Path(c.metadata.get('source','doc')).stem}-p{p1:04d}-c{i:04d}")
        metas.append({
            "type": "text",
            "source": c.metadata.get("source"),
            "page": p1,
            "file_name": c.metadata.get("file_name"),
            "page_label": c.metadata.get("page_label"),
            "doc_tag": doc_tag,
        })
    store = _get_store(collection_name, embeddings, persist_dir)
    store.add_texts(texts=texts, metadatas=metas, ids=ids)
    return store

def index_image_artifacts(images, embeddings, persist_dir="chroma_db",
                          collection_name="pdf_images", doc_tag=None):
    if not images:
        return None
    texts, metas, ids = [], [], []
    for a in images:
        body = (a.caption or "").strip()
        if a.ocr_text:
            body += ("\nOCR: " + a.ocr_text.strip())
        if not body.strip():
            body = f"Image on page {a.page} of {Path(a.pdf_path).name}"
        texts.append(body)

        meta = {
            "type": "image",
            "image_id": a.image_id,
            "pdf_path": a.pdf_path,
            "png_path": a.png_path,
            "page": a.page,
            "doc_tag": doc_tag,
        }
        meta.update(_bbox_fields(a.bbox))      # <-- flatten bbox here
        metas.append(meta)
        ids.append(a.image_id)

    store = _get_store(collection_name, embeddings, persist_dir)
    store.add_texts(texts=texts, metadatas=metas, ids=ids)
    # store.persist()  # remove in Chroma >=0.4
    return store

def index_table_artifacts(tables, embeddings, persist_dir="chroma_db",
                          collection_name="pdf_tables", doc_tag=None):
    if not tables:
        return None
    texts, metas, ids = [], [], []
    for t in tables:
        texts.append((t.preview_text or "").strip() or f"Table on page {t.page}")
        meta = {
            "type": "table",
            "table_id": t.table_id,
            "pdf_path": t.pdf_path,
            "page": t.page,
            "csv_path": t.csv_path,
            "json_path": t.json_path,
            "doc_tag": doc_tag,
        }
        meta.update(_bbox_fields(t.bbox))      # <-- flatten bbox here
        metas.append(meta)
        ids.append(t.table_id)

    store = _get_store(collection_name, embeddings, persist_dir)
    store.add_texts(texts=texts, metadatas=metas, ids=ids)
    return store


def index_all_modalities(result: Dict[str, Any], embeddings, persist_dir="chroma_db"):
    """
    result is the dict returned by ingest_pdf_multimodal(...)
    """
    doc_tag = Path(result["pdf_path"]).stem
    stores = {}
    stores["text"] = index_text_docs(result.get("text"), embeddings, persist_dir, "pdf_text", doc_tag)
    stores["tables"] = index_table_artifacts(result.get("tables"), embeddings, persist_dir, "pdf_tables", doc_tag)
    stores["images"] = index_image_artifacts(result.get("images"), embeddings, persist_dir, "pdf_images", doc_tag)
    return stores
