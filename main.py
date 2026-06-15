import os
from src.utils.logger import logger
from src.utils.config import config

def run_streamlit():
    logger.info("Starting Streamlit UI...")
    # Using subprocess or os.system to run streamlit
    os.system("streamlit run src/app/streamlit_app.py")

if __name__ == "__main__":
    config.validate()
    logger.info("Starting InstaSync AI...")
    try:
        run_streamlit()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
