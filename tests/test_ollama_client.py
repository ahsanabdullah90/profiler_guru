"""Unit tests for OllamaClient with mocked HTTP responses."""
import json
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from src.utils.ollama_client import OllamaClient


# ── Helpers ──────────────────────────────────────────────────────────

def _mock_http_response(status: int, body: dict):
    """Build a MagicMock that mimics urllib.request.urlopen's response context manager."""
    mock = MagicMock()
    mock.status = status
    mock.read.return_value = json.dumps(body).encode("utf-8")
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    return mock


# ── get_best_model ────────────────────────────────────────────────────

class TestGetBestModel:
    def test_empty_list_raises(self):
        client = OllamaClient()
        with pytest.raises(RuntimeError, match="No Ollama models are installed"):
            client.get_best_model([])

    @patch.object(OllamaClient, "generate", return_value="OK")
    def test_gemma2_preferred(self, mock_gen):
        client = OllamaClient()
        result = client.get_best_model(["llama3:latest", "gemma2:9b", "mistral:7b"])
        assert result == "gemma2:9b"

    @patch.object(OllamaClient, "generate", return_value="OK")
    def test_llama3_preferred_over_mistral(self, mock_gen):
        client = OllamaClient()
        result = client.get_best_model(["mistral:7b", "llama3:8b"])
        assert result == "llama3:8b"

    @patch.object(OllamaClient, "generate", return_value="OK")
    def test_fallback_to_first(self, mock_gen):
        client = OllamaClient()
        result = client.get_best_model(["custom-model:latest"])
        assert result == "custom-model:latest"

    @patch.object(OllamaClient, "generate", return_value="OK")
    def test_case_insensitive(self, mock_gen):
        client = OllamaClient()
        result = client.get_best_model(["LLAMA3:latest"])
        assert result == "LLAMA3:latest"

    @patch.object(OllamaClient, "generate", return_value="OK")
    def test_filters_out_embedding_models(self, mock_gen):
        client = OllamaClient()
        result = client.get_best_model(["bge-m3", "llama3:8b", "nomic-embed-text"])
        assert result == "llama3:8b"

    def test_only_embedding_models_raises(self):
        client = OllamaClient()
        with pytest.raises(RuntimeError, match="embedding-only"):
            client.get_best_model(["bge-m3", "nomic-embed-text", "mxbai-embed-large"])

    @patch.object(OllamaClient, "generate", return_value="OK")
    def test_filters_various_embedding_patterns(self, mock_gen):
        client = OllamaClient()
        result = client.get_best_model(["bge-large", "gte-qwen2", "snowflake-arctic-embed", "all-minilm", "mistral:7b"])
        assert result == "mistral:7b"

    @patch.object(OllamaClient, "generate", side_effect=["", "OK"])
    def test_skips_model_that_fails_probe(self, mock_gen):
        """gemma2 (priority) returns empty probe → skipped; llama3 returns OK → selected."""
        client = OllamaClient()
        result = client.get_best_model(["llama3:8b", "gemma2:9b"])
        assert result == "llama3:8b"

    @patch.object(OllamaClient, "generate", return_value="")
    def test_all_models_fail_probe_raises(self, mock_gen):
        """Every candidate returns empty probe → RuntimeError."""
        client = OllamaClient()
        with pytest.raises(RuntimeError, match="None of the installed Ollama models"):
            client.get_best_model(["llama3:8b", "mistral:7b"])

    @patch.object(OllamaClient, "generate", side_effect=[RuntimeError("error"), "OK"])
    def test_skips_model_that_excepts_on_probe(self, mock_gen):
        """First model (non-priority) raises on probe → skipped; next returns OK → selected."""
        client = OllamaClient()
        result = client.get_best_model(["bad-model", "other-model"])
        assert result == "other-model"


# ── get_installed_models ────────────────────────────────────────────

