import asyncio
import os
from app.gmail_provider import GmailProvider
from app.database import Database
from app.agent import EmailAgent
from app.llm_provider import get_llm_provider
from app.email_processor import EmailProcessor

async def main():
    # Initialize components
    db = Database()
    llm_provider = get_llm_provider("openai")
    agent = EmailAgent(db=db, llm_provider=llm_provider)
    
    # Initialize Gmail provider
    gmail = GmailProvider(
        credentials_path="config/credentials.json",
        token_path="config/token.pickle"
    )
    
    # Authenticate with Gmail
    print("Authenticating with Gmail...")
    authenticated = await gmail.authenticate()
    if not authenticated:
        print("Failed to authenticate with Gmail")
        return
    print("Successfully authenticated!")
    
    # Create email processor
    processor = EmailProcessor(
        email_provider=gmail,
        database=db,
        agent=agent,
        sync_interval=300,  # 5 minutes
        max_emails_per_sync=15
    )
    
    try:
        # Start the processor
        print("\nStarting email processor...")
        await processor.start()
    except KeyboardInterrupt:
        # Stop the processor on Ctrl+C
        print("\nStopping email processor...")
        await processor.stop()

if __name__ == "__main__":
    asyncio.run(main())
