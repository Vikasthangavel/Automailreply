"""
Email Fetcher Module
Handles IMAP connection to Gmail and fetches unread emails.
"""

import imaplib
import email
from email.header import decode_header
from email.message import Message
from typing import List, Tuple, Optional
from datetime import datetime
import config
from utils.logger import get_logger

logger = get_logger(__name__)


class EmailFetcher:
    """
    Manages IMAP connection to Gmail inbox.
    Fetches and parses unread emails.
    """
    
    def __init__(self, email_address: str, password: str):
        """
        Initialize email fetcher with credentials.
        
        Args:
            email_address (str): Gmail address
            password (str): Gmail app password (not regular password for security)
        """
        self.email_address = email_address
        self.password = password
        self.imap_connection = None
    
    def connect(self) -> bool:
        """
        Establish secure IMAP connection to Gmail.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.imap_connection = imaplib.IMAP4_SSL(
                config.GMAIL_IMAP_SERVER,
                config.GMAIL_IMAP_PORT
            )
            self.imap_connection.login(self.email_address, self.password)
            logger.info(f"Successfully connected to Gmail for {self.email_address}")
            return True
        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP connection error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during IMAP connection: {e}")
            return False
    
    def disconnect(self):
        """Close IMAP connection."""
        try:
            if self.imap_connection:
                self.imap_connection.close()
                logger.info("IMAP connection closed")
        except Exception as e:
            logger.warning(f"Error closing IMAP connection: {e}")
    
    def _decode_email_header(self, header_text: str) -> str:
        """
        Decode email headers that may contain encoded text.
        
        Args:
            header_text (str): Raw header text
        
        Returns:
            str: Decoded header text
        """
        if not header_text:
            return ""
        
        try:
            # Handle encoded words in headers
            decoded_parts = decode_header(header_text)
            decoded_text = ""
            
            for part, charset in decoded_parts:
                if isinstance(part, bytes):
                    try:
                        charset = charset or "utf-8"
                        decoded_text += part.decode(charset, errors="ignore")
                    except Exception:
                        decoded_text += str(part)
                else:
                    decoded_text += str(part) if part else ""
            
            return decoded_text.strip()
        except Exception as e:
            logger.warning(f"Error decoding header: {e}")
            return header_text
    
    def _get_email_body(self, msg: Message) -> str:
        """
        Extract plain text body from email message.
        Handles multipart and non-multipart emails.
        
        Args:
            msg (Message): Email message object
        
        Returns:
            str: Email body text
        """
        body = ""
        
        try:
            if msg.is_multipart():
                # For multipart emails, get plain text first, then HTML
                for part in msg.walk():
                    content_type = part.get_content_type()
                    
                    if content_type == "text/plain":
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or "utf-8"
                        body += payload.decode(charset, errors="ignore")
                    elif content_type == "text/html" and not body:
                        # Use HTML only if no plain text available
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or "utf-8"
                        html_body = payload.decode(charset, errors="ignore")
                        # Simple HTML stripping (production should use BeautifulSoup)
                        import re
                        body = re.sub("<[^<]+?>", "", html_body)
            else:
                # Non-multipart email
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset() or "utf-8"
                    body = payload.decode(charset, errors="ignore")
                else:
                    body = msg.get_payload()
        except Exception as e:
            logger.warning(f"Error extracting email body: {e}")
            body = msg.get_payload()
        
        return body.strip()
    
    def fetch_unread_emails(self, limit: int = None) -> List[dict]:
        """
        Fetch unread emails from INBOX.
        
        Args:
            limit (int): Maximum number of emails to fetch (None = all)
        
        Returns:
            List[dict]: List of email dictionaries with keys:
                - uid: IMAP unique identifier
                - sender: Sender email address
                - subject: Email subject
                - body: Email body text
                - received_date: When email was received
        """
        unread_emails = []
        
        try:
            # Select INBOX folder
            status, mailbox_data = self.imap_connection.select("INBOX")
            if status != "OK":
                logger.error(f"Failed to select INBOX: {mailbox_data}")
                return unread_emails
            
            # Search for unread emails
            status, email_ids = self.imap_connection.search(None, "UNSEEN")
            if status != "OK":
                logger.error(f"Failed to search unread emails: {email_ids}")
                return unread_emails
            
            email_id_list = email_ids[0].split()
            
            # Limit number of emails if specified
            if limit:
                email_id_list = email_id_list[-limit:]
            
            logger.info(f"Found {len(email_id_list)} unread emails")
            
            # Fetch each email
            for email_id in email_id_list:
                try:
                    status, msg_data = self.imap_connection.fetch(email_id, "(RFC822)")
                    if status != "OK":
                        logger.warning(f"Failed to fetch email {email_id}")
                        continue
                    
                    # Parse email message
                    msg = email.message_from_bytes(msg_data[0][1])
                    
                    # Extract email details
                    sender = self._decode_email_header(msg.get("From", ""))
                    subject = self._decode_email_header(msg.get("Subject", "(No Subject)"))
                    body = self._get_email_body(msg)
                    received_date_str = msg.get("Date", "")
                    
                    # Parse received date
                    try:
                        from email.utils import parsedate_to_datetime
                        received_date = parsedate_to_datetime(received_date_str)
                    except Exception:
                        received_date = datetime.now()
                    
                    # Convert email_id to string (it's bytes from IMAP)
                    email_uid = email_id.decode() if isinstance(email_id, bytes) else str(email_id)
                    
                    email_dict = {
                        "uid": email_uid,
                        "sender": sender,
                        "subject": subject,
                        "body": body,
                        "received_date": received_date
                    }
                    
                    unread_emails.append(email_dict)
                    logger.debug(f"Fetched email from {sender}: {subject}")
                
                except Exception as e:
                    logger.error(f"Error parsing email {email_id}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error fetching unread emails: {e}")
        
        return unread_emails
    
    def mark_as_read(self, email_uid: str) -> bool:
        """
        Mark email as read in IMAP.
        
        Args:
            email_uid (str): Email UID to mark as read
        
        Returns:
            bool: True if successful
        """
        try:
            status, _ = self.imap_connection.store(email_uid, "+FLAGS", "\\Seen")
            return status == "OK"
        except Exception as e:
            logger.warning(f"Error marking email {email_uid} as read: {e}")
            return False
