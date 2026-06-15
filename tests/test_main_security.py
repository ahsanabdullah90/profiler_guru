import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# We need to mock the logger and config before importing main to avoid side effects
with patch('src.utils.logger.logger'), patch('src.utils.config.config'):
    import main

class TestMainSecurity(unittest.TestCase):
    @patch('os.system')
    def test_run_streamlit_does_not_use_os_system(self, mock_system):
        # Verify os.system is NO LONGER used
        # We need to mock subprocess.run to avoid actually running streamlit
        with patch('subprocess.run'):
            main.run_streamlit()
        mock_system.assert_not_called()

    @patch('subprocess.run')
    def test_run_streamlit_uses_subprocess(self, mock_run):
        # Verify subprocess.run is used correctly
        # Mocking sys.executable to have a predictable value
        with patch('sys.executable', '/usr/bin/python3'):
            main.run_streamlit()

        expected_cmd = ['/usr/bin/python3', '-m', 'streamlit', 'run', 'src/app/streamlit_app.py']
        mock_run.assert_called_once_with(expected_cmd, check=True)

if __name__ == "__main__":
    unittest.main()