class TestGetInstalledModels:
    @patch("src.utils.ollama_client.urllib.request.urlopen")
    def test_success(self, mock_urlopen):
        mock_urlopen.return_value = _mock_http_response(200, {
            "models": [
                {"name": "llama3:latest"},
                {"name": "mistral:7b"},
            ]
        })
        client = OllamaClient()
        result = client.get_installed_models()
        assert result == ["llama3:latest", "mistral:7b"]

    @patch("src.utils.ollama_client.urllib.request.urlopen")
    def test_connection_failure_returns_empty(self, mock_urlopen):
        mock_urlopen.side_effect = ConnectionError("Connection refused")
        client = OllamaClient()
        result = client.get_installed_models()
        assert result == []


# ── generate (/api/generate) ────────────────────────────────────────

class TestGenerate:
    @patch("src.utils.ollama_client.urllib.request.urlopen")
    def test_success(self, mock_urlopen):
        mock_urlopen.return_value = _mock_http_response(200, {"response": "Hello from Ollama"})
        client = OllamaClient()
        result = client.generate("llama3", "Say hello")
        assert result == "Hello from Ollama"

    @patch("src.utils.ollama_client.urllib.request.urlopen")
    def test_failure_raises(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("Ollama is down")
        client = OllamaClient()
        with pytest.raises(RuntimeError, match="Ollama generation failed"):
            client.generate("llama3", "Say hello")

    @patch("src.utils.ollama_client.urllib.request.urlopen")
    def test_non_200_returns_empty(self, mock_urlopen):
        mock_urlopen.return_value = _mock_http_response(500, {})
        client = OllamaClient()
        result = client.generate("llama3", "Say hello")
        assert result == ""


# ── generate_chat (/api/chat) ───────────────────────────────────────

class TestGenerateChat:
    @patch("src.utils.ollama_client.urllib.request.urlopen")
    def test_success_with_system(self, mock_urlopen):
        mock_urlopen.return_value = _mock_http_response(200, {
            "message": {"role": "assistant", "content": "Chat response"},
        })
        client = OllamaClient()
        result = client.generate_chat("gemma3:4b", "Hi", system="Be helpful")
        assert result == "Chat response"

    @patch("src.utils.ollama_client.urllib.request.urlopen")
    def test_success_no_system(self, mock_urlopen):
        mock_urlopen.return_value = _mock_http_response(200, {
            "message": {"role": "assistant", "content": "OK"},
        })
        client = OllamaClient()
        result = client.generate_chat("gemma3:4b", "Hi", system=None)
        assert result == "OK"

    @patch("src.utils.ollama_client.urllib.request.urlopen")
    def test_empty_message_content(self, mock_urlopen):
        mock_urlopen.return_value = _mock_http_response(200, {
            "message": {"role": "assistant", "content": ""},
        })
        client = OllamaClient()
        result = client.generate_chat("gemma3:4b", "Hi")
        assert result == ""

    @patch("src.utils.ollama_client.urllib.request.urlopen")
    def test_failure_raises(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("Ollama is down")
        client = OllamaClient()
        with pytest.raises(RuntimeError, match="Ollama chat generation failed"):
            client.generate_chat("gemma3:4b", "Hi")

    @patch("src.utils.ollama_client.urllib.request.urlopen")
    def test_non_200_returns_empty(self, mock_urlopen):
        mock_urlopen.return_value = _mock_http_response(503, {})
        client = OllamaClient()
        result = client.generate_chat("gemma3:4b", "Hi")
        assert result == ""


# ── generate_stream ───────────────────────────────────────────────────

class TestGenerateStream:
    @patch("src.utils.ollama_client.urllib.request.urlopen")
    def test_yields_tokens(self, mock_urlopen):
        lines = [
            json.dumps({"response": "Hello", "done": False}).encode("utf-8"),
            json.dumps({"response": " world", "done": False}).encode("utf-8"),
            json.dumps({"response": "", "done": True}).encode("utf-8"),
        ]
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__iter__ = MagicMock(return_value=iter(lines))
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        client = OllamaClient()
        tokens = list(client.generate_stream("llama3", "Say hello"))
        assert tokens == ["Hello", " world"]

    @patch("src.utils.ollama_client.urllib.request.urlopen")
    def test_failure_raises(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("Ollama is down")
        client = OllamaClient()
        with pytest.raises(RuntimeError, match="streaming generation failed"):
            list(client.generate_stream("llama3", "Say hello"))
