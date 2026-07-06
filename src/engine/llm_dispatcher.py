
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

    def dispatch(self, prompt: str, token_budget: int, force_cloud: bool = False, provider: str | None = None, ollama_model: str | None = None, user_consent: bool = False, system: str | None = None) -> str:
        """Dispatches the prompt to the appropriate LLM based on token budget, preferences, and availability.

        Args:
            prompt: The user prompt text (grounding data, context, task instructions).
            system: Optional system prompt for role/safety boundaries. If provided,
                    it is passed as a separate system instruction to the LLM, strengthening
                    role enforcement. If None, behavior is unchanged (backward compatible).
        
        Raises LLMDispatchError if the generation fails or is misconfigured.
        """
        active_provider = provider or config.ACTIVE_PROVIDER or "ollama"
        use_cloud = active_provider in ("gemini", "anthropic", "openai", "opencode_go", "opencode_zen")
        use_cloud = use_cloud or force_cloud or (token_budget > config.PERSONA_ASSESS_MAX_LOCAL_TOKENS)

        if use_cloud:
            if not user_consent:
                logger.warning(f"Cloud LLM ({active_provider}) requested, but user consent was not given. Falling back to local Ollama.")
                return self._call_local(prompt, ollama_model, system=system)

            if not config.ENABLE_CLOUD_AI:
                raise LLMDispatchError("Cloud AI processing is disabled in the application configuration.")

            if active_provider == "gemini":
                return self._call_gemini(prompt, system=system)
            elif active_provider == "anthropic":
                return self._call_anthropic(prompt, system=system)
            elif active_provider in ("openai", "opencode_go", "opencode_zen"):
                return self._call_openai(prompt, active_provider, system=system)
            else:
                raise LLMDispatchError(f"Unknown provider: {active_provider}")
        else:
            return self._call_local(prompt, ollama_model, system=system)

    def _require_model(self, model_name: str, provider: str) -> None:
        """Raise a clear error if no model is configured for the provider."""
        if not model_name:
            raise LLMDispatchError(
                f"No model selected for {provider}. "
                "Go to Settings → Models to configure a model."
            )

    def _resolve_ollama_model(self, ollama_model: str | None = None) -> str:
        """Return an explicit model name, auto-selecting from installed models if needed."""
        target_model = ollama_model or config.OLLAMA_MODEL
        if target_model:
            return target_model
        try:
            installed = ollama_client.get_installed_models()
            if installed:
                return ollama_client.get_best_model(installed) or installed[0]
        except Exception as e:
            logger.warning(f"Failed to auto-select Ollama model: {e}")
        raise LLMDispatchError(
            "No Ollama model selected and none could be auto-detected. "
            "Go to Settings → Models to configure a model."
        )

    def _call_gemini(self, prompt: str, system: str | None = None) -> str:
        api_key = config.GOOGLE_API_KEY or config.CLOUD_API_KEY
        if not api_key:
            raise LLMDispatchError("Gemini API key is not configured.")
        model = config.GEMINI_MODEL
        self._require_model(model, "Gemini")
        try:
            client = self._get_gemini_client(api_key)
            logger.info(f"Dispatching to Gemini ({model})...")
            genai_kwargs = {"model": model, "contents": prompt}
            if system:
                from google.genai import types as genai_types
                genai_kwargs["config"] = genai_types.GenerateContentConfig(system_instruction=system)
            response = retry_api_call(client.models.generate_content, **genai_kwargs)
            if not response or not response.text:
                raise LLMDispatchError("Gemini returned an empty response.")
            return str(response.text)
        except Exception as e:
            logger.error(f"Gemini dispatch failed: {e}")
            raise LLMDispatchError(f"Gemini request failed. Details: {str(e)}")

    def _call_anthropic(self, prompt: str, system: str | None = None) -> str:
        import anthropic
        api_key = config.ANTHROPIC_API_KEY
        if not api_key:
            raise LLMDispatchError("Anthropic API key is not configured.")
        model = config.ANTHROPIC_MODEL
        self._require_model(model, "Anthropic")
        try:
            client = anthropic.Anthropic(api_key=api_key)
            logger.info(f"Dispatching to Anthropic ({model})...")
            create_kwargs = {
                "model": model,
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system:
                create_kwargs["system"] = system
            response = retry_api_call(client.messages.create, **create_kwargs)
            text = "".join(block.text for block in response.content if block.type == "text")
            if not text:
                raise LLMDispatchError("Anthropic returned an empty response.")
            return text
        except Exception as e:
            logger.error(f"Anthropic dispatch failed: {e}")
            raise LLMDispatchError(f"Anthropic request failed. Details: {str(e)}")

    def _call_openai(self, prompt: str, provider: str = "openai", system: str | None = None) -> str:
        import openai
        key_map = {
            "openai": ("OPENAI_API_KEY", config.OPENAI_API_KEY, None),
            "opencode_go": ("OPENGODE_GO_API_KEY", config.OPENGODE_GO_API_KEY, config.OPENGODE_GO_BASE_URL),
            "opencode_zen": ("OPENGODE_ZEN_API_KEY", config.OPENGODE_ZEN_API_KEY, config.OPENGODE_ZEN_BASE_URL),
        }
        env_name, api_key, base_url = key_map.get(provider, key_map["openai"])
        if not api_key:
            raise LLMDispatchError(f"{env_name} is not configured.")
        model = getattr(config, f"{provider.upper()}_MODEL", "")
        self._require_model(model, provider)
        try:
            kwargs = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            client = openai.OpenAI(**kwargs)
            logger.info(f"Dispatching to {provider} ({model})...")
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            response = retry_api_call(
                client.chat.completions.create,
                model=model,
                messages=messages,
            )
            text = response.choices[0].message.content or ""
            if not text:
                raise LLMDispatchError(f"{provider} returned an empty response.")
            return text
        except Exception as e:
            logger.error(f"{provider} dispatch failed: {e}")
            raise LLMDispatchError(f"{provider} request failed. Details: {str(e)}")

    def _call_local(self, prompt: str, ollama_model: str | None = None, system: str | None = None) -> str:
        target_model = self._resolve_ollama_model(ollama_model)
        logger.info(f"Dispatching request to local Ollama model '{target_model}'...")
        try:
            return retry_api_call(ollama_client.generate, target_model, prompt, system=system)
        except Exception as e:
            logger.error(f"Local Ollama dispatch failed: {e}")
            raise LLMDispatchError(f"Local Ollama model '{target_model}' is not reachable or failed to generate. Please ensure Ollama is running locally and the model is installed. Details: {str(e)}")

    def dispatch_stream(self, prompt: str, token_budget: int, force_cloud: bool = False, provider: str | None = None, ollama_model: str | None = None, user_consent: bool = False, system: str | None = None):
        """Streams the LLM response tokens based on token budget and provider preferences."""
        active_provider = provider or config.ACTIVE_PROVIDER or "ollama"
        use_cloud = active_provider in ("gemini", "anthropic", "openai", "opencode_go", "opencode_zen")
        use_cloud = use_cloud or force_cloud or (token_budget > config.PERSONA_ASSESS_MAX_LOCAL_TOKENS)

        if use_cloud:
            if not user_consent:
                logger.warning(f"Cloud LLM ({active_provider}) requested/required, but user consent was not given. Falling back to local Ollama.")
                yield from self._call_local_stream(prompt, ollama_model, system=system)
                return

            if not config.ENABLE_CLOUD_AI:
                raise LLMDispatchError("Cloud AI processing is disabled in the application configuration.")

            if active_provider == "gemini":
                yield from self._call_gemini_stream(prompt, system=system)
            elif active_provider == "anthropic":
                yield from self._call_anthropic_stream(prompt, system=system)
            elif active_provider in ("openai", "opencode_go", "opencode_zen"):
                yield from self._call_openai_stream(prompt, active_provider, system=system)
            else:
                raise LLMDispatchError(f"Unknown provider: {active_provider}")
        else:
            yield from self._call_local_stream(prompt, ollama_model, system=system)

    def _call_gemini_stream(self, prompt: str, system: str | None = None):
        api_key = config.GOOGLE_API_KEY or config.CLOUD_API_KEY
        if not api_key:
            raise LLMDispatchError("Gemini API key is not configured.")
        model = config.GEMINI_MODEL
        self._require_model(model, "Gemini")
        try:
            client = self._get_gemini_client(api_key)
            genai_kwargs = {"model": model, "contents": prompt}
            if system:
                from google.genai import types as genai_types
                genai_kwargs["config"] = genai_types.GenerateContentConfig(system_instruction=system)
            response_stream = client.models.generate_content_stream(**genai_kwargs)
            for chunk in response_stream:
                if chunk and chunk.text:
                    yield chunk.text
        except Exception as e:
            logger.error(f"Gemini streaming dispatch failed: {e}")
            raise LLMDispatchError(f"Gemini request failed. Details: {str(e)}")

    def _call_anthropic_stream(self, prompt: str, system: str | None = None):
        import anthropic
        api_key = config.ANTHROPIC_API_KEY
        if not api_key:
            raise LLMDispatchError("Anthropic API key is not configured.")
        model = config.ANTHROPIC_MODEL
        self._require_model(model, "Anthropic")
        try:
            client = anthropic.Anthropic(api_key=api_key)
            stream_kwargs = {
                "model": model,
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system:
                stream_kwargs["system"] = system
            with client.messages.stream(**stream_kwargs) as stream:
                for text in stream.text_stream:
                    yield text
        except Exception as e:
            logger.error(f"Anthropic streaming dispatch failed: {e}")
            raise LLMDispatchError(f"Anthropic request failed. Details: {str(e)}")

    def _call_openai_stream(self, prompt: str, provider: str = "openai", system: str | None = None):
        import openai
        key_map = {
            "openai": ("OPENAI_API_KEY", config.OPENAI_API_KEY, None),
            "opencode_go": ("OPENGODE_GO_API_KEY", config.OPENGODE_GO_API_KEY, config.OPENGODE_GO_BASE_URL),
            "opencode_zen": ("OPENGODE_ZEN_API_KEY", config.OPENGODE_ZEN_API_KEY, config.OPENGODE_ZEN_BASE_URL),
        }
        _, api_key, base_url = key_map.get(provider, key_map["openai"])
        if not api_key:
            raise LLMDispatchError(f"API key not configured for {provider}.")
        model = getattr(config, f"{provider.upper()}_MODEL", "")
        self._require_model(model, provider)
        try:
            kwargs = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            client = openai.OpenAI(**kwargs)
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            stream = client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    yield delta.content
        except Exception as e:
            logger.error(f"{provider} streaming dispatch failed: {e}")
            raise LLMDispatchError(f"{provider} request failed. Details: {str(e)}")

    def _call_local_stream(self, prompt: str, ollama_model: str | None = None, system: str | None = None):
        target_model = self._resolve_ollama_model(ollama_model)
        logger.info(f"Dispatching streaming request to local Ollama model '{target_model}'...")
        try:
            yield from ollama_client.generate_stream(target_model, prompt, system=system)
        except Exception as e:
            logger.error(f"Local Ollama streaming failed: {e}")
            raise LLMDispatchError(f"Local Ollama model '{target_model}' streaming failed. Details: {str(e)}")


from src.utils.lazy_proxy import LazyProxy

llm_dispatcher = LazyProxy(LLMDispatcher)
