import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
import logging
from enum import Enum

from .email_provider import EmailProvider, EmailMessage
from .database import Database
from .agent import EmailAgent
from app import agent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailProcessor:
    def __init__(
        self,
        email_provider: EmailProvider,
        database: Database,
        agent: EmailAgent,
        sync_interval: int = 300,  # 5 minutes
        max_emails_per_sync: int = 50
    ):
        self.provider = email_provider
        self.db = database
        self.agent = agent
        self.sync_interval = sync_interval
        self.max_emails_per_sync = max_emails_per_sync
        self._last_sync = None
        self._running = False
    
    async def start(self):
        """Start the email processor."""
        if self._running:
            return
        
        self._running = True
        logger.info("Starting email processor...")
        
        # Initial sync
        await self.sync_emails()
        
        # Start background sync
        while self._running:
            await asyncio.sleep(self.sync_interval)
            await self.sync_emails()
    
    async def stop(self):
        """Stop the email processor."""
        self._running = False
        logger.info("Stopping email processor...")
    
    async def sync_emails(self):
        """Sync emails from provider to local database."""
        try:
            logger.info("Starting email sync...")
            
            # Fetch new emails
            query = "is:unread" if self._last_sync else None
            emails = await self.provider.fetch_emails(
                max_results=self.max_emails_per_sync,
                query=query
            )
            
            if not emails:
                logger.info("No new emails to sync")
                return
            
            logger.info(f"Found {len(emails)} new emails")
            
            # Process each email
            for email in emails:
                await self.process_email(email)
            
            self._last_sync = datetime.now()
            logger.info("Email sync completed")
            
        except Exception as e:
            logger.error(f"Error during email sync: {str(e)}")
    
    async def process_email(self, email: EmailMessage):
        """Process a single email."""
        logger.info(f"Processing email: {email.subject}")

        email_data = {
            k: v for k, v in email.model_dump().items() 
            if k in ['id', 'subject', 'sender', 'recipients', 'content', 
                    'timestamp', 'thread_id', 'labels']
        }

        is_new = await self.db.sync_email(email_data)
        if is_new:
            category = await self.agent.process_email(email_data)
            logger.info(f"Email category: {email_data['subject']} - {category}")

            await self.provider.add_label(email_data["id"], f"G.{category}") # add prefix G. for not conflict with gmail label.

            logger.info(f"Email processed successfully: {email_data['subject']} - {is_new}")
