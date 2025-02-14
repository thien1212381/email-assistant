from sqlalchemy import create_engine, Column, String, DateTime, Text, ForeignKey, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os
import json
from datetime import datetime
from typing import Dict, List, Optional
from datetime import time
from enum import Enum
import uuid

Base = declarative_base()

class EmailCategory(str, Enum):
    MEETING = "Meetings"
    IMPORTANT = "Important"
    FOLLOW_UP = "Follow-Up"
    SPAM = "Spam"

class EmailModel(Base):
    __tablename__ = 'emails'
    
    id = Column(String, primary_key=True)
    subject = Column(String)
    sender = Column(String)
    recipients = Column(String)  # Stored as string representation of list
    content = Column(String)
    timestamp = Column(DateTime, default=datetime.now)
    category = Column(String)
    is_read = Column(Boolean, default=False)
    
    # Relationships
    meetings = relationship("MeetingModel", back_populates="email")

class MeetingModel(Base):
    __tablename__ = 'meetings'
    
    id = Column(String, primary_key=True)
    email_id = Column(String, ForeignKey('emails.id'))
    title = Column(String)
    datetime = Column(DateTime)
    attendees = Column(String)  # Stored as string representation of list
    location = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    
    # Relationships
    email = relationship("EmailModel", back_populates="meetings")

class MessageModel(Base):
    __tablename__ = 'messages'
    
    id = Column(String, primary_key=True)
    role = Column(String)  # 'user' or 'assistant'
    content = Column(String)
    timestamp = Column(DateTime, default=datetime.now)

class Database:
    def __init__(self, db_path: str = "data/emails.db"):
        """Initialize database connection."""
        # Ensure data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Create engine and initialize tables
        self.engine = create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        
        # Create chat database
        chat_db_path = os.path.join(os.path.dirname(db_path), "chat.db")
        self.chat_engine = create_engine(f'sqlite:///{chat_db_path}')
        Base.metadata.create_all(self.chat_engine)
        self.ChatSession = sessionmaker(bind=self.chat_engine)

    def create_tables(self) -> None:
        """Create all database tables."""
        Base.metadata.create_all(self.engine)
        
    def save_email(self, email_data: Dict) -> None:
        """Save an email to the database."""
        with self.Session() as session:
            email = EmailModel(
                id=email_data['id'],
                subject=email_data['subject'],
                sender=email_data['sender'],
                recipients=str(email_data['recipients']),
                content=email_data['content'],
                timestamp=email_data.get('timestamp', datetime.now()),
                category=email_data.get('category'),
                is_read=email_data.get('is_read', False)
            )
            session.merge(email)
            session.commit()

    def add_message(self, role: str, content: str) -> MessageModel:
        session = self.ChatSession()
        try:
            message = MessageModel(
                id=str(uuid.uuid4()),
                role=role,
                content=content
            )
            session.add(message)
            session.commit()
            return message
        finally:
            session.close()

    def get_messages(self) -> List[MessageModel]:
        session = self.ChatSession()
        try:
            return session.query(MessageModel)\
                .order_by(MessageModel.timestamp).all()
        finally:
            session.close()

    def _email_to_dict(self, email: EmailModel) -> Dict:
        """Convert EmailModel to dictionary."""
        return {
            'id': email.id,
            'subject': email.subject,
            'sender': email.sender,
            'recipients': eval(email.recipients),
            'content': email.content,
            'timestamp': email.timestamp,
            'category': email.category,
            'is_read': email.is_read
        }

    def _meeting_to_dict(self, meeting: MeetingModel) -> Dict:
        """Convert MeetingModel to dictionary."""
        return {
            'id': meeting.id,
            'title': meeting.title,
            'datetime': meeting.datetime,
            'location': meeting.location,
            'attendees': eval(meeting.attendees),
            'description': meeting.description,
            'email_id': meeting.email_id
        }
