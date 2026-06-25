import time
from src.utils.logger import logger

def retry_api_call(func, *args, retries=3, **kwargs):
    """Executes an API call with exponential backoff (2s, 4s, 8s)."""
    delay = 2
    for attempt in range(retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt == retries:
                logger.error(f"API call failed after {retries} retries: {e}")
                raise e
            logger.warning(f"API call failed: {e}. Retrying in {delay}s (Attempt {attempt + 1}/{retries})...")
            time.sleep(delay)
            delay *= 2
