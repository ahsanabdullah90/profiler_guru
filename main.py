import os
import sys
import subprocess
from src.utils.logger import logger
from src.utils.config import config

def run_streamlit():
    logger.info("Starting Streamlit UI...")
    # Using subprocess.run to securely execute streamlit
    # sys.executable -m streamlit ensures we use the streamlit package in the current environment
    subprocess.run([sys.executable, "-m", "streamlit", "run", "src/app/streamlit_app.py"], check=True)

if __name__ == "__main__":
    config.validate()
    logger.info("Starting InstaSync AI...")
    try:
        run_streamlit()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
