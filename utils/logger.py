"""
Logging utility module for Email Automation System.
Provides structured logging with file and console output.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime
import config

# Ensure log directory exists
config.LOG_DIR.mkdir(parents=True, exist_ok=True)

class CustomFormatter(logging.Formatter):
    """Custom formatter with colored console output."""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m'  # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        level = record.levelname
        if sys.stdout.isatty():
            color = self.COLORS.get(level, '')
            level = f"{color}{level}{self.RESET}"

        # Keep console output compact and flow-oriented.
        time_str = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        return f"{time_str} | {level:<8} | {record.getMessage()}"


def get_logger(name):
    """
    Create and configure a logger with file and console handlers.
    
    Args:
        name (str): Logger name (typically __name__)
    
    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers if logger already configured
    if logger.hasHandlers():
        return logger
    
    logger.setLevel(logging.DEBUG)
    
    # Log format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # File handler with rotation (max 10MB, keep 5 backups)
    try:
        file_handler = RotatingFileHandler(
            config.LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(log_format))
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not setup file logging: {e}")
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO if not config.DEBUG_MODE else logging.DEBUG)
    console_handler.setFormatter(CustomFormatter(log_format))
    logger.addHandler(console_handler)
    
    return logger


def log_email_processing(logger, email_id, sender, subject, status, details=""):
    """
    Log email processing with structured format.
    
    Args:
        logger: Logger instance
        email_id (str): Email UID
        sender (str): Sender email address
        subject (str): Email subject
        status (str): Processing status (success, skipped, failed, error)
        details (str): Additional details
    """
    log_entry = f"Email ID: {email_id} | From: {sender} | Subject: {subject} | Status: {status}"
    if details:
        log_entry += f" | {details}"
    
    if status == "success":
        logger.info(log_entry)
    elif status == "skipped":
        logger.debug(log_entry)
    elif status in ["failed", "error"]:
        logger.error(log_entry)
    else:
        logger.info(log_entry)
