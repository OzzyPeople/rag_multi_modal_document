# src/rag/retriever.py
from __future__ import annotations
from typing import Sequence, Optional, Dict, Any, List

# Prefer the new package; fall back if you haven't migrated yet.
try:
    from langchain_chroma import Chroma
except Exception:  # pragma: no cover
    from langchain_community.vectorstores import Chroma  # deprecated path

from langchain_google_genai import ChatGoogleGenerativeAI


class RAGRetriever:
    """
    Minimal multi-collection retriever for Chroma.
    - collections: e.g. ("pdf_text", "pdf_tables", "pdf_images")
    - embeddings: your embeddings instance (e.g. GoogleGenerativeAIEmbeddings)
    """

    def __init__(
        self,
        embeddings,
        persist_dir: str = "chroma_db",
        collections: Sequence[str] = ("pdf_text", "pdf_tables", "pdf_images"),
        k_each: int = 4,
    ) -> None:
        self.embeddings = embeddings
        self.persist_dir = persist_dir
        self.collections = list(collections)
        self.k_each = k_each

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
        k = k_each or self.k_each
        ctx: List[Dict[str, Any]] = []
        for name in self.collections:
            store = self._store(name)
            for doc, score in store.similarity_search_with_score(query, k=k):
                ctx.append({"collection": name, "doc": doc, "score": float(score)})
        ctx.sort(key=lambda x: x["score"])  # lower distance = better
        return ctx[:top_n]

    def format_context(
        self,
        snips: Sequence[Dict[str, Any]],
        *,
        max_chars_per_chunk: int = 1200,
    ) -> str:
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
        return "\n\n---\n\n".join(blocks)

    def answer(
        self,
        query: str,
        *,
        api_key: Optional[str] = None,
        llm: Optional[ChatGoogleGenerativeAI] = None,
        system_prompt: Optional[str] = None,
        k_each: Optional[int] = None,
        top_n: int = 6,
        max_chars_per_chunk: int = 1200,
    ):
        """
        Retrieve → format → answer (Gemini).
        Returns (answer_text, hits, formatted_context).
        """
        snips = self.retrieve_context(query, k_each=k_each, top_n=top_n)
        context = self.format_context(snips, max_chars_per_chunk=max_chars_per_chunk)

        if llm is None:
            if api_key is None:
                raise ValueError("Provide api_key=... or pass a pre-built llm=ChatGoogleGenerativeAI(...)")
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                google_api_key=api_key,
                temperature=0.2,
            )

        system = system_prompt or (
            "You are a helpful assistant. Use ONLY the provided context to answer. "
            "Cite page numbers shown in brackets like [pdf_text p5]. If unknown, say so."
        )
        msgs = [("system", system), ("human", f"Question: {query}\n\nContext:\n{context}")]
        resp = llm.invoke(msgs)
        return resp.content, snips, context