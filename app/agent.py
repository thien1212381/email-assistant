from datetime import datetime, timedelta
from typing import Dict, List, Optional
import uuid

from .database import Database, EmailCategory
from .llm_provider import LLMProvider
from .meeting_detector import MeetingDetector
from .notification_system import NotificationSystem
from .utils import prepare_email_for_prompt, clean_email_content
import re
from sqlalchemy import text
import random


class EmailAgent:
    def __init__(self, db: Database, llm_provider: LLMProvider):
        self.db = db
        self.llm = llm_provider
        self.meeting_detector = MeetingDetector(db, llm_provider)
        self.notification_system = NotificationSystem(db)
    
    async def handle_user_query(self, nl_query: str) -> str:
        """Convert natural language query to a SQLite query."""
        
        # Generate a prompt to convert natural language to SQL
        prompt = f"Convert the following natural language query into a SQLite query.\n\nTable emails has schemas:\n"
        
        columns = [
            { "name": "subject", "type": "String" },
            { "name": "sender", "type": "String" },
            { "name": "recipients", "type": "String" },
            { "name": "content", "type": "String" },
            { "name": "timestamp", "type": "DateTime" },
            { "name": "category", "type": "Enum('Meetings','Important','Follow-Up','Spam')" },
            { "name": "is_read", "type": "Boolean" },
        ]
        
        prompt += '\n'.join([f"{col['name']} {col['type']}" for col in columns])
        prompt += f"\n\nQuery: {nl_query}\n\n"
    
        # Call the LLM provider to generate a SQL query
        result = await self.llm.generate_response(prompt)

        # Extract the SQL block from the result
        matches = re.findall(r'```sql\n(.*?)```', result, re.DOTALL)
        if matches:
            sql_block = matches[0].strip()
        else:
            return []
            
        # Execute the query on the database
        with self.db.Session() as session:
            result = session.execute(text(sql_block))
            rows = result.fetchall()
            columns = result.keys()

            if len(rows) == 0:
                return []

            result_dict = [{col: val for col, val in zip(columns, row)} for row in rows]
            print(result_dict)

            await self.llm.save_context(
                input=f"{nl_query}",
                output=",".join([f"{col}: {val}" for col, val in zip(columns, rows)])
            )
            return result_dict

    async def classify_email(self, email_data: dict) -> str:
        """Classify email into categories using LLM."""
        cleaned_data = prepare_email_for_prompt(email_data)
        return await self.llm.classify_email(
            subject=cleaned_data['subject'],
            content=cleaned_data['content']
        )

    async def generate_summary_emails(self, emails: List[Dict]) -> str:
        """Generate a summary of emails."""
        prompt = f"Generate a summary of the following emails:\n"
        for email in emails:
            cleaned_data = prepare_email_for_prompt(email)
            prompt += (
                f"Subject: {cleaned_data['subject']}\n"
                f"Sender: {cleaned_data['sender']}\n"
                f"Content: {cleaned_data['content']}\n\n"
            )
        return await self.llm.generate_response(prompt)

    async def get_meeting_info(self, email_data: dict) -> dict:
        """Extract meeting information from email."""
        cleaned_data = prepare_email_for_prompt(email_data)
        return await self.meeting_detector.detect_meeting(cleaned_data)

    async def generate_auto_reply(self, email_data: dict) -> str:
        """Generate an auto-reply based on email content."""
        cleaned_data = prepare_email_for_prompt(email_data)
        prompt = (
            f"Generate a professional reply based on email content:\n\n"
            f"Subject: {cleaned_data['subject']}\n"
            f"Sender: {cleaned_data['sender']}\n"
            f"Content: {cleaned_data['content']}\n\n"
        )
        return await self.llm.generate_response(prompt)

    async def process_email(self, email_data: dict) -> str:
        """Process an incoming email."""       
        # Clean and normalize email data
        cleaned_data = prepare_email_for_prompt(email_data)
        
        # Classify email
        category = await self.llm.classify_email(
            subject=cleaned_data['subject'],
            content=cleaned_data['content']
        )
        
        if category == "Meetings":
            # Check for meeting information
            meeting_info = await self.meeting_detector.detect_meeting(cleaned_data)
            if meeting_info:
                # Schedule meeting reminder
                await self.notification_system.schedule_meeting_reminder(meeting_info)
    
        email_data['category'] = category
        self.db.save_email(email_data)
        
        return category
