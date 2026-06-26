import os
import sys
import subprocess
from src.utils.logger import logger
from src.utils.config import config

def run_streamlit():
    logger.info("Starting Streamlit UI...")
    try:
        # Use sys.executable to run streamlit within the same environment/interpreter
        # This is more secure than os.system and captures exit codes/errors properly
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", "src/app/streamlit_app.py"],
            check=True
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Streamlit process exited with error code {e.returncode}")
        sys.exit(e.returncode)
    except FileNotFoundError:
        logger.error("Streamlit is not installed or could not be found in the current environment.")
        sys.exit(1)

if __name__ == "__main__":
    config.validate()
    logger.info("Starting Profile_Guru...")
    try:
        run_streamlit()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
