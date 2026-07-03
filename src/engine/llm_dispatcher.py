
from google import genai

from src.utils.api_utils import retry_api_call
from src.utils.config import config
from src.utils.logger import logger
from src.utils.ollama_client import ollama_client


class LLMDispatchError(Exception):
    """Raised when LLM dispatching, generation, or configuration fails."""
    pass


class LLMDispatcher:
    _cached_client = None
    _cached_client_key = None

    def _get_cloud_client(self, api_key: str):
        """Return a cached genai.Client, creating a new one if the API key changed."""
        if self._cached_client_key != api_key:
            self._cached_client = genai.Client(api_key=api_key)
            self._cached_client_key = api_key
        return self._cached_client

    def dispatch(self, prompt: str, token_budget: int, force_cloud: bool = False, provider: str | None = None, ollama_model: str | None = None, user_consent: bool = False) -> str:
        """Dispatches the prompt to the appropriate LLM based on token budget, preferences, and availability.
        
        Raises LLMDispatchError if the generation fails or is misconfigured.
        """
        # Determine if cloud is required or requested
        use_cloud = force_cloud or (token_budget > config.PERSONA_ASSESS_MAX_LOCAL_TOKENS) or (provider == "gemini")

        if use_cloud:
            if not user_consent:
                logger.warning("Cloud LLM requested/required, but user consent was not given. Falling back to local Ollama.")
                return self._call_local(prompt, ollama_model)

            if not config.ENABLE_CLOUD_AI:
                raise LLMDispatchError("Cloud AI processing is disabled in the application configuration.")

            # Get API key (prioritizing config which might be updated dynamically by settings manager)
            api_key = config.CLOUD_API_KEY
            if not api_key:
                raise LLMDispatchError("Cloud API Key is not configured. Please set your API key in the Settings tab.")

            try:
                client = self._get_cloud_client(api_key)

                logger.info(f"Dispatching request to Cloud Gemini (budget: {token_budget} tokens)...")
                response = retry_api_call(client.models.generate_content, model='gemini-1.5-flash', contents=prompt)
                if not response or not response.text:
                    raise LLMDispatchError("Cloud Gemini returned an empty response.")
                return str(response.text)
            except Exception as e:
                logger.error(f"Cloud Gemini dispatch failed: {e}")
                raise LLMDispatchError(f"Cloud Gemini request failed. Details: {str(e)}")
        else:
            return self._call_local(prompt, ollama_model)

    def _call_local(self, prompt: str, ollama_model: str | None = None) -> str:
        target_model = ollama_model or config.OLLAMA_MODEL
        logger.info(f"Dispatching request to local Ollama model '{target_model}'...")
        try:
            return retry_api_call(ollama_client.generate, target_model, prompt)
        except Exception as e:
            logger.error(f"Local Ollama dispatch failed: {e}")
            raise LLMDispatchError(f"Local Ollama model '{target_model}' is not reachable or failed to generate. Please ensure Ollama is running locally and the model is installed. Details: {str(e)}")

from src.utils.lazy_proxy import LazyProxy

llm_dispatcher = LazyProxy(LLMDispatcher)
