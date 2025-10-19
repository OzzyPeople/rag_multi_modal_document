#run_retrieval.py
from __future__ import annotations
import argparse
import os
import logging
from dotenv import load_dotenv

from src.embedding.google_embed import get_google_embeddings
from src.retriever.retriever_collection import RAGRetriever
from src.prompts.system_prompt import SCIENTIFIC_ANALYST
from src.evaluation.evaluate_rag import evaluate_response
from src.utils.logger import get_logger, set_log_level

logger = get_logger(__name__)

def main(SYSTEM_PROMPT: str = SCIENTIFIC_ANALYST):
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", type=str,
                        default="Explain scaled dot-product attention.")
    parser.add_argument("--evaluate", action="store_true")
    parser.add_argument("--model", type=str,
                        default=os.getenv("MODEL_NAME", "gemini-2.0-flash"))
    parser.add_argument("--persist", type=str,
                        default=os.getenv("CHROMA_DIR", "chroma_db"))
    parser.add_argument("--k-each", type=int, default=4)
    parser.add_argument("--show-context", action="store_true")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    # Set log level based on debug flag
    if args.debug:
        set_log_level(logger, logging.DEBUG)
        logger.info("Debug logging enabled")

    logger.info(f"Starting retrieval with model: {args.model}")

    api_key = os.getenv("MODEL_API_KEY")
    if not api_key:
        logger.error("MODEL_API_KEY environment variable is not set")
        raise RuntimeError("MODEL_API_KEY is not set")

    logger.info("Initializing embeddings...")

    emb = get_google_embeddings(model="models/text-embedding-004")
    rag = RAGRetriever(
        embeddings=emb,
        model_name=args.model,
        api_key=api_key,
        system_prompt=SYSTEM_PROMPT,
        persist_dir=args.persist
    )

    answer, hits, ctx = rag.answer(
        args.question,
        k_each=args.k_each,
    )
    print("\n" + "="*50)
    print("ANSWER")
    print("="*50)
    print(answer.encode('utf-8', errors='replace').decode('utf-8'))
    print("="*50 + "\n")

    if args.show_context:
        print("\n" + "="*50)
        print("CONTEXT")
        print("="*50)
        print(ctx)
        print("="*50 + "\n")

    # Evaluate
    if args.evaluate:
        logger.info("Starting evaluation...")
        eval_result = evaluate_response(
            question=args.question,
            answer=answer,
            contexts=hits,
            api_key=api_key,
        )
        print("\n" + "="*50)
        print("EVALUATION")
        print("="*50)
        for metric, value in eval_result.items():
            if value is not None:
                print(f"{metric}: {value:.4f}")
            else:
                print(f"{metric}: N/A")
        print("="*50 + "\n")

    logger.info("Retrieval completed successfully")

if __name__ == "__main__":
    main()

#poetry run python -m src.retriever.run_retrieval --question "Explain scaled dot-product attention." --show-context
#poetry run python -m src.retriever.run_retrieval --question "What is attention mechanism?" --evaluate