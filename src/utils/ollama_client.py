import urllib.request
import json
from src.utils.logger import logger

class OllamaClient:
    def __init__(self, host="http://localhost:11434"):
        self.host = host.rstrip('/')

    def get_installed_models(self):
        """Queries local Ollama to list all installed models.
        Returns a list of model names, or an empty list if Ollama is unreachable.
        """
        url = f"{self.host}/api/tags"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=3) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    models = [m['name'] for m in data.get('models', [])]
                    return models
        except Exception as e:
            logger.debug(f"Ollama not reachable at {self.host}: {e}")
        return []

    def get_best_model(self, installed_models):
        """Ranks installed models by preference and returns the best match.
        Preference order: gemma2 > llama3 > mistral > phi3 > any other.
        """
        if not installed_models:
            return None
        
        priority = ["gemma2", "llama3", "mistral", "phi3"]
        
        # Check for substring matches in priority order
        for p in priority:
            for model in installed_models:
                if p in model.lower():
                    return model
                    
        return installed_models[0]

    def generate(self, model: str, prompt: str, system: str = None) -> str:
        """Sends a generation request to Ollama."""
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
            with urllib.request.urlopen(req, timeout=60) as response:
                if response.status == 200:
                    result = json.loads(response.read().decode('utf-8'))
                    return result.get("response", "")
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise RuntimeError(f"Ollama generation failed: {e}")
        return ""

ollama_client = OllamaClient()
