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
        """
        if not installed_models:
            return None

        embedding_patterns = ["bge", "nomic-embed", "mxbai-embed", "gte", "snowflake-arctic-embed", "all-minilm", "embed"]
        generation_models = [m for m in installed_models if not any(p in m.lower() for p in embedding_patterns)]

        if not generation_models:
            return None

        priority = ["gemma2", "llama3", "mistral", "phi3"]

        for p in priority:
            for model in generation_models:
                if p in model.lower():
                    return model

        return generation_models[0]

    def generate(self, model: str, prompt: str, system: str | None = None) -> str:
        """Sends a generation request to Ollama."""
        from src.utils.config import config
        url = f"{self.host}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
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
                    return str(result.get("response", ""))
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise RuntimeError(f"Ollama generation failed: {e}") from e
        return ""

    def generate_stream(self, model: str, prompt: str, system: str | None = None):
        """Sends a streaming generation request to Ollama, yielding string tokens."""
        from src.utils.config import config
        url = f"{self.host}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True
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
