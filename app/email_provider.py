from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel

class EmailMessage(BaseModel):
    id: str
    subject: str
    sender: str
    recipients: List[str]
    content: str
    timestamp: datetime
    thread_id: Optional[str] = None
    labels: List[str] = []
    attachments: List[Dict] = []

class EmailProvider(ABC):
    """Abstract base class for email providers."""
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the email provider."""
        pass
    
    @abstractmethod
    async def fetch_emails(self, 
                          max_results: int = 10,
                          query: str = None,
                          include_spam: bool = False) -> List[EmailMessage]:
        """Fetch emails from the provider."""
        pass
    
    @abstractmethod
    async def mark_as_read(self, message_id: str) -> bool:
        """Mark an email as read."""
        pass
    
    @abstractmethod
    async def mark_as_unread(self, message_id: str) -> bool:
        """Mark an email as unread."""
        pass
    
    @abstractmethod
    async def add_label(self, message_id: str, label: str) -> bool:
        """Add a label to an email."""
        pass
    
    @abstractmethod
    async def remove_label(self, message_id: str, label: str) -> bool:
        """Remove a label from an email."""
        pass
    
    @abstractmethod
    async def send_email(self, 
                        to: List[str],
                        subject: str,
                        content: str,
                        cc: List[str] = None,
                        bcc: List[str] = None,
                        attachments: List[Dict] = None) -> bool:
        """Send an email."""
        pass
    
    @abstractmethod
    async def get_thread(self, thread_id: str) -> List[EmailMessage]:
        """Get all messages in a thread."""
        pass
