import html
import logging
import re
import unicodedata
from typing import List

logger = logging.getLogger("dataforge.clean.service")

class TextCleaner:
    """
    Data Cleaning & Normalization Engine for text in the DataForge AI pipeline.
    """
    def __init__(self) -> None:
        # Regex patterns for boilerplate, navigation, and advertisement filtering
        self.ad_patterns = [
            re.compile(r'\b(?:sponsored|advertisement|ad\b|ads\b|promoted content|ads by google)\b', re.IGNORECASE),
            re.compile(r'\b(?:buy now|click here to|shop the latest|special offer)\b', re.IGNORECASE)
        ]
        
        self.cookie_patterns = [
            re.compile(r'\b(?:cookie policy|privacy policy|use cookies|agree to our use of cookies|ensure you get the best experience)\b', re.IGNORECASE)
        ]
        
        self.nav_patterns = [
            re.compile(r'\b(?:terms of service|contact us|sign in|log in|register|newsletter|subscribe|all rights reserved|copyright ©)\b', re.IGNORECASE),
            re.compile(r'^\s*(?:home|about|features|pricing|blog|contact)\s*$', re.IGNORECASE)
        ]

    def fix_encoding(self, text: str) -> str:
        """Repair double-encoded UTF-8 strings or character encoding artifacts word-by-word."""
        if not text:
            return ""
            
        def repair_word(match: re.Match) -> str:
            word = match.group(0)
            try:
                # Try to decode word as double-encoded (UTF-8 bytes read as Windows-1252/Latin-1)
                return word.encode('latin-1').decode('utf-8')
            except (UnicodeEncodeError, UnicodeDecodeError):
                return word
                
        # Run repair on each non-whitespace sequence to handle mixed valid/invalid UTF-8 correctly
        return re.sub(r'\S+', repair_word, text)

    def clean_html(self, text: str) -> str:
        """Remove HTML tags, block elements (nav, footer, header), and unescape entities."""
        if not text:
            return ""
            
        # 1. Strip structural block elements along with their contents (nav, footer, header, scripts, styles)
        structural_tags = ['script', 'style', 'nav', 'footer', 'header', 'aside', 'form', 'noscript', 'iframe']
        for tag in structural_tags:
            text = re.sub(rf'<{tag}\b[^>]*>[\s\S]*?</{tag}>', ' ', text, flags=re.IGNORECASE)
            
        # 2. Strip all remaining HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        
        # 3. Unescape HTML entities (e.g. &amp; -> &, &#8217; -> ')
        text = html.unescape(text)
        
        return text

    def normalize_unicode(self, text: str) -> str:
        """Apply Unicode NFKC normalization to flatten characters."""
        if not text:
            return ""
        return unicodedata.normalize("NFKC", text)

    def cleanup_punctuation(self, text: str) -> str:
        """Standardize non-standard punctuation (smart quotes, dashes, ellipsis)."""
        if not text:
            return ""
            
        # Define replacements for smart quotes, special hyphens, ellipses, etc.
        replacements = {
            '“': '"', '”': '"',  # Smart double quotes
            '‘': "'", '’': "'",  # Smart single quotes
            '′': "'", '`': "'",  # Primes and backticks
            '–': '-', '—': '-',  # En-dash and Em-dash
            '…': '...',          # Ellipsis
            '•': '*',            # Bullet points
            '™': '(TM)', '®': '(R)', '©': '(C)' # Symbols
        }
        
        for char, repl in replacements.items():
            text = text.replace(char, repl)
            
        return text

    def remove_boilerplate_and_nav(self, text: str) -> str:
        """Remove navigation menus, cookie policies, disclaimers, and ads line-by-line."""
        if not text:
            return ""
            
        lines = text.splitlines()
        cleaned_lines: List[str] = []
        
        for line in lines:
            trimmed = line.strip()
            if not trimmed:
                cleaned_lines.append("")
                continue
                
            # Heuristic 1: Filter out lines matching advertisement patterns
            if any(pat.search(trimmed) for pat in self.ad_patterns):
                logger.debug(f"Filtered ad line: {trimmed}")
                continue
                
            # Heuristic 2: Filter out cookie policy disclaimers
            if any(pat.search(trimmed) for pat in self.cookie_patterns):
                logger.debug(f"Filtered cookie disclaimer: {trimmed}")
                continue
                
            # Heuristic 3: Filter out navigation links / generic footers
            if any(pat.search(trimmed) for pat in self.nav_patterns):
                logger.debug(f"Filtered nav/footer line: {trimmed}")
                continue
                
            # Heuristic 4: Filter out menu lists with separators (e.g., "Home | Blog | Terms")
            if (trimmed.count('|') >= 2 or trimmed.count('•') >= 2 or trimmed.count('·') >= 2 or trimmed.count('*') >= 2) and len(trimmed) < 120:
                logger.debug(f"Filtered menu line: {trimmed}")
                continue
                
            # Heuristic 5: Skip lines that are only short navigation link remnants (e.g. "Main Menu", "Back to Top")
            if len(trimmed) < 20 and any(kw in trimmed.lower() for kw in ["menu", "next", "prev", "previous", "top", "view", "share", "follow"]):
                logger.debug(f"Filtered short link line: {trimmed}")
                continue
                
            cleaned_lines.append(line)
            
        return "\n".join(cleaned_lines)

    def normalize_whitespace(self, text: str) -> str:
        """Collapse multiple spaces/tabs, normalize line breaks, and strip margins."""
        if not text:
            return ""
            
        # 1. Normalize line endings and collapse empty lines (allow at most one blank line for paragraph separations)
        lines = text.splitlines()
        normalized_lines: List[str] = []
        last_was_empty = False
        
        for line in lines:
            trimmed = re.sub(r'[ \t]+', ' ', line).strip()
            if not trimmed:
                if not last_was_empty:
                    normalized_lines.append("")
                    last_was_empty = True
            else:
                normalized_lines.append(trimmed)
                last_was_empty = False
                
        # Reconnect lines
        text = "\n".join(normalized_lines)
        
        # 2. Final strip
        return text.strip()

    def clean_document(self, text: str) -> str:
        """Run the full text cleaning pipeline chain."""
        if not text:
            return ""
            
        text = self.fix_encoding(text)
        text = self.clean_html(text)
        text = self.remove_boilerplate_and_nav(text)
        text = self.normalize_unicode(text)
        text = self.cleanup_punctuation(text)
        text = self.normalize_whitespace(text)
        
        return text
