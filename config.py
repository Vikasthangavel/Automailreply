"""
Configuration module for Email Automation System.
Contains all constants and default settings.
"""

import os
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).parent

# Email Configuration
GMAIL_IMAP_SERVER = "imap.gmail.com"
GMAIL_IMAP_PORT = 993
GMAIL_SMTP_SERVER = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587

# Excel Configuration
EXCEL_FILE_PATH = PROJECT_ROOT / "data" / "KeywordandResponses.xlsx"
EXCEL_COLUMNS = {
    "keyword": "Keyword",
    "priority": "Priority",
    "response": "Response Template"
}

# Database Configuration
DATABASE_PATH = PROJECT_ROOT / "data" / "email_automation.db"

# Logging Configuration
LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "email_automation.log"
LOG_LEVEL = "INFO"

# Fuzzy Matching Configuration
FUZZY_MATCH_THRESHOLD = 80  # 0-100 score threshold for fuzzy match
FUZZY_MATCH_PROCESSOR = "partial_ratio"  # or "token_set_ratio", "token_sort_ratio"

# Email Processing Configuration
BATCH_SIZE = 10  # Number of emails to process in one batch
MAX_RETRIES = 3  # Maximum retry attempts for email operations

# Response Configuration
FALLBACK_RESPONSE = """
Hello,

Thank you for reaching out. We have received your email and will process your request shortly.

Best regards,
Automated Response System
"""

# Environment variables (loaded from .env file)
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")  # App Password for Gmail
SENDER_NAME = os.getenv("SENDER_NAME", "Automated Response System")

# Feature Flags
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
DRY_RUN_MODE = os.getenv("DRY_RUN_MODE", "false").lower() == "true"
