#run_pipeline.py
from pathlib import Path
import os
import argparse
import sys
from dotenv import load_dotenv

from src.utils.pdf_orchestrator import IngestConfig, ingest_pdf_multimodal
from src.clients.gemini_client import GeminiClient
from src.utils.text_loader import load_pdf_text
from src.clients.chroma_client import index_all_modalities
from src.embedding.google_embed import get_google_embeddings
from src.utils.helpers import file_sha256, is_already_indexed

def parse_int_or_none(v: str | None) -> int | None:
    if not v:
        return None
    v = v.strip()
    if not v:
        return None
    try:
        i = int(v)
        return i if i > 0 else None
    except ValueError:
        return None

def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Ingest a PDF and index into Chroma.")
    parser.add_argument("--pdf", required=False, help="Path to PDF. Falls back to $PDF_PATH if omitted.")
    parser.add_argument("--num-pages", type=int, default=None, help="Limit to first N pages (omit for all).")
    parser.add_argument("--force", action="store_true", help="Re-ingest even if already indexed.")
    parser.add_argument("--artifacts-dir", default=os.getenv("ARTIFACTS_DIR", "artifacts_pdf"))
    parser.add_argument("--chroma-dir", default=os.getenv("CHROMA_DIR", "chroma_db"))
    parser.add_argument("--model-name", default=os.getenv("MODEL_NAME", "gemini-2.0-flash"))
    args = parser.parse_args()

    API_KEY = os.getenv("MODEL_API_KEY")
    if not API_KEY:
        print("[ERROR] Missing MODEL_API_KEY in environment.", file=sys.stderr)
        sys.exit(1)

    pdf_path = args.pdf or os.getenv("PDF_PATH")
    if not pdf_path:
        print("[ERROR] Provide --pdf or set PDF_PATH in env.", file=sys.stderr)
        sys.exit(1)

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        print(f"[ERROR] PDF not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    # Determine page cap: CLI flag wins, else env NUM_PAGES/NUMBER_OF_PAGES
    env_pages = os.getenv("NUMBER_OF_PAGES") or os.getenv("NUM_PAGES")
    num_pages = args.num_pages if args.num_pages is not None else parse_int_or_none(env_pages)

    # Idempotency key for this file
    doc_hash = file_sha256(str(pdf_path))
    already = is_already_indexed(doc_hash, persist_dir=args.chroma_dir)

    if already and not args.force:
        print(f"✅ '{pdf_path.stem}' already indexed — skipping ingestion.")
        return

    print(f"🚀 Ingesting '{pdf_path.stem}' ... (pages={'all' if not num_pages else num_pages})")

    cfg = IngestConfig(
        enable_text=True,
        enable_tables=True,
        enable_images=True,
        run_ocr=False,
        dpi=144,
        out_dir=args.artifacts_dir,
        num_pages=num_pages,  # None => all pages; int => first N pages
    )

    gc = GeminiClient(api_key=API_KEY, system_prompt="You caption images.", model=args.model_name)

    result = ingest_pdf_multimodal(
        str(pdf_path),
        cfg,
        gemini_client=gc,          # builds captioner when enabled
        text_loader=load_pdf_text, # supports num_pages
    )

    emb = get_google_embeddings(model="models/text-embedding-004")

    # Attach identifiers to every vector for provenance
    # NOTE: index_all_modalities should accept doc_tag to thread metadata (doc_hash, file_name) through.
    stores = index_all_modalities(
        result,
        emb,
        persist_dir=args.chroma_dir,
        doc_tag={"doc_hash": doc_hash, "file_name": pdf_path.name},
    )

    print(f"Indexed: {result['stats']}")

if __name__ == "__main__":
    main()
