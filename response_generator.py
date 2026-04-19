"""
Response Generator Module
Generates email responses based on matched keywords and their priorities.
Handles response merging and fallback scenarios.
"""

from typing import List, Tuple, Optional
import config
from utils.logger import get_logger

logger = get_logger(__name__)


class ResponseGenerator:
    """
    Generates email responses based on keyword matches.
    Prioritizes and merges multiple responses intelligently.
    """
    
    def __init__(self):
        """Initialize response generator with fallback response."""
        self.fallback_response = config.FALLBACK_RESPONSE
    
    def generate_response(
        self,
        matches: List[Tuple[str, int, str]],
        sender_email: str,
        sender_name: str = None,
        include_sender_greeting: bool = True
    ) -> str:
        """
        Generate response email body from matched keywords.
        
        Args:
            matches: List of (keyword, priority, response) tuples from keyword matching
            sender_email (str): Recipient email address
            sender_name (str): Recipient name (extracted from email if available)
            include_sender_greeting (bool): Whether to include personalized greeting
        
        Returns:
            str: Complete email body ready to send
        """
        try:
            if not matches:
                logger.info("No matches found, using fallback response")
                return self._format_email_body(
                    self.fallback_response,
                    sender_email,
                    sender_name,
                    include_sender_greeting
                )
            
            # Generate response based on matches
            response_body = self._merge_responses(matches)
            
            return self._format_email_body(
                response_body,
                sender_email,
                sender_name,
                include_sender_greeting
            )
        
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return self.fallback_response
    
    def _merge_responses(self, matches: List[Tuple[str, int, str]]) -> str:
        """
        Merge multiple response templates cleanly.
        Handles multiple matches by priority.
        
        Args:
            matches: Sorted list of (keyword, priority, response) tuples
        
        Returns:
            str: Merged response text
        """
        if not matches:
            return self.fallback_response
        
        if len(matches) == 1:
            # Single match - use response directly
            return matches[0][2]
        
        # Multiple matches - merge based on priority
        merged_response = "Thank you for reaching out. Here's the information you requested:\n\n"
        
        previous_priority = None
        for keyword, priority, response in matches:
            # Add priority separator if priority changes
            if previous_priority is not None and priority != previous_priority:
                merged_response += "\n---\n\n"
            
            # Clean response (remove common email signatures/footers)
            clean_response = response.strip()
            
            # Add keyword context
            merged_response += f"Regarding '{keyword}':\n{clean_response}\n\n"
            
            previous_priority = priority
        
        return merged_response.strip()
    
    def _format_email_body(
        self,
        body: str,
        recipient_email: str,
        recipient_name: Optional[str] = None,
        include_greeting: bool = True
    ) -> str:
        """
        Format email body with greeting and signature.
        
        Args:
            body (str): Main response body
            recipient_email (str): Recipient email for personalization
            recipient_name (str): Recipient name for greeting
            include_greeting (bool): Whether to include greeting
        
        Returns:
            str: Formatted complete email body
        """
        formatted_body = ""
        
        # Add greeting
        if include_greeting:
            if recipient_name:
                # Extract name from email address if not provided
                name_part = recipient_name.split("@")[0].replace(".", " ").title()
            else:
                name_part = recipient_email.split("@")[0].replace(".", " ").title()
            
            formatted_body += f"Hi {name_part},\n\n"
        
        # Add main body
        formatted_body += body + "\n\n"
        
        # Add signature
        signature = f"Best regards,\n{config.SENDER_NAME}\nAutomated Response System"
        formatted_body += signature
        
        return formatted_body
    
    def get_response_summary(
        self,
        matches: List[Tuple[str, int, str]]
    ) -> dict:
        """
        Get summary information about generated response.
        
        Args:
            matches: List of matched keywords
        
        Returns:
            dict: Summary with keyword count, priority info, etc.
        """
        return {
            "match_count": len(matches),
            "keywords": [m[0] for m in matches],
            "priorities": [m[1] for m in matches],
            "has_fallback": len(matches) == 0,
            "highest_priority": matches[0][1] if matches else None,
            "lowest_priority": matches[-1][1] if matches else None
        }
