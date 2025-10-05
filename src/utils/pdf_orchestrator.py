# src/utils/pdf/orchestrator.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List

# NOTE: adjust imports to your actual module names
from src.utils.table_extractor import extract_tables, TableArtifact
from src.utils.image_extractor import (
    extract_images,
    ImageArtifact,
    caption_with_gemini_client_factory,
)

@dataclass
class IngestConfig:
    enable_text: bool = False
    enable_tables: bool = True
    enable_images: bool = True
    run_ocr: bool = False
    caption_with_gemini: bool = True
    dpi: int = 144
    out_dir: str = "artifacts_pdf"
    num_pages: Optional[int] = None   # <-- if 3, take first 3 pages



def ingest_pdf_multimodal(
    pdf_path: str,
    cfg: IngestConfig,
    *,
    gemini_client: Optional["GeminiClient"] = None,           # GeminiClient instance
    captioner: Optional[Callable[..., str]] = None,           # custom captioner(bytes, mime=...) if you have one
    text_loader: Optional[Callable[[str], List[Any]]] = None, # e.g., load_pdf_text(pdf_path) -> List[Document]
) -> Dict[str, Any]:
    """
    Orchestrate extraction of text, tables, and images from a PDF.
    Returns a dict with 'text', 'tables', 'images' and simple 'stats'.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    text_docs: Optional[List[Any]] = None
    tables: Optional[List[TableArtifact]] = None
    images: Optional[List[ImageArtifact]] = None

    if cfg.enable_text and text_loader is not None:
        text_docs = text_loader(str(path), num_pages=cfg.num_pages)

    if cfg.enable_tables:
        tables = extract_tables(str(path), out_dir=cfg.out_dir, num_pages=cfg.num_pages)

    if cfg.enable_images:
        # Prefer explicitly passed captioner; else build one from your GeminiClient
        cap = captioner
        if cap is None and cfg.caption_with_gemini and gemini_client is not None:
            cap = caption_with_gemini_client_factory(
                gemini_client,
                model="gemini-2.0-flash",
                max_output_tokens=64,  # forwarded into your client.generate_vision(**kwargs)
            )
        images = extract_images(
            str(path),
            out_dir=cfg.out_dir,
            dpi=cfg.dpi,
            run_ocr=cfg.run_ocr,
            captioner=cap,
            num_pages=cfg.num_pages,
        )

    return {
        "pdf_path": str(path),
        "text": text_docs,
        "tables": tables,
        "images": images,
        "stats": {
            "text_pages": len(text_docs) if text_docs is not None else 0,
            "tables": len(tables) if tables is not None else 0,
            "images": len(images) if images is not None else 0,
        },
    }