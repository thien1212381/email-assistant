from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr

class Email(BaseModel):
    id: str
    subject: str
    sender: EmailStr
    recipients: List[EmailStr]
    content: str
    timestamp: datetime
    category: Optional[str] = None
    is_read: bool = False
    
class Meeting(BaseModel):
    id: str
    email_id: str
    title: str
    datetime: datetime
    attendees: List[str]
    location: Optional[str] = None
    description: Optional[str] = None
