import re
from typing import Optional, Dict, List, Union
from html import unescape
import unicodedata
import json

def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text by removing extra spaces, newlines, and tabs."""
    # Replace multiple whitespace characters with a single space
    text = re.sub(r'\s+', ' ', text)
    # Remove leading/trailing whitespace
    return text.strip()

def clean_html(text: str) -> str:
    """Remove HTML tags and decode HTML entities."""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode HTML entities
    text = unescape(text)
    return text

def normalize_unicode(text: str) -> str:
    """Normalize Unicode characters to their closest ASCII representation."""
    # Normalize unicode characters (e.g., convert é to e)
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')

def remove_urls(text: str) -> str:
    """Remove URLs from text."""
    return re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)

def remove_email_signatures(text: str) -> str:
    """Remove common email signature patterns."""
    # List of common signature markers
    signature_markers = [
        r'Best regards,',
        r'Regards,',
        r'Sincerely,',
        r'Thanks,',
        r'Thank you,',
        r'Cheers,',
        r'--\s*\n',  # Common signature separator
        r'Sent from my iPhone',
        r'Sent from my iPad',
        r'Get Outlook for',
    ]
    
    # Create pattern to match any signature marker and everything that follows
    pattern = '|'.join(f'({marker}.*$)' for marker in signature_markers)
    return re.sub(pattern, '', text, flags=re.MULTILINE | re.DOTALL)

def truncate_text(text: str, max_length: int = 100, add_ellipsis: bool = True) -> str:
    """Truncate text to specified length, optionally adding ellipsis."""
    if len(text) <= max_length:
        return text
    
    truncated = text[:max_length].rstrip()
    if add_ellipsis:
        truncated += '...'
    return truncated

def clean_email_content(content: str, max_length: Optional[int] = None) -> str:
    """Clean and normalize email content for LLM processing."""
    # Apply cleaning steps in sequence
    content = clean_html(content)
    content = normalize_whitespace(content)
    content = normalize_unicode(content)
    content = remove_urls(content)
    content = remove_email_signatures(content)
    
    if max_length:
        content = truncate_text(content, max_length)
    
    return content

def prepare_email_for_prompt(
    email_data: Dict[str, Union[str, List, Dict]],
    content_max_length: int = 1000,
    subject_max_length: int = 50
) -> Dict[str, str]:
    """Prepare email data for LLM prompt by cleaning and normalizing fields."""
    cleaned_data = email_data.copy()
    
    if 'subject' in email_data:
        cleaned_data['subject'] = clean_email_content(
            str(email_data['subject']),
            subject_max_length
        )
    
    if 'content' in email_data:
        cleaned_data['content'] = clean_email_content(
            str(email_data['content']),
            content_max_length
        )
    
    if 'sender' in email_data:
        cleaned_data['sender'] = normalize_whitespace(str(email_data['sender']))
    
    if 'recipients' in email_data:
        if isinstance(email_data['recipients'], list):
            cleaned_data['recipients'] = [
                normalize_whitespace(str(r)) for r in email_data['recipients']
            ]
        elif isinstance(email_data['recipients'], str):
            try:
                # Try to parse JSON string
                recipients = json.loads(email_data['recipients'])
                cleaned_data['recipients'] = [
                    normalize_whitespace(str(r)) for r in recipients
                ]
            except json.JSONDecodeError:
                cleaned_data['recipients'] = [
                    normalize_whitespace(email_data['recipients'])
                ]
    
    return cleaned_data

def estimate_tokens(text: str) -> int:
    """Roughly estimate the number of tokens in a text.
    
    This is a simple estimation based on whitespace-split words.
    For more accurate counts, use the specific tokenizer of your LLM.
    """
    # Split on whitespace and punctuation
    words = re.findall(r'\b\w+\b', text)
    # Rough estimate: 1 word ≈ 1.3 tokens (OpenAI GPT average)
    return int(len(words) * 1.3)
