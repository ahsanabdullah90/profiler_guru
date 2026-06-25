import os
import logging
import sys
from logging.handlers import RotatingFileHandler

# Ensure console output handles unicode without crashing on Windows
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    except Exception:
        pass

def setup_logger():
    logger = logging.getLogger("Profile_Guru")
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # Lazily import config to prevent circular imports during initialization
    try:
        from src.utils.config import config
        log_dir = config.DATA_DIR / "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # Rotating File Handler: max 5 MB per file, keep 2 backups
        fh = RotatingFileHandler(
            log_dir / "app.log", 
            maxBytes=5 * 1024 * 1024, 
            backupCount=2,
            encoding='utf-8'
        )
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        logger.info(f"File logger successfully initialized at: {log_dir / 'app.log'}")
    except Exception as e:
        # Fallback if config is not yet initialized or fails
        logger.warning(f"Could not initialize rotating file log handler: {e}")

    return logger

logger = setup_logger()
