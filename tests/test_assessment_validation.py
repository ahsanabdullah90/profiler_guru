"""Tests for assessment validation and error handling."""
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from main_api import app
from src.api.api_rag import _is_error_profile


class TestErrorProfileDetection:
    """Test the _is_error_profile helper function."""

    def test_detects_error_messages(self):
        """Should detect various error patterns in profile text."""
        error_texts = [
            "Error: Local Ollama model 'llama3' is not reachable",
            "Ollama generation failed: HTTP Error 404",
            "Traceback (most recent call last):\n  File...",
            "The model failed to generate a response",
        ]
        for text in error_texts:
            assert _is_error_profile(text) is True, f"Should detect: {text}"

    def test_accepts_valid_profiles(self):
        """Should accept valid assessment profiles."""
        valid_texts = [
            "# Personality Assessment\n\nThis is a valid assessment...",
            "## Communication Style\n\nDirect and assertive...",
            "The subject shows high levels of openness...",
        ]
        for text in valid_texts:
            assert _is_error_profile(text) is False, f"Should accept: {text}"

    def test_handles_none_and_empty(self):
        """Should handle None and empty strings."""
        assert _is_error_profile(None) is False
        assert _is_error_profile("") is False


class TestModelValidation:
    """Test model validation before assessment generation."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self, client):
        """Get authentication headers."""
        resp = client.post("/api/v1/auth/login", json={"password": "koko"})
        if resp.status_code == 401:
            pytest.skip("APP_PASSWORD not configured")
        return {"Authorization": f"Bearer {resp.json()['token']}"}

    def test_profile_endpoint_ignores_error_files(self, client, auth_headers, tmp_path):
        """GET /profile should return null for error files."""
        from src.utils.config import config
        
        # Create a test contact with an error file
        contact_dir = Path(config.CHATS_DIR) / "test_error_contact"
        contact_dir.mkdir(parents=True, exist_ok=True)
        
        # Write an error file
        error_file = contact_dir / "personality_assessment.md"
        error_file.write_text("Error: Local Ollama model 'llama3' is not reachable")
        
        # Write a meta file
        meta_file = contact_dir / "personality_assessment.json"
        meta_file.write_text('{"model": "llama3"}')
        
        try:
            # Request the profile
            resp = client.get("/api/v1/rag/contacts/test_error_contact/profile", headers=auth_headers)
            assert resp.status_code == 200
            
            data = resp.json()
            # Should return null for error files
            assert data["profile"] is None
            assert data["meta"] is None
        finally:
            # Cleanup
            if error_file.exists():
                error_file.unlink()
            if meta_file.exists():
                meta_file.unlink()
            if contact_dir.exists():
                contact_dir.rmdir()

    def test_profile_endpoint_accepts_valid_files(self, client, auth_headers, tmp_path):
        """GET /profile should return valid profiles."""
        from src.utils.config import config
        
        # Create a test contact with a valid file
        contact_dir = Path(config.CHATS_DIR) / "test_valid_contact"
        contact_dir.mkdir(parents=True, exist_ok=True)
        
        # Write a valid profile
        profile_file = contact_dir / "personality_assessment.md"
        profile_file.write_text("# Personality Assessment\n\nThis is valid.")
        
        # Write a meta file
        meta_file = contact_dir / "personality_assessment.json"
        meta_file.write_text('{"model": "gemma3:4b", "framework_id": "big_five"}')
        
        try:
            # Request the profile
            resp = client.get("/api/v1/rag/contacts/test_valid_contact/profile", headers=auth_headers)
            assert resp.status_code == 200
            
            data = resp.json()
            # Should return the valid profile
            assert data["profile"] is not None
            assert "Personality Assessment" in data["profile"]
            assert data["meta"] is not None
            assert data["meta"]["model"] == "gemma3:4b"
        finally:
            # Cleanup
            if profile_file.exists():
                profile_file.unlink()
            if meta_file.exists():
                meta_file.unlink()
            if contact_dir.exists():
                contact_dir.rmdir()
