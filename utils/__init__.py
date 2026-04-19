"""
Utilities package for Email Automation System.
"""

from utils.logger import get_logger, log_email_processing
from utils.database import EmailDatabase, get_database

__all__ = [
    'get_logger',
    'log_email_processing',
    'EmailDatabase',
    'get_database'
]
