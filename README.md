RAG-Multimodal PDF (Text + Tables + Images)
1) Document Choice

Type: PDF (scientific/technical papers).
Why: PDFs are the most common real-world artifact. They mix long-form text with tables and figures—perfect to demonstrate a pragmatic, production-lean RAG that goes beyond plain text.

2) Setup Instructions
poetry install

3) Create .env in the repo root:
# APIs
MODEL_API_KEY=your_google_api_key
MODEL_NAME=gemini-2.0-flash

# Files & storage
PDF_PATH=./data/transformer_article.pdf
CHROMA_DIR=./chroma_db
ARTIFACTS_DIR=./artifacts_pdf

# Optional for quick tests
NUM_PAGES=3              # limit ingestion to first N pages
QUESTION=Explain scaled dot-product attention.

### Usage Example
poetry run python -m src.llm_poc

### Known Limitations & Future Work

Gemini rate limits/costs: Free-tier quota can throttle captioning/QA; add backoff or batching, or use a paid tier.
Table accuracy: Complex/rotated tables and multi-line cells may extract imperfectly. Next: table structure repair & header detection.
Image bounding boxes: Embedded image bbox is not always available from PyMuPDF; we fall back to page-level context.
No multimodal embeddings: We index text surrogates for images; consider image embeddings or CLIP-style joint models later.
Simple ranking: Add a cross-encoder reranker (e.g., Cohere Rerank, bge-reranker) for better precision at k.
Chunking/citation: Switch to semantic chunking with overlap + page anchoring for long pages.
Chroma migration: Prefer langchain-chroma package; remove deprecated imports fully.

### Optional Extras
Architecture (flow)
PDF
 └─ ingest_pdf_multimodal
     ├─ Text: PyPDFLoader → page docs → embed → Chroma(pdf_text)
     ├─ Tables: pdfplumber → CSV/JSON + preview text → embed → Chroma(pdf_tables)
     └─ Images: PyMuPDF renders/rasters → (OCR?) (Gemini captions?) → text → embed → Chroma(pdf_images)

Query
 └─ RAGRetriever
     ├─ top-k per collection → merge by distance → formatted context [collection p#]
     └─ Gemini QA (use-only-context, cite pages) → Answer

Where artifacts live

Chroma: CHROMA_DIR
Extracted assets: ARTIFACTS_DIR/
tables/<pdf_stem>/*.csv and *.json
figures/<pdf_stem>/*.png (full pages + embedded rasters)

Notable challenges

Metadata constraints in Chroma: We sanitize complex fields (e.g., tuples like bboxes) into strings to avoid upsert errors.
Balancing speed vs. coverage: Full-page renders ensure we “see” vector figures; captions & OCR add recall but cost tokens/time.
Reliable page-level citations: Keeping per-page granularity made eval & debugging far easier in MVP.