# Logging Quick Start

## TL;DR

Logging is now enabled across the project! Logs go to:
- **Console** (your terminal)
- **File**: `logs/rag_YYYYMMDD.log`
- **Errors**: `logs/errors.log`

## Quick Examples

### Run with logging
```bash
# Normal mode (INFO level)
poetry run python -m src.retriever.run_retrieval --question "What is attention?" --evaluate

# Debug mode (more verbose)
poetry run python -m src.retriever.run_retrieval --question "What is attention?" --evaluate --debug
```

### Add logging to your code
```python
from src.utils.logger import get_logger

logger = get_logger(__name__)

logger.info("Something happened")
logger.error("Something went wrong", exc_info=True)
```

## What You'll See

### Console Output (Clean, user-facing)
```
==================================================
ANSWER
==================================================
The attention mechanism maps queries to key-value pairs...
==================================================

==================================================
EVALUATION
==================================================
faithfulness: 0.8542
answer_relevancy: 0.9123
==================================================
```

### Log File Output (Detailed, for debugging)
```
2025-01-19 10:30:45 | INFO     | src.retriever.retriever_collection | Initializing RAGRetriever with collections: ('pdf_text', 'pdf_tables', 'pdf_images')
2025-01-19 10:30:45 | INFO     | src.clients.gemini_client | Initializing GeminiClient with model: gemini-2.0-flash
2025-01-19 10:30:46 | INFO     | src.retriever.retriever_collection | Retrieving context for query (k_each=4, top_n=6)
2025-01-19 10:30:46 | INFO     | src.retriever.retriever_collection | Retrieved 6 documents in 0.35s
2025-01-19 10:30:46 | INFO     | src.clients.gemini_client | Starting text generation (prompt length: 1234 chars)
2025-01-19 10:30:48 | INFO     | src.clients.gemini_client | Generation completed in 2.15s (response: 567 chars)
2025-01-19 10:30:50 | INFO     | src.evaluation.evaluate_rag | Starting RAG evaluation
2025-01-19 10:31:05 | INFO     | src.evaluation.evaluate_rag | Evaluation completed in 15.23s
2025-01-19 10:31:05 | INFO     | src.evaluation.evaluate_rag | Results - Faithfulness: 0.8542, Answer Relevancy: 0.9123
```

## What Gets Logged

✅ **API Calls**: Timing, request/response sizes, errors
✅ **Performance**: Execution time for all major operations
✅ **Evaluation**: RAGAS metrics and timing
✅ **Retrieval**: Number of documents, search timing
✅ **Errors**: Full stack traces in error log

## View Logs

```bash
# View today's main log
cat logs/rag_$(date +%Y%m%d).log

# View recent logs (live tail)
tail -f logs/rag_*.log

# View only errors
cat logs/errors.log
```

For more details, see [LOGGING.md](./LOGGING.md)

