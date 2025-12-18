import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging(log_file="rssy2.log"):
    # Create logger
    logger = logging.getLogger("RSSy2")
    logger.setLevel(logging.INFO)

    # Prevent duplicating logs if setup_logging is called multiple times
    if logger.handlers:
        return logger

    # Log format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler (Rotating)
    # Max 5MB per file, keep 3 backups
    file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

# Create a shared logger instance
logger = setup_logging()
