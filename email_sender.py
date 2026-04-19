"""
Email Sender Module
Handles SMTP email sending via Gmail.
Supports both regular SMTP and future API integration.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
import config
from utils.logger import get_logger

logger = get_logger(__name__)


class EmailSender:
    """
    Handles sending emails via SMTP (Gmail).
    Supports HTML and plain text emails.
    """
    
    def __init__(self, sender_email: str, sender_password: str):
        """
        Initialize email sender with credentials.
        
        Args:
            sender_email (str): Gmail address to send from
            sender_password (str): Gmail app password (not regular password)
        """
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.smtp_connection = None
    
    def connect(self) -> bool:
        """
        Establish SMTP connection to Gmail.
        
        Returns:
            bool: True if connection successful
        """
        try:
            self.smtp_connection = smtplib.SMTP(
                config.GMAIL_SMTP_SERVER,
                config.GMAIL_SMTP_PORT,
                timeout=10
            )
            self.smtp_connection.starttls()  # Upgrade to secure connection
            self.smtp_connection.login(self.sender_email, self.sender_password)
            logger.info(f"Successfully connected to SMTP for {self.sender_email}")
            return True
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP connection error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during SMTP connection: {e}")
            return False
    
    def disconnect(self):
        """Close SMTP connection."""
        try:
            if self.smtp_connection:
                self.smtp_connection.quit()
                logger.info("SMTP connection closed")
        except Exception as e:
            logger.warning(f"Error closing SMTP connection: {e}")
    
    def send_email(
        self,
        recipient_email: str,
        subject: str,
        body: str,
        html: bool = False,
        cc: List[str] = None,
        bcc: List[str] = None
    ) -> bool:
        """
        Send email via SMTP.
        
        Args:
            recipient_email (str): Recipient email address
            subject (str): Email subject
            body (str): Email body content
            html (bool): Whether body is HTML (default: False for plain text)
            cc (List[str]): CC email addresses
            bcc (List[str]): BCC email addresses
        
        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not self.smtp_connection:
            logger.error("SMTP connection not established. Call connect() first.")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["From"] = self.sender_email
            msg["To"] = recipient_email
            msg["Subject"] = subject
            
            if cc:
                msg["Cc"] = ", ".join(cc)
            
            # Attach body
            mime_type = "html" if html else "plain"
            msg.attach(MIMEText(body, mime_type, "utf-8"))
            
            # Prepare recipients list
            recipients = [recipient_email]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)
            
            # Send email
            self.smtp_connection.sendmail(
                self.sender_email,
                recipients,
                msg.as_string()
            )
            
            logger.info(f"Email sent successfully to {recipient_email}")
            return True
        
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending email to {recipient_email}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending email to {recipient_email}: {e}")
            return False
    
    def send_with_retry(
        self,
        recipient_email: str,
        subject: str,
        body: str,
        max_retries: int = None,
        html: bool = False
    ) -> bool:
        """
        Send email with automatic retry on failure.
        Useful for handling transient network issues.
        
        Args:
            recipient_email (str): Recipient email address
            subject (str): Email subject
            body (str): Email body
            max_retries (int): Maximum retry attempts (default from config)
            html (bool): Whether body is HTML
        
        Returns:
            bool: True if sent successfully after retries
        """
        max_retries = max_retries or config.MAX_RETRIES
        
        for attempt in range(1, max_retries + 1):
            try:
                if not self.smtp_connection:
                    if not self.connect():
                        logger.warning(f"Reconnection attempt {attempt} failed")
                        continue
                
                if self.send_email(recipient_email, subject, body, html):
                    return True
            
            except Exception as e:
                logger.warning(f"Send attempt {attempt}/{max_retries} failed: {e}")
                if attempt < max_retries:
                    # Try to reconnect for next attempt
                    try:
                        self.disconnect()
                    except Exception:
                        pass
                    self.smtp_connection = None
        
        logger.error(f"Failed to send email after {max_retries} attempts")
        return False
