"""
Email Automation System - Main Orchestrator
Coordinates all components: email fetching, keyword matching, response generation, and sending.
"""

import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import config
from email_fetcher import EmailFetcher
from keyword_engine import KeywordEngine
from response_generator import ResponseGenerator
from email_sender import EmailSender
from utils.logger import get_logger
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

    def _section(self, title: str):
        """Print a clean section title for console readability."""
        logger.info("=" * 60)
        logger.info(title)
        logger.info("=" * 60)

    def _step(self, number: int, total: int, message: str):
        """Print a numbered processing step."""
        logger.info(f"[Step {number}/{total}] {message}")
    
    def initialize(self) -> bool:
        """
        Initialize and validate all system components.
        
        Returns:
            bool: True if initialization successful
        """
        self._section("Email Automation System - Initialization")
        
        # Validate configuration
        if not self._validate_config():
            return False
        
        # Initialize components
        try:
            self._step(1, 2, "Creating core components")
            self.email_fetcher = EmailFetcher(config.EMAIL_ADDRESS, config.EMAIL_PASSWORD)
            self.keyword_engine = KeywordEngine()
            self.response_generator = ResponseGenerator()
            self.email_sender = EmailSender(config.EMAIL_ADDRESS, config.EMAIL_PASSWORD)
            
            self._step(2, 2, "Initialization complete")
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
        
        self._section("Email Processing Run")
        logger.info(f"Mode: {'DRY RUN (no emails will be sent)' if dry_run else 'LIVE RUN'}")
        logger.info(f"Batch size: {batch_size}")
        
        # Connect to email
        self._step(1, 5, "Connecting to IMAP")
        if not self.email_fetcher.connect():
            logger.error("Failed to connect to email server")
            self.database.log_event("connection_error", "Failed to connect to IMAP")
            return self.stats
        
        # Connect to SMTP
        self._step(2, 5, "Connecting to SMTP")
        if not dry_run and not self.email_sender.connect():
            logger.error("Failed to connect to SMTP server")
            self.database.log_event("connection_error", "Failed to connect to SMTP")
            self.email_fetcher.disconnect()
            return self.stats
        if dry_run:
            logger.info("Skipping SMTP connection in dry run mode")
        
        try:
            # Fetch unread emails
            self._step(3, 5, "Fetching unread emails")
            unread_emails = self.email_fetcher.fetch_unread_emails(limit=batch_size)
            logger.info(f"Unread emails found: {len(unread_emails)}")
            if not unread_emails:
                logger.info("No new emails to process")
            
            # Process each email
            self._step(4, 5, "Processing emails")
            total_emails = len(unread_emails)
            for index, email_data in enumerate(unread_emails, start=1):
                self._process_email(email_data, dry_run, index, total_emails)
            
            # Log run statistics
            self._step(5, 5, "Run complete")
            logger.info("Run summary:")
            logger.info(f"- Total processed: {self.stats['total_processed']}")
            logger.info(f"- Emails sent: {self.stats['emails_sent']}")
            logger.info(f"- Skipped: {self.stats['skipped']}")
            logger.info(f"- Errors: {self.stats['errors']}")
            
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
    
    def _process_email(
        self,
        email_data: dict,
        dry_run: bool = False,
        email_index: int = 0,
        total_emails: int = 0
    ) -> bool:
        """
        Process a single email through the entire workflow.

        Args:
            email_data (dict): Email data from fetcher
            dry_run (bool): If True, don't send email
            email_index (int): Current email number in this run
            total_emails (int): Total emails in this run

        Returns:
            bool: True if processed successfully
        """
        email_uid = email_data["uid"]
        sender = email_data["sender"]
        subject = email_data["subject"]
        body = email_data["body"]
        received_date = email_data["received_date"]

        self.stats["total_processed"] += 1

        subject_preview = (subject or "(No Subject)").strip()
        if len(subject_preview) > 70:
            subject_preview = f"{subject_preview[:67]}..."

        prefix = f"[Email {email_index}/{total_emails}]" if total_emails else "[Email]"
        logger.info(f"{prefix} From: {sender}")
        logger.info(f"{prefix} Subject: {subject_preview}")

        # Check if already processed
        if self.database.email_processed(email_uid):
            logger.info(f"{prefix} Skipped (already processed)")
            self.stats["skipped"] += 1
            return False

        try:
            # Validate email body
            if not body or len(body.strip()) == 0:
                logger.warning(f"{prefix} Failed (empty email body)")
                self.database.add_processed_email(
                    email_uid, sender, subject, received_date,
                    "empty_body", False, "failed"
                )
                self.stats["errors"] += 1
                return False

            # Match keywords
            matches = self.keyword_engine.match_keywords(body)
            matched_keywords = self.keyword_engine.extract_unique_keywords(matches)
            logger.info(f"{prefix} Matched keywords: {matched_keywords or 'none'}")

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
                logger.info(f"{prefix} Dry run: response generation complete")

            # Record in database
            if sent_successfully or dry_run:
                self.database.add_processed_email(
                    email_uid, sender, subject, received_date,
                    matched_keywords, sent_successfully, "success"
                )

                if sent_successfully:
                    self.stats["emails_sent"] += 1
                    logger.info(f"{prefix} Completed (response sent)")
                else:
                    logger.info(f"{prefix} Completed (dry run, not sent)")
            else:
                self.database.add_processed_email(
                    email_uid, sender, subject, received_date,
                    matched_keywords, False, "failed"
                )
                self.stats["errors"] += 1
                logger.error(f"{prefix} Failed (send error)")

            # Mark as read in IMAP
            marked = self.email_fetcher.mark_as_read(email_uid)
            if not marked:
                logger.warning(f"{prefix} Warning: could not mark as read")

            return sent_successfully

        except Exception as e:
            logger.error(f"{prefix} Failed (unexpected error: {e})")
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
        self._section("System Statistics")
        logger.info(f"- Total emails processed: {stats.get('total_processed', 0)}")
        logger.info(f"- Successful: {stats.get('success_count', 0)}")
        logger.info(f"- Failed: {stats.get('failed_count', 0)}")
        logger.info(f"- Success rate: {stats.get('success_rate', 'N/A')}")


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
