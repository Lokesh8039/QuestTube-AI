import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Global thread pool for executing background operations without Celery/Redis
_executor = ThreadPoolExecutor(max_workers=4)

def run_background_task(task_func, *args, **kwargs):
    """
    Submits a function to be executed in a background thread.
    Useful for running long operations (like transcript scraping and embedding generation)
    without blocking the HTTP request-response cycle.
    """
    logger.info(f"Submitting background task: {task_func.__name__} with args: {args}, kwargs: {kwargs}")
    return _executor.submit(task_func, *args, **kwargs)
