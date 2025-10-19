#rag_retrieval.py
from __future__ import annotations
from typing import Sequence, Optional, Dict, Any, List
import time
from src.clients.gemini_client import GeminiClient
from src.prompts.task_prompts import human_question
from src.utils.logger import get_logger

logger = get_logger(__name__)

try:
    from langchain_chroma import Chroma
except Exception:  # pragma: no cover
    from langchain_community.vectorstores import Chroma

class RAGRetriever:
    """
    Minimal multi-collection retriever for Chroma.
    - collections: e.g. ("pdf_text", "pdf_tables", "pdf_images")
    - embeddings: your embeddings instance (e.g. GoogleGenerativeAIEmbeddings)
    """

    def __init__(
        self,
        embeddings,
        model_name: str,
        api_key: str,
        system_prompt: str,
        persist_dir: str = "chroma_db",
        collections: Sequence[str] = ("pdf_text", "pdf_tables", "pdf_images"),
        k_each: int = 4,
    ) -> None:
        self.embeddings = embeddings
        self.persist_dir = persist_dir
        self.collections = list(collections)
        self.k_each = k_each
        logger.info(f"Initializing RAGRetriever with collections: {collections}, persist_dir: {persist_dir}")
        self.model = GeminiClient(api_key=api_key, system_prompt=system_prompt, model=model_name)

    def _store(self, name: str) -> Chroma:
        return Chroma(
            collection_name=name,
            persist_directory=self.persist_dir,
            embedding_function=self.embeddings,
        )

    def retrieve_context(
        self,
        query: str,
        *,
        k_each: Optional[int] = None,
        top_n: int = 6,
    ) -> List[Dict[str, Any]]:
        """
        Search each collection for `k_each` hits and return top_n globally (by distance).
        Returns a list of dicts: {collection, doc, score}
        """
        start_time = time.time()
        k = k_each or self.k_each
        logger.info(f"Retrieving context for query (k_each={k}, top_n={top_n})")
        logger.debug(f"Query: {query[:100]}...")

        ctx: List[Dict[str, Any]] = []
        for name in self.collections:
            store = self._store(name)
            coll_start = time.time()
            results = store.similarity_search_with_score(query, k=k)
            coll_time = time.time() - coll_start

            for doc, score in results:
                ctx.append({"collection": name, "doc": doc, "score": float(score)})

            logger.debug(f"Collection '{name}': {len(results)} results in {coll_time:.2f}s")

        ctx.sort(key=lambda x: x["score"])  # lower distance = better
        top_results = ctx[:top_n]

        elapsed = time.time() - start_time
        logger.info(f"Retrieved {len(top_results)} documents in {elapsed:.2f}s (from {len(ctx)} total hits)")

        return top_results

    def format_context(
        self,
        snips: Sequence[Dict[str, Any]],
        *,
        max_chars_per_chunk: int = 1200,
    ) -> List[str]:
        """
        Human-readable block for prompting. Truncates chunk text to avoid huge prompts.
        """
        blocks: List[str] = []
        for s in snips:
            doc = s["doc"]
            name = s["collection"]
            m = doc.metadata or {}
            src = m.get("file_name") or m.get("pdf_path") or ""
            page = m.get("page")
            text = (doc.page_content or "").strip()
            if max_chars_per_chunk and len(text) > max_chars_per_chunk:
                text = text[:max_chars_per_chunk] + " …"
            blocks.append(f"[{name} p{page}] {text}\n(Source: {src})")
        return blocks

    def answer(
        self,
        query: str,
        *,
        k_each: Optional[int] = None,
        top_n: int = 6,
        max_chars_per_chunk: int = 1200,
    ):
        """
        Retrieve → format → answer (Gemini).
        Returns (answer_text, hits, formatted_context).
        """
        logger.info(f"Answering query: {query[:100]}...")
        start_time = time.time()

        snips = self.retrieve_context(query, k_each=k_each, top_n=top_n)
        context = self.format_context(snips, max_chars_per_chunk=max_chars_per_chunk)

        logger.debug(f"Formatted {len(context)} context chunks")

        PROMPT = human_question(query, context)
        resp = self.model.generate(PROMPT)

        # Fix: Handle both string response and object response
        if hasattr(resp, 'content'):
            answer_text = resp.content
        else:
            answer_text = str(resp)  # resp is already a string

        elapsed = time.time() - start_time
        logger.info(f"Answer generated in {elapsed:.2f}s (answer length: {len(answer_text)} chars)")

        return answer_text, snips, context