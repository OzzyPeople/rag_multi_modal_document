from src.utils.pdf_orchestrator import IngestConfig, ingest_pdf_multimodal
from src.clients.gemini_client import GeminiClient
from src.prompts.system_prompt import CAPTION_ASSISTANT, SCIENTIFIC_ANALYST
from src.utils.text_loader import load_pdf_text
from src.clients.chroma_client import index_all_modalities
from src.embedding.google_embed import get_google_embeddings
from langchain_chroma import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI
from src.retriever.rag_retriever import RAGRetriever

from dotenv import load_dotenv
import json
import os
load_dotenv()

API_KEY = os.getenv("MODEL_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME")
pdf_path = os.getenv("PDF_PATH")
num_pages = os.getenv("NUMBER_OF_PAGES")

##Pipeline: Ingest PDF -> Index in Chroma
cfg = IngestConfig(
    enable_text=True,
    enable_tables=True,
    enable_images=True,
    run_ocr=False,
    dpi=144,
    out_dir="artifacts_pdf",
    num_pages=int(num_pages)
)
gc = GeminiClient(api_key=API_KEY, system_prompt=CAPTION_ASSISTANT, model=MODEL_NAME)

result = ingest_pdf_multimodal(
    pdf_path,
    cfg,
    gemini_client=gc,  # builds the captioner under the hood
    text_loader=load_pdf_text,
)
emb = get_google_embeddings(model="models/text-embedding-004")
stores = index_all_modalities(result, emb, persist_dir="chroma_db")

### Retrieval -> RAG Retrieval -> LLM Answering
emb = get_google_embeddings()
rag = RAGRetriever(emb, persist_dir="chroma_db")

question = input("Question (Enter for default): ").strip() or "Explain scaled dot-product attention."
answer, hits, ctx = rag.answer(question, api_key=API_KEY)
print(answer)

if __name__ == "__main__":
    print(answer)

#poetry run python -m src.llm_poc

