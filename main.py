"""
Email Automation System - Main Orchestrator
Coordinates all components: email fetching, keyword matching, response generation, and sending.
"""

import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import config
from email_fetcher import EmailFetcher
from keyword_engine import KeywordEngine
from response_generator import ResponseGenerator
from email_sender import EmailSender
from utils.logger import get_logger, log_email_processing
from utils.database import get_database

logger = get_logger(__name__)


class EmailAutomationSystem:
    """
    Main orchestrator for the email automation system.
    Coordinates all components and manages the processing workflow.
    """
    
    def __init__(self):
        """Initialize all system components."""
        self.email_fetcher = None
        self.keyword_engine = None
        self.response_generator = None
        self.email_sender = None
        self.database = get_database()
        self.stats = {
            "total_processed": 0,
            "emails_sent": 0,
            "errors": 0,
            "skipped": 0
        }
    
    def initialize(self) -> bool:
        """
        Initialize and validate all system components.
        
        Returns:
            bool: True if initialization successful
        """
        logger.info("=" * 60)
        logger.info("Email Automation System - Initializing")
        logger.info("=" * 60)
        
        # Validate configuration
        if not self._validate_config():
            return False
        
        # Initialize components
        try:
            self.email_fetcher = EmailFetcher(config.EMAIL_ADDRESS, config.EMAIL_PASSWORD)
            self.keyword_engine = KeywordEngine()
            self.response_generator = ResponseGenerator()
            self.email_sender = EmailSender(config.EMAIL_ADDRESS, config.EMAIL_PASSWORD)
            
            logger.info("All components initialized successfully")
            return True
        
        except Exception as e:
            logger.error(f"Error initializing components: {e}")
            return False
    
    def _validate_config(self) -> bool:
        """
        Validate configuration and environment variables.
        
        Returns:
            bool: True if configuration is valid
        """
        errors = []
        
        # Check email credentials
        if not config.EMAIL_ADDRESS:
            errors.append("EMAIL_ADDRESS not set in environment")
        if not config.EMAIL_PASSWORD:
            errors.append("EMAIL_PASSWORD not set in environment")
        
        # Check Excel file
        if not config.EXCEL_FILE_PATH.exists():
            errors.append(f"Excel file not found: {config.EXCEL_FILE_PATH}")
        
        if errors:
            for error in errors:
                logger.error(f"Configuration error: {error}")
            return False
        
        logger.info("Configuration validated successfully")
        return True
    
    def run(self, batch_size: int = None, dry_run: bool = False) -> dict:
        """
        Run the main email automation workflow.
        
        Args:
            batch_size (int): Number of emails to process in this run (default from config)
            dry_run (bool): If True, don't actually send emails (default: config.DRY_RUN_MODE)
        
        Returns:
            dict: Statistics about the run
        """
        dry_run = dry_run or config.DRY_RUN_MODE
        batch_size = batch_size or config.BATCH_SIZE
        
        logger.info(f"Starting email processing run (dry_run={dry_run})")
        
        # Connect to email
        if not self.email_fetcher.connect():
            logger.error("Failed to connect to email server")
            self.database.log_event("connection_error", "Failed to connect to IMAP")
            return self.stats
        
        # Connect to SMTP
        if not dry_run and not self.email_sender.connect():
            logger.error("Failed to connect to SMTP server")
            self.database.log_event("connection_error", "Failed to connect to SMTP")
            self.email_fetcher.disconnect()
            return self.stats
        
        try:
            # Fetch unread emails
            unread_emails = self.email_fetcher.fetch_unread_emails(limit=batch_size)
            logger.info(f"Processing {len(unread_emails)} unread emails")
            
            # Process each email
            for email_data in unread_emails:
                self._process_email(email_data, dry_run)
            
            # Log run statistics
            logger.info("=" * 60)
            logger.info("Processing Run Complete")
            logger.info(f"  Total Processed: {self.stats['total_processed']}")
            logger.info(f"  Emails Sent: {self.stats['emails_sent']}")
            logger.info(f"  Skipped: {self.stats['skipped']}")
            logger.info(f"  Errors: {self.stats['errors']}")
            logger.info("=" * 60)
            
            self.database.log_event(
                "run_complete",
                f"Processed {self.stats['total_processed']} emails, "
                f"sent {self.stats['emails_sent']}"
            )
        
        except Exception as e:
            logger.error(f"Error during processing: {e}")
            self.database.log_event("processing_error", str(e), error_message=str(e))
        
        finally:
            self.email_fetcher.disconnect()
            if not dry_run:
                self.email_sender.disconnect()
        
        return self.stats
    
    def _process_email(self, email_data: dict, dry_run: bool = False) -> bool:
        """
        Process a single email through the entire workflow.
        
        Args:
            email_data (dict): Email data from fetcher
            dry_run (bool): If True, don't send email
        
        Returns:
            bool: True if processed successfully
        """
        email_uid = email_data["uid"]
        sender = email_data["sender"]
        subject = email_data["subject"]
        body = email_data["body"]
        received_date = email_data["received_date"]
        
        self.stats["total_processed"] += 1
        
        # Check if already processed
        if self.database.email_processed(email_uid):
            log_email_processing(
                logger, email_uid, sender, subject, "skipped",
                details="Email already processed"
            )
            self.stats["skipped"] += 1
            return False
        
        try:
            # Validate email body
            if not body or len(body.strip()) == 0:
                logger.warning(f"Empty email body from {sender}")
                self.database.add_processed_email(
                    email_uid, sender, subject, received_date,
                    "empty_body", False, "failed"
                )
                self.stats["errors"] += 1
                return False
            
            # Match keywords
            matches = self.keyword_engine.match_keywords(body)
            matched_keywords = self.keyword_engine.extract_unique_keywords(matches)
            
            # Generate response
            response_body = self.response_generator.generate_response(
                matches, sender
            )
            
            # Send email (unless dry run)
            sent_successfully = True
            if not dry_run:
                sent_successfully = self.email_sender.send_email(
                    recipient_email=sender,
                    subject=f"Re: {subject}",
                    body=response_body
                )
            else:
                logger.info(f"DRY RUN: Would send response to {sender}")
            
            # Record in database
            if sent_successfully or dry_run:
                self.database.add_processed_email(
                    email_uid, sender, subject, received_date,
                    matched_keywords, sent_successfully, "success"
                )
                
                log_email_processing(
                    logger, email_uid, sender, subject, "success",
                    details=f"Matched keywords: {matched_keywords}"
                )
                
                if sent_successfully:
                    self.stats["emails_sent"] += 1
            else:
                self.database.add_processed_email(
                    email_uid, sender, subject, received_date,
                    matched_keywords, False, "failed"
                )
                self.stats["errors"] += 1
            
            # Mark as read in IMAP
            self.email_fetcher.mark_as_read(email_uid)
            
            return sent_successfully
        
        except Exception as e:
            logger.error(f"Error processing email from {sender}: {e}")
            self.database.add_processed_email(
                email_uid, sender, subject, received_date,
                "", False, "error"
            )
            self.database.log_event(
                "processing_error",
                f"Error processing {email_uid}",
                email_uid,
                str(e)
            )
            self.stats["errors"] += 1
            return False
    
    def show_statistics(self):
        """Display database statistics."""
        stats = self.database.get_statistics()
        logger.info("=" * 60)
        logger.info("System Statistics")
        logger.info(f"  Total Emails Processed: {stats.get('total_processed', 0)}")
        logger.info(f"  Successful: {stats.get('success_count', 0)}")
        logger.info(f"  Failed: {stats.get('failed_count', 0)}")
        logger.info(f"  Success Rate: {stats.get('success_rate', 'N/A')}")
        logger.info("=" * 60)


def main():
    """Main entry point for the email automation system."""
    # Create and initialize system
    system = EmailAutomationSystem()
    
    if not system.initialize():
        logger.error("Failed to initialize system")
        sys.exit(1)
    
    # Show current statistics
    system.show_statistics()
    
    # Run the automation
    system.run()
    
    # Show updated statistics
    system.show_statistics()


if __name__ == "__main__":
    main()
