import google.generativeai as genai
from src.utils.config import config
from src.utils.logger import logger
from src.utils.ollama_client import ollama_client
import time

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

class LLMDispatcher:
    def dispatch(self, prompt: str, token_budget: int, force_cloud: bool = False, provider: str = None, ollama_model: str = None, user_consent: bool = False) -> str:
        """Dispatches the prompt to the appropriate LLM based on token budget, preferences, and availability."""
        # Determine if cloud is required or requested
        use_cloud = force_cloud or (token_budget > config.PERSONA_ASSESS_MAX_LOCAL_TOKENS) or (provider == "gemini")
        
        if use_cloud:
            if not user_consent:
                logger.warning("Cloud LLM requested/required, but user consent was not given. Falling back to local Ollama.")
                return self._call_local(prompt, ollama_model)
                
            if not config.ENABLE_CLOUD_AI:
                return "Error: Cloud AI processing is disabled in the application configuration."
                
            # Get API key (prioritizing config which might be updated dynamically by settings manager)
            api_key = config.CLOUD_API_KEY
            if not api_key:
                return "Error: Cloud API Key is not configured. Please set your API key in the Settings tab."
                
            try:
                # Configure dynamically to reflect any runtime updates to the API key
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                logger.info(f"Dispatching request to Cloud Gemini (budget: {token_budget} tokens)...")
                response = retry_api_call(model.generate_content, prompt)
                if not response or not response.text:
                    return "Error: Cloud Gemini returned an empty response."
                return response.text
            except Exception as e:
                logger.error(f"Cloud Gemini dispatch failed: {e}")
                return f"Error: Cloud Gemini request failed. Details: {str(e)}"
        else:
            return self._call_local(prompt, ollama_model)
            
    def _call_local(self, prompt: str, ollama_model: str = None) -> str:
        target_model = ollama_model or config.OLLAMA_MODEL
        logger.info(f"Dispatching request to local Ollama model '{target_model}'...")
        try:
            return retry_api_call(ollama_client.generate, target_model, prompt)
        except Exception as e:
            logger.error(f"Local Ollama dispatch failed: {e}")
            return f"Error: Local Ollama model '{target_model}' is not reachable or failed to generate. Please ensure Ollama is running locally and the model is installed. Details: {str(e)}"

llm_dispatcher = LLMDispatcher()
