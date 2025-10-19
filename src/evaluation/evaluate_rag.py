import time
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from datasets import Dataset
from src.utils.logger import get_logger

logger = get_logger(__name__)


def evaluate_response(
        question: str,
        answer: str,
        contexts: list,  # List of retrieved chunks
        api_key: str,
        model: str = "gemini-2.0-flash-exp"
) -> dict:
    """
    Evaluate a RAG response using RAGAS metrics with Gemini Flash.

    Args:
        question: User's question
        answer: Generated answer
        contexts: List of retrieved text chunks
        api_key: Google API key
        model: Gemini model name

    Returns:
        Dictionary with evaluation scores
    """
    start_time = time.time()
    logger.info(f"Starting RAG evaluation with model: {model}")
    logger.debug(f"Question: {question[:100]}...")

    # Create evaluator LLM
    evaluator_llm = ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
        temperature=0,
        max_output_tokens=2048
    )

    # Create embeddings for RAGAS
    evaluator_embeddings = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004",
        google_api_key=api_key
    )

    # Wrap for RAGAS
    ragas_llm = LangchainLLMWrapper(evaluator_llm)
    ragas_embeddings = LangchainEmbeddingsWrapper(evaluator_embeddings)

    # Configure metrics
    # Note: context_precision requires ground truth 'reference' which we don't have
    faithfulness.llm = ragas_llm
    answer_relevancy.llm = ragas_llm
    answer_relevancy.embeddings = ragas_embeddings

    # Convert contexts to expected format
    # contexts should be List[str] where each string is a retrieved chunk
    if isinstance(contexts, list) and len(contexts) > 0:
        if hasattr(contexts[0], 'page_content'):  # If LangChain Document objects
            context_texts = [str(doc.page_content) for doc in contexts]
        else:
            context_texts = [str(ctx) for ctx in contexts]
    else:
        context_texts = []

    # Ensure all contexts are strings
    context_texts = [str(ctx) if not isinstance(ctx, str) else ctx for ctx in context_texts]
    logger.info(f"Prepared {len(context_texts)} context chunks for evaluation")

    # Run evaluation
    try:
        # Create dataset in the format RAGAS expects
        dataset = Dataset.from_dict({
            'question': [question],
            'answer': [answer],
            'contexts': [context_texts]  # List of lists of strings
        })

        logger.info("Running RAGAS evaluation (this may take a while)...")
        eval_start = time.time()
        results = evaluate(
            dataset=dataset,
            metrics=[faithfulness, answer_relevancy],
            llm=ragas_llm,
            embeddings=ragas_embeddings
        )
        eval_time = time.time() - eval_start

        # Extract scalar values from RAGAS results (returns lists)
        faithfulness_score = results['faithfulness']
        answer_relevancy_score = results['answer_relevancy']

        # Handle both list and scalar returns
        if isinstance(faithfulness_score, list):
            faithfulness_score = faithfulness_score[0] if faithfulness_score else None
        if isinstance(answer_relevancy_score, list):
            answer_relevancy_score = answer_relevancy_score[0] if answer_relevancy_score else None

        result_dict = {
            'faithfulness': faithfulness_score,
            'answer_relevancy': answer_relevancy_score
        }

        total_time = time.time() - start_time
        logger.info(f"Evaluation completed in {total_time:.2f}s (RAGAS: {eval_time:.2f}s)")
        if faithfulness_score is not None and answer_relevancy_score is not None:
            logger.info(f"Results - Faithfulness: {faithfulness_score:.4f}, Answer Relevancy: {answer_relevancy_score:.4f}")
        else:
            logger.warning(f"Results - Faithfulness: {faithfulness_score}, Answer Relevancy: {answer_relevancy_score}")

        return result_dict
    except Exception as e:
        import traceback
        total_time = time.time() - start_time
        logger.error(f"Evaluation failed after {total_time:.2f}s: {e}")
        logger.debug(traceback.format_exc())
        return {
            'faithfulness': None,
            'answer_relevancy': None
        }