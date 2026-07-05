"""Unit tests for OllamaClient with mocked HTTP responses."""
import json
import pytest
from unittest.mock import patch, MagicMock
from src.utils.ollama_client import OllamaClient


class TestGetBestModel:
    def test_empty_list_returns_none(self):
        client = OllamaClient()
        assert client.get_best_model([]) is None

    def test_gemma2_preferred(self):
        client = OllamaClient()
        result = client.get_best_model(["llama3:latest", "gemma2:9b", "mistral:7b"])
        assert result == "gemma2:9b"

    def test_llama3_preferred_over_mistral(self):
        client = OllamaClient()
        result = client.get_best_model(["mistral:7b", "llama3:8b"])
        assert result == "llama3:8b"

    def test_fallback_to_first(self):
        client = OllamaClient()
        result = client.get_best_model(["custom-model:latest"])
        assert result == "custom-model:latest"

    def test_case_insensitive(self):
        client = OllamaClient()
        result = client.get_best_model(["LLAMA3:latest"])
        assert result == "LLAMA3:latest"


class TestGetInstalledModels:
    @patch("src.utils.ollama_client.urllib.request.urlopen")
    def test_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({
            "models": [
                {"name": "llama3:latest"},
                {"name": "mistral:7b"},
            ]
        }).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        client = OllamaClient()
        result = client.get_installed_models()
        assert result == ["llama3:latest", "mistral:7b"]

    @patch("src.utils.ollama_client.urllib.request.urlopen")
    def test_connection_failure_returns_empty(self, mock_urlopen):
        mock_urlopen.side_effect = ConnectionError("Connection refused")

        client = OllamaClient()
        result = client.get_installed_models()
        assert result == []


class TestGenerate:
    @patch("src.utils.ollama_client.urllib.request.urlopen")
    def test_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({
            "response": "Hello from Ollama"
        }).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        client = OllamaClient()
        result = client.generate("llama3", "Say hello")
        assert result == "Hello from Ollama"

    @patch("src.utils.ollama_client.urllib.request.urlopen")
    def test_failure_raises(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("Ollama is down")

        client = OllamaClient()
        with pytest.raises(RuntimeError, match="Ollama generation failed"):
            client.generate("llama3", "Say hello")


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
