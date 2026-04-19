"""
Database module for tracking processed emails and system operations.
Uses SQLite for lightweight, file-based persistence.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple
import config
from utils.logger import get_logger

logger = get_logger(__name__)


class EmailDatabase:
    """Manages SQLite database for email processing tracking."""
    
    def __init__(self, db_path: Path = None):
        """
        Initialize database connection.
        
        Args:
            db_path (Path): Path to SQLite database file
        """
        self.db_path = db_path or config.DATABASE_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize_database()
    
    def initialize_database(self):
        """Create tables if they don't exist."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Table: processed_emails
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_emails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_uid TEXT UNIQUE NOT NULL,
                    sender_email TEXT NOT NULL,
                    subject TEXT,
                    received_date TIMESTAMP,
                    processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    matched_keywords TEXT,
                    response_sent BOOLEAN DEFAULT 1,
                    status TEXT DEFAULT 'success'
                )
            """)
            
            # Table: processing_log
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processing_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    event_type TEXT NOT NULL,
                    email_uid TEXT,
                    message TEXT,
                    error_message TEXT
                )
            """)
            
            # Create index for faster lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_email_uid 
                ON processed_emails(email_uid)
            """)
            
            conn.commit()
            conn.close()
            logger.info(f"Database initialized at {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            raise
    
    def email_processed(self, email_uid: str) -> bool:
        """
        Check if email has already been processed.
        
        Args:
            email_uid (str): Email unique identifier (IMAP UID)
        
        Returns:
            bool: True if email was processed, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM processed_emails WHERE email_uid = ?", (email_uid,))
            result = cursor.fetchone()
            conn.close()
            return result is not None
        except sqlite3.Error as e:
            logger.error(f"Database query error: {e}")
            return False
    
    def add_processed_email(
        self,
        email_uid: str,
        sender_email: str,
        subject: str,
        received_date: datetime,
        matched_keywords: str,
        response_sent: bool = True,
        status: str = "success"
    ) -> bool:
        """
        Record a processed email in the database.
        
        Args:
            email_uid (str): Email unique identifier
            sender_email (str): Sender's email address
            subject (str): Email subject
            received_date (datetime): When email was received
            matched_keywords (str): Comma-separated matched keywords
            response_sent (bool): Whether response was sent
            status (str): Processing status (success, failed, skipped)
        
        Returns:
            bool: True if successfully added, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO processed_emails 
                (email_uid, sender_email, subject, received_date, 
                 matched_keywords, response_sent, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                email_uid,
                sender_email,
                subject,
                received_date,
                matched_keywords,
                response_sent,
                status
            ))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"Email {email_uid} already exists in database")
            return False
        except sqlite3.Error as e:
            logger.error(f"Database insert error: {e}")
            return False
    
    def log_event(
        self,
        event_type: str,
        message: str,
        email_uid: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Log a system event.
        
        Args:
            event_type (str): Type of event (connection, processing, error)
            message (str): Event message
            email_uid (str): Associated email UID if applicable
            error_message (str): Error details if applicable
        
        Returns:
            bool: True if logged successfully
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO processing_log 
                (event_type, email_uid, message, error_message)
                VALUES (?, ?, ?, ?)
            """, (event_type, email_uid, message, error_message))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error logging event: {e}")
            return False
    
    def get_statistics(self) -> dict:
        """
        Get processing statistics.
        
        Returns:
            dict: Statistics including total processed, success rate, etc.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total processed emails
            cursor.execute("SELECT COUNT(*) FROM processed_emails")
            total_processed = cursor.fetchone()[0]
            
            # Success count
            cursor.execute("SELECT COUNT(*) FROM processed_emails WHERE status = 'success'")
            success_count = cursor.fetchone()[0]
            
            # Failed count
            cursor.execute("SELECT COUNT(*) FROM processed_emails WHERE status = 'failed'")
            failed_count = cursor.fetchone()[0]
            
            conn.close()
            
            success_rate = (success_count / total_processed * 100) if total_processed > 0 else 0
            
            return {
                "total_processed": total_processed,
                "success_count": success_count,
                "failed_count": failed_count,
                "success_rate": f"{success_rate:.2f}%"
            }
        except sqlite3.Error as e:
            logger.error(f"Error retrieving statistics: {e}")
            return {}


# Global database instance
_db_instance = None


def get_database() -> EmailDatabase:
    """Get or create global database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = EmailDatabase()
    return _db_instance
