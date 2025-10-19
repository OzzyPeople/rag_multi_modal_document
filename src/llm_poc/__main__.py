
from langchain_chroma import Chroma
from src.embedding.google_embed import get_google_embeddings
import os
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("MODEL_API_KEY")

emb = get_google_embeddings(model="models/text-embedding-004", api_key=API_KEY)
store = Chroma(
    collection_name="pdf_images",
    persist_directory="chroma_db",
    embedding_function=emb,
)

docs = store.get()  # get all or use where={"pdf_path": "data/transformer_article.pdf"}


if __name__ == "__main__":
    for meta, doc in zip(docs["metadatas"], docs["documents"]):
        print("\nFILE:", meta.get("source"))
        print("CONTENT:", doc[:400])

#poetry run python -m src.llm_poc

