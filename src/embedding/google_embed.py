import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings

def get_google_embeddings(
    model: str = "models/text-embedding-004",
    api_key: str | None = None,
):
    """
    Returns a GoogleGenerativeAIEmbeddings instance.

    Args:
        model (str): Embedding model. Examples:
                     - "models/text-embedding-004" (newer)
                     - "models/embedding-001" (older)
        api_key (str|None): Google API key. If None, falls back to
                            GOOGLE_API_KEY env var.
    """
    if api_key is None:
        api_key = os.getenv("MODEL_API_KEY")
        if not api_key:
            raise ValueError(
                "Google API key not provided. "
                "Pass api_key=... or set GOOGLE_API_KEY in your environment."
            )

    return GoogleGenerativeAIEmbeddings(
        model=model,
        google_api_key=api_key
    )