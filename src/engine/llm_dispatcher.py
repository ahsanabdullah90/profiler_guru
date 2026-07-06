
from google import genai

from src.utils.api_utils import retry_api_call
from src.utils.config import config
from src.utils.logger import logger
from src.utils.ollama_client import ollama_client


class LLMDispatchError(Exception):
    """Raised when LLM dispatching, generation, or configuration fails."""
    pass


class LLMDispatcher:
    _cached_clients = {}

    def _get_gemini_client(self, api_key: str):
        cache_key = f"gemini:{api_key}"
        if cache_key not in self._cached_clients:
            self._cached_clients[cache_key] = genai.Client(api_key=api_key)
        return self._cached_clients[cache_key]

    def dispatch(self, prompt: str, token_budget: int, force_cloud: bool = False, provider: str | None = None, ollama_model: str | None = None, user_consent: bool = False) -> str:
        """Dispatches the prompt to the appropriate LLM based on token budget, preferences, and availability.
        
        Raises LLMDispatchError if the generation fails or is misconfigured.
        """
        active_provider = provider or config.ACTIVE_PROVIDER or "ollama"
        use_cloud = active_provider in ("gemini", "anthropic", "openai", "opencode_go", "opencode_zen")
        use_cloud = use_cloud or force_cloud or (token_budget > config.PERSONA_ASSESS_MAX_LOCAL_TOKENS)

        if use_cloud:
            if not user_consent:
                logger.warning(f"Cloud LLM ({active_provider}) requested, but user consent was not given. Falling back to local Ollama.")
                return self._call_local(prompt, ollama_model)

            if not config.ENABLE_CLOUD_AI:
                raise LLMDispatchError("Cloud AI processing is disabled in the application configuration.")

            if active_provider == "gemini":
                return self._call_gemini(prompt)
            elif active_provider == "anthropic":
                return self._call_anthropic(prompt)
            elif active_provider in ("openai", "opencode_go", "opencode_zen"):
                return self._call_openai(prompt, active_provider)
            else:
                raise LLMDispatchError(f"Unknown provider: {active_provider}")
        else:
            return self._call_local(prompt, ollama_model)

    def _call_gemini(self, prompt: str) -> str:
        api_key = config.GOOGLE_API_KEY or config.CLOUD_API_KEY
        if not api_key:
            raise LLMDispatchError("Gemini API key is not configured.")
        model = config.GEMINI_MODEL
        try:
            client = self._get_gemini_client(api_key)
            logger.info(f"Dispatching to Gemini ({model})...")
            response = retry_api_call(client.models.generate_content, model=model, contents=prompt)
            if not response or not response.text:
                raise LLMDispatchError("Gemini returned an empty response.")
            return str(response.text)
        except Exception as e:
            logger.error(f"Gemini dispatch failed: {e}")
            raise LLMDispatchError(f"Gemini request failed. Details: {str(e)}")

    def _call_anthropic(self, prompt: str) -> str:
        import anthropic
        api_key = config.ANTHROPIC_API_KEY
        if not api_key:
            raise LLMDispatchError("Anthropic API key is not configured.")
        model = config.ANTHROPIC_MODEL
        try:
            client = anthropic.Anthropic(api_key=api_key)
            logger.info(f"Dispatching to Anthropic ({model})...")
            response = retry_api_call(
                client.messages.create,
                model=model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(block.text for block in response.content if block.type == "text")
            if not text:
                raise LLMDispatchError("Anthropic returned an empty response.")
            return text
        except Exception as e:
            logger.error(f"Anthropic dispatch failed: {e}")
            raise LLMDispatchError(f"Anthropic request failed. Details: {str(e)}")

    def _call_openai(self, prompt: str, provider: str = "openai") -> str:
        import openai
        key_map = {
            "openai": ("OPENAI_API_KEY", config.OPENAI_API_KEY, None),
            "opencode_go": ("OPENGODE_GO_API_KEY", config.OPENGODE_GO_API_KEY, config.OPENGODE_GO_BASE_URL),
            "opencode_zen": ("OPENGODE_ZEN_API_KEY", config.OPENGODE_ZEN_API_KEY, config.OPENGODE_ZEN_BASE_URL),
        }
        env_name, api_key, base_url = key_map.get(provider, key_map["openai"])
        if not api_key:
            raise LLMDispatchError(f"{env_name} is not configured.")
        model = getattr(config, f"{provider.upper()}_MODEL", "gpt-4o")
        try:
            kwargs = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            client = openai.OpenAI(**kwargs)
            logger.info(f"Dispatching to {provider} ({model})...")
            response = retry_api_call(
                client.chat.completions.create,
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.choices[0].message.content or ""
            if not text:
                raise LLMDispatchError(f"{provider} returned an empty response.")
            return text
        except Exception as e:
            logger.error(f"{provider} dispatch failed: {e}")
            raise LLMDispatchError(f"{provider} request failed. Details: {str(e)}")

    def _call_local(self, prompt: str, ollama_model: str | None = None) -> str:
        target_model = ollama_model or config.OLLAMA_MODEL
        logger.info(f"Dispatching request to local Ollama model '{target_model}'...")
        try:
            return retry_api_call(ollama_client.generate, target_model, prompt)
        except Exception as e:
            logger.error(f"Local Ollama dispatch failed: {e}")
            raise LLMDispatchError(f"Local Ollama model '{target_model}' is not reachable or failed to generate. Please ensure Ollama is running locally and the model is installed. Details: {str(e)}")

    def dispatch_stream(self, prompt: str, token_budget: int, force_cloud: bool = False, provider: str | None = None, ollama_model: str | None = None, user_consent: bool = False):
        """Streams the LLM response tokens based on token budget and provider preferences."""
        active_provider = provider or config.ACTIVE_PROVIDER or "ollama"
        use_cloud = active_provider in ("gemini", "anthropic", "openai", "opencode_go", "opencode_zen")
        use_cloud = use_cloud or force_cloud or (token_budget > config.PERSONA_ASSESS_MAX_LOCAL_TOKENS)

        if use_cloud:
            if not user_consent:
                logger.warning(f"Cloud LLM ({active_provider}) requested/required, but user consent was not given. Falling back to local Ollama.")
                yield from self._call_local_stream(prompt, ollama_model)
                return

            if not config.ENABLE_CLOUD_AI:
                raise LLMDispatchError("Cloud AI processing is disabled in the application configuration.")

            if active_provider == "gemini":
                yield from self._call_gemini_stream(prompt)
            elif active_provider == "anthropic":
                yield from self._call_anthropic_stream(prompt)
            elif active_provider in ("openai", "opencode_go", "opencode_zen"):
                yield from self._call_openai_stream(prompt, active_provider)
            else:
                raise LLMDispatchError(f"Unknown provider: {active_provider}")
        else:
            yield from self._call_local_stream(prompt, ollama_model)

    def _call_gemini_stream(self, prompt: str):
        api_key = config.GOOGLE_API_KEY or config.CLOUD_API_KEY
        if not api_key:
            raise LLMDispatchError("Gemini API key is not configured.")
        model = config.GEMINI_MODEL
        try:
            client = self._get_gemini_client(api_key)
            response_stream = client.models.generate_content_stream(model=model, contents=prompt)
            for chunk in response_stream:
                if chunk and chunk.text:
                    yield chunk.text
        except Exception as e:
            logger.error(f"Gemini streaming dispatch failed: {e}")
            raise LLMDispatchError(f"Gemini request failed. Details: {str(e)}")

    def _call_anthropic_stream(self, prompt: str):
        import anthropic
        api_key = config.ANTHROPIC_API_KEY
        if not api_key:
            raise LLMDispatchError("Anthropic API key is not configured.")
        model = config.ANTHROPIC_MODEL
        try:
            client = anthropic.Anthropic(api_key=api_key)
            with client.messages.stream(
                model=model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                for text in stream.text_stream:
                    yield text
        except Exception as e:
            logger.error(f"Anthropic streaming dispatch failed: {e}")
            raise LLMDispatchError(f"Anthropic request failed. Details: {str(e)}")

    def _call_openai_stream(self, prompt: str, provider: str = "openai"):
        import openai
        key_map = {
            "openai": ("OPENAI_API_KEY", config.OPENAI_API_KEY, None),
            "opencode_go": ("OPENGODE_GO_API_KEY", config.OPENGODE_GO_API_KEY, config.OPENGODE_GO_BASE_URL),
            "opencode_zen": ("OPENGODE_ZEN_API_KEY", config.OPENGODE_ZEN_API_KEY, config.OPENGODE_ZEN_BASE_URL),
        }
        _, api_key, base_url = key_map.get(provider, key_map["openai"])
        if not api_key:
            raise LLMDispatchError(f"API key not configured for {provider}.")
        model = getattr(config, f"{provider.upper()}_MODEL", "gpt-4o")
        try:
            kwargs = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            client = openai.OpenAI(**kwargs)
            stream = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    yield delta.content
        except Exception as e:
            logger.error(f"{provider} streaming dispatch failed: {e}")
            raise LLMDispatchError(f"{provider} request failed. Details: {str(e)}")

    def _call_local_stream(self, prompt: str, ollama_model: str | None = None):
        target_model = ollama_model or config.OLLAMA_MODEL
        logger.info(f"Dispatching streaming request to local Ollama model '{target_model}'...")
        try:
            yield from ollama_client.generate_stream(target_model, prompt)
        except Exception as e:
            logger.error(f"Local Ollama streaming failed: {e}")
            raise LLMDispatchError(f"Local Ollama model '{target_model}' streaming failed. Details: {str(e)}")


from src.utils.lazy_proxy import LazyProxy

llm_dispatcher = LazyProxy(LLMDispatcher)
