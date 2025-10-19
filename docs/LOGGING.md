# Logging Documentation

## Overview

The RAG Multi-Doc project uses Python's built-in `logging` module with a centralized configuration for consistent logging across all components.

## Features

- **Console + File Output**: Logs are displayed in the terminal and saved to files
- **Automatic Log Rotation**: Log files rotate at 10MB, keeping 5 backup files
- **Separate Error Logs**: Errors are written to both main log and a dedicated error log
- **Performance Tracking**: API calls, retrieval operations, and evaluations include timing information
- **Configurable Verbosity**: Easy to switch between INFO and DEBUG levels

## Log Files Location

All logs are stored in the `logs/` directory:

```
logs/
├── rag_YYYYMMDD.log    # Main log file (daily rotation by date)
└── errors.log           # Error-only log file
```

## Usage

### Basic Usage

```python
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Log messages at different levels
logger.debug("Detailed debugging information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred", exc_info=True)  # Include stack trace
logger.critical("Critical failure")
```

### Command Line

Enable debug logging with the `--debug` flag:

```bash
# Normal logging (INFO level)
poetry run python -m src.retriever.run_retrieval --question "Your question"

# Debug logging (DEBUG level - more verbose)
poetry run python -m src.retriever.run_retrieval --question "Your question" --debug
```

### Changing Log Levels Programmatically

```python
import logging
from src.utils.logger import get_logger, set_log_level

logger = get_logger(__name__)

# Change to DEBUG level
set_log_level(logger, logging.DEBUG)

# Change to WARNING level (less verbose)
set_log_level(logger, logging.WARNING)
```

## What Gets Logged

### API Calls (LLM & Embeddings)
- Model initialization
- Request timing and payload size
- Response size and generation time
- API failures with stack traces

Example log output:
```
2025-01-19 10:30:45 | INFO     | src.clients.gemini_client | Initializing GeminiClient with model: gemini-2.0-flash
2025-01-19 10:30:46 | INFO     | src.clients.gemini_client | Starting text generation (prompt length: 1234 chars)
2025-01-19 10:30:48 | INFO     | src.clients.gemini_client | Generation completed in 2.15s (response: 567 chars)
```

### Retrieval Operations
- Query processing
- Per-collection search timing
- Number of results retrieved
- Total retrieval time

Example log output:
```
2025-01-19 10:30:50 | INFO     | src.retriever.retriever_collection | Retrieving context for query (k_each=4, top_n=6)
2025-01-19 10:30:51 | DEBUG    | src.retriever.retriever_collection | Collection 'pdf_text': 4 results in 0.12s
2025-01-19 10:30:51 | DEBUG    | src.retriever.retriever_collection | Collection 'pdf_images': 4 results in 0.09s
2025-01-19 10:30:51 | INFO     | src.retriever.retriever_collection | Retrieved 6 documents in 0.35s (from 12 total hits)
```

### Evaluation Metrics
- Evaluation start and completion
- Number of contexts processed
- RAGAS execution time
- Final metric scores

Example log output:
```
2025-01-19 10:31:00 | INFO     | src.evaluation.evaluate_rag | Starting RAG evaluation with model: gemini-2.0-flash-exp
2025-01-19 10:31:01 | INFO     | src.evaluation.evaluate_rag | Prepared 6 context chunks for evaluation
2025-01-19 10:31:15 | INFO     | src.evaluation.evaluate_rag | Evaluation completed in 15.23s (RAGAS: 14.87s)
2025-01-19 10:31:15 | INFO     | src.evaluation.evaluate_rag | Results - Faithfulness: 0.8542, Answer Relevancy: 0.9123
```

### Performance Metrics
Every logged operation includes timing information to help identify bottlenecks:
- API response times
- Database query times
- Total pipeline execution time

## Log Format

### Standard Format (INFO level)
```
YYYY-MM-DD HH:MM:SS | LEVEL    | module.name | message
```

### Detailed Format (DEBUG level)
```
YYYY-MM-DD HH:MM:SS | LEVEL    | module.name:function_name:line_number | message
```

## Configuration

### Custom Logger Setup

```python
from src.utils.logger import setup_logger
import logging

# Create custom logger with specific settings
logger = setup_logger(
    name=__name__,
    level=logging.DEBUG,
    log_to_file=True,
    log_to_console=True,
    detailed=True  # Include function names and line numbers
)
```

### Silencing Third-Party Libraries

The logger automatically reduces verbosity of noisy libraries:
- `urllib3`
- `httpx`
- `chromadb`
- `google`
- `langchain`

These are set to WARNING level by default.

## Best Practices

1. **Use appropriate log levels**:
   - `DEBUG`: Detailed diagnostic information
   - `INFO`: Confirmation that things are working as expected
   - `WARNING`: Something unexpected happened, but the software is still working
   - `ERROR`: A serious problem occurred
   - `CRITICAL`: The program may not be able to continue

2. **Include context in messages**:
   ```python
   # Good
   logger.info(f"Retrieved {len(results)} documents in {elapsed:.2f}s")

   # Less helpful
   logger.info("Documents retrieved")
   ```

3. **Log exceptions with stack traces**:
   ```python
   try:
       risky_operation()
   except Exception as e:
       logger.error(f"Operation failed: {e}", exc_info=True)
   ```

4. **Don't log sensitive information**:
   ```python
   # Bad - exposes API key
   logger.info(f"Using API key: {api_key}")

   # Good
   logger.info("API key loaded successfully")
   ```

## Troubleshooting

### Logs not appearing
- Check if `logs/` directory exists
- Verify file permissions
- Check that logger is imported: `from src.utils.logger import get_logger`

### Too much output
- Use `--debug` flag only when needed
- Adjust log level: `set_log_level(logger, logging.WARNING)`

### Log files growing too large
- Current rotation is set at 10MB with 5 backups
- Modify `maxBytes` and `backupCount` in `src/utils/logger.py` if needed

## Examples

### Example 1: Basic Logging in a New Module

```python
# my_module.py
from src.utils.logger import get_logger

logger = get_logger(__name__)

def process_data(data):
    logger.info(f"Processing {len(data)} items")
    try:
        result = expensive_operation(data)
        logger.info("Processing completed successfully")
        return result
    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        raise
```

### Example 2: Conditional Debug Logging

```python
from src.utils.logger import get_logger
import logging

logger = get_logger(__name__)

def complex_function(debug=False):
    if debug:
        set_log_level(logger, logging.DEBUG)

    logger.debug("Starting complex operation")
    logger.info("Operation in progress")
    logger.debug("Intermediate result: ...")
```

### Example 3: Performance Logging

```python
import time
from src.utils.logger import get_logger

logger = get_logger(__name__)

def timed_operation():
    start = time.time()
    logger.info("Starting timed operation")

    # Your code here
    result = do_something()

    elapsed = time.time() - start
    logger.info(f"Operation completed in {elapsed:.2f}s")
    return result
```

## Summary

The logging system is designed to provide:
- **Transparency**: See what's happening at each step
- **Performance insights**: Track timing of operations
- **Debugging capability**: Detailed traces when things go wrong
- **Production readiness**: Automatic rotation and error tracking

For questions or issues, check the main log file in `logs/rag_YYYYMMDD.log`.
