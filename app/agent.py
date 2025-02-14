from datetime import datetime, timedelta
from typing import Dict, List, Optional
import uuid

from .database import Database, EmailModel
from .llm_provider import LLMProvider
from .meeting_detector import MeetingDetector
from .notification_system import NotificationSystem
import re
from sqlalchemy import text


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
        return await self.llm.classify_email(
            subject=email_data['subject'],
            content=email_data['content']
        )

    async def generate_summary_emails(self, emails: List[Dict]) -> str:
        """Generate a summary of emails."""
        prompt = f"Generate a summary of the following emails:\n\n"
        for email in emails:
            prompt += f"Subject: {email['subject']}\nSender: {email['sender']}\nContent: {email['content']}\n\n"
        return await self.llm.generate_response(prompt)

    async def get_meeting_info(self, email_data: dict) -> dict:
        """Extract meeting information from email."""
        return await self.meeting_detector.detect_meeting(email_data)

    async def generate_auto_reply(self, email_data: dict) -> str:
        """Generate an auto-reply based on email content."""
        prompt = f"Generate a professional reply based on email content.:\n\n"
        prompt += f"Subject: {email_data['subject']}\nSender: {email_data['sender']}\nContent: {email_data['content']}\n\n"
        return await self.llm.generate_response(prompt)

    async def process_email(self, email_data: dict) -> str:
        """Process an incoming email."""
        # Ensure email has an ID
        if 'id' not in email_data:
            email_data['id'] = str(uuid.uuid4())
            
        # Save email to database
        self.db.save_email(email_data)
        
        # Classify email
        category = await self.llm.classify_email(
            subject=email_data['subject'],
            content=email_data['content']
        )
        
        # Check for meeting information
        meeting_info = await self.meeting_detector.detect_meeting(email_data)
        if meeting_info:
            # Schedule meeting reminder
            await self.notification_system.schedule_meeting_reminder(meeting_info)
            
            # Check for conflicts
            conflicts = self.meeting_detector.check_conflicts(meeting_info['datetime'])
            if conflicts:
                # Generate alternative times
                suggestions = self.meeting_detector.generate_alternative_times(
                    meeting_info['datetime'],
                    conflicts
                )
                
                # Notify about conflicts
                await self.notification_system.notify_meeting_conflict(
                    meeting_info,
                    conflicts,
                    suggestions
                )
    
        self.db.save_email(email_data)
        
        return category
