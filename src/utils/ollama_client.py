import json
import urllib.request

from src.utils.logger import logger


class OllamaClient:
    def __init__(self, host="http://localhost:11434"):
        self.host = host.rstrip('/')

    def get_installed_models(self):
        """Queries local Ollama to list all installed models.
        Returns a list of model names, or an empty list if Ollama is unreachable.
        """
        from src.utils.config import config
        url = f"{self.host}/api/tags"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=config.OLLAMA_LIST_TIMEOUT) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    models = [m['name'] for m in data.get('models', [])]
                    return models
        except Exception as e:
            logger.debug(f"Ollama not reachable at {self.host}: {e}")
        return []

    def get_best_model(self, installed_models):
        """Ranks installed models by preference and returns the best match.
        Filters out embedding models (bge, nomic-embed, etc.) as they cannot generate text.
        Preference order: gemma2 > llama3 > mistral > phi3 > any other.

        Returns a model name if a working text-generation model is found.
        Raises RuntimeError if no model supports text generation (verified with a probe).
        """
        if not installed_models:
            raise RuntimeError(
                "No Ollama models are installed. "
                "Go to Settings → Models to install or configure a model."
            )

        embedding_patterns = ["bge", "nomic-embed", "mxbai-embed", "gte", "snowflake-arctic-embed", "all-minilm", "embed"]
        generation_candidates = [m for m in installed_models if not any(p in m.lower() for p in embedding_patterns)]

        if not generation_candidates:
            raise RuntimeError(
                "All installed Ollama models are embedding-only models "
                "(bge, nomic-embed, etc.), which cannot generate text. "
                "Install a text-generation model like 'gemma3:4b' or 'llama3:8b'."
            )

        priority = ["gemma2", "llama3", "mistral", "phi3"]

        candidates_by_priority = []
        for p in priority:
            for model in generation_candidates:
                if p in model.lower():
                    candidates_by_priority.append(model)
        for model in generation_candidates:
            if model not in candidates_by_priority:
                candidates_by_priority.append(model)

        for model in candidates_by_priority:
            try:
                probe = self.generate(model, "Respond with exactly and only: OK", system=None)
                if probe and probe.strip():
                    logger.info(f"Auto-selected Ollama model '{model}' (verified with probe)")
                    return model
                logger.warning(f"Auto-selection candidate '{model}' returned empty probe, trying next")
            except Exception as e:
                logger.warning(f"Auto-selection candidate '{model}' failed probe: {e}, trying next")

        raise RuntimeError(
            "None of the installed Ollama models produced text output from a probe request. "
            "The models may not support text generation, or Ollama may not be running correctly. "
            "Go to Settings → Models to configure a compatible model."
        )

    def generate(self, model: str, prompt: str, system: str | None = None) -> str:
        """Sends a generation request to Ollama via /api/generate."""
        from src.utils.config import config
        url = f"{self.host}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_ctx": 131072, "keep_alive": config.OLLAMA_KEEP_ALIVE},
        }
        if system:
            payload["system"] = system

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=config.OLLAMA_GENERATE_TIMEOUT) as response:
                if response.status == 200:
                    result = json.loads(response.read().decode('utf-8'))
                    text = str(result.get("response", ""))
                    if not text:
                        logger.warning(
                            f"Ollama model '{model}' returned empty response via /api/generate "
                            f"(eval_count={result.get('eval_count', 'N/A')}). "
                            f"The model may not support this endpoint."
                        )
                    return text
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise RuntimeError(f"Ollama generation failed: {e}") from e
        logger.warning(f"Ollama /api/generate returned non-200 status for model '{model}', returning empty")
        return ""

    def generate_chat(self, model: str, prompt: str, system: str | None = None) -> str:
        """Sends a request to Ollama via /api/chat.

        Uses message-based format with explicit system/user roles, required by
        chat-template models like gemma3, phi3, and qwen3.
        """
        from src.utils.config import config
        url = f"{self.host}/api/chat"
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"num_ctx": 131072, "keep_alive": config.OLLAMA_KEEP_ALIVE},
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=config.OLLAMA_GENERATE_TIMEOUT) as response:
                if response.status == 200:
                    result = json.loads(response.read().decode('utf-8'))
                    text = str(result.get("message", {}).get("content", ""))
                    if not text:
                        logger.warning(
                            f"Ollama model '{model}' returned empty response via /api/chat "
                            f"(eval_count={result.get('eval_count', 'N/A')})."
                        )
                    return text
        except Exception as e:
            logger.error(f"Ollama chat generation failed: {e}")
            raise RuntimeError(f"Ollama chat generation failed: {e}") from e
        logger.warning(f"Ollama /api/chat returned non-200 status for model '{model}', returning empty")
        return ""

    def generate_stream(self, model: str, prompt: str, system: str | None = None):
        """Sends a streaming generation request to Ollama, yielding string tokens."""
        from src.utils.config import config
        url = f"{self.host}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {"num_ctx": 131072, "keep_alive": config.OLLAMA_KEEP_ALIVE},
        }
        if system:
            payload["system"] = system

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            response = urllib.request.urlopen(req, timeout=config.OLLAMA_GENERATE_TIMEOUT)
            if response.status == 200:
                for line in response:
                    if line:
                        data = json.loads(line.decode('utf-8'))
                        token = data.get("response", "")
                        if token:
                            yield token
                        if data.get("done", False):
                            break
        except Exception as e:
            logger.error(f"Ollama streaming generation failed: {e}")
            raise RuntimeError(f"Ollama streaming generation failed: {e}") from e


ollama_client = OllamaClient()
