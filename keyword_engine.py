"""
Keyword Matching Engine
Performs fuzzy and exact keyword matching on email content.
Supports priority-based matching for multiple keywords.
"""

import pandas as pd
from rapidfuzz import fuzz
from typing import List, Tuple, Optional
import config
from utils.logger import get_logger

logger = get_logger(__name__)


class KeywordEngine:
    """
    Handles keyword matching using fuzzy logic.
    Loads keywords from Excel and performs intelligent matching.
    """
    
    def __init__(self, excel_path: str = None):
        """
        Initialize keyword engine and load knowledge base.
        
        Args:
            excel_path (str): Path to Excel file with keywords
        """
        self.excel_path = excel_path or config.EXCEL_FILE_PATH
        self.keywords_df = None
        self.load_knowledge_base()
    
    def load_knowledge_base(self) -> bool:
        """
        Load keywords and responses from Excel file.
        
        Returns:
            bool: True if loaded successfully, False otherwise
        """
        try:
            if not self.excel_path.exists():
                logger.error(f"Excel file not found: {self.excel_path}")
                return False
            
            # Read Excel file
            self.keywords_df = pd.read_excel(
                self.excel_path,
                dtype={
                    config.EXCEL_COLUMNS["keyword"]: str,
                    config.EXCEL_COLUMNS["priority"]: int,
                    config.EXCEL_COLUMNS["response"]: str
                }
            )
            
            # Validate required columns
            required_columns = list(config.EXCEL_COLUMNS.values())
            missing_columns = [col for col in required_columns if col not in self.keywords_df.columns]
            
            if missing_columns:
                logger.error(f"Missing columns in Excel: {missing_columns}")
                return False
            
            # Clean data
            self.keywords_df = self.keywords_df.dropna(subset=[config.EXCEL_COLUMNS["keyword"]])
            self.keywords_df[config.EXCEL_COLUMNS["keyword"]] = \
                self.keywords_df[config.EXCEL_COLUMNS["keyword"]].str.lower().str.strip()
            
            logger.info(f"Loaded {len(self.keywords_df)} keywords from Excel")
            return True
        
        except pd.errors.EmptyDataError:
            logger.error("Excel file is empty")
            return False
        except Exception as e:
            logger.error(f"Error loading Excel file: {e}")
            return False
    
    def match_keywords(
        self,
        email_body: str,
        use_fuzzy: bool = True,
        threshold: int = None
    ) -> List[Tuple[str, int, str]]:
        """
        Find matching keywords in email body.
        Returns list of matched keywords with their priority and response.
        
        Args:
            email_body (str): Email body text to search
            use_fuzzy (bool): Whether to use fuzzy matching (default: True)
            threshold (int): Fuzzy matching threshold (default from config)
        
        Returns:
            List[Tuple[str, int, str]]: List of (keyword, priority, response) tuples,
                                        sorted by priority (descending)
        """
        if self.keywords_df is None or len(self.keywords_df) == 0:
            logger.warning("No keywords loaded")
            return []
        
        threshold = threshold or config.FUZZY_MATCH_THRESHOLD
        email_body_lower = email_body.lower()
        matched_keywords = []
        matched_keyword_set = set()  # To avoid duplicates
        
        try:
            for idx, row in self.keywords_df.iterrows():
                keyword = str(row[config.EXCEL_COLUMNS["keyword"]]).lower()
                priority = int(row[config.EXCEL_COLUMNS["priority"]])
                response = str(row[config.EXCEL_COLUMNS["response"]])
                
                # Avoid duplicate matches for same keyword
                if keyword in matched_keyword_set:
                    continue
                
                # Exact match (case-insensitive)
                if keyword in email_body_lower:
                    matched_keywords.append((keyword, priority, response))
                    matched_keyword_set.add(keyword)
                    logger.debug(f"Exact match found: {keyword}")
                
                # Fuzzy match if enabled
                elif use_fuzzy:
                    # Split email body into words for better matching
                    words = email_body_lower.split()
                    
                    for word in words:
                        # Clean word of punctuation
                        clean_word = ''.join(c for c in word if c.isalnum())
                        
                        # Use partial_ratio for substring matching
                        match_score = fuzz.partial_ratio(keyword, clean_word)
                        
                        if match_score >= threshold:
                            matched_keywords.append((keyword, priority, response))
                            matched_keyword_set.add(keyword)
                            logger.debug(
                                f"Fuzzy match found: {keyword} (score: {match_score}) "
                                f"in word '{clean_word}'"
                            )
                            break  # Move to next keyword after first match
        
        except Exception as e:
            logger.error(f"Error during keyword matching: {e}")
        
        # Sort by priority (descending) and return
        matched_keywords.sort(key=lambda x: x[1], reverse=True)
        
        if matched_keywords:
            logger.info(f"Matched {len(matched_keywords)} keywords: "
                       f"{[kw[0] for kw in matched_keywords]}")
        
        return matched_keywords
    
    def extract_unique_keywords(self, matches: List[Tuple[str, int, str]]) -> str:
        """
        Extract unique keyword strings from match results.
        
        Args:
            matches: List of (keyword, priority, response) tuples
        
        Returns:
            str: Comma-separated unique keywords
        """
        return ", ".join([match[0] for match in matches])
    
    def reload_knowledge_base(self) -> bool:
        """Reload keywords from Excel (useful for updates without restarting)."""
        logger.info("Reloading knowledge base...")
        return self.load_knowledge_base()
