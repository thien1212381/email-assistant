from datetime import datetime, timedelta
import pytz
import uuid
from app.database import Database, EmailCategory

# Initialize database
db = Database()

# Sample data
sample_emails = [
    {
        "id": str(uuid.uuid4()),
        "subject": "Team Meeting - Project Update",
        "sender": "manager@company.com",
        "recipients": ["team@company.com"],
        "content": """
Hi team,

Let's meet today at 2 PM to discuss the project progress. We'll cover:
1. Current sprint status
2. Upcoming deliverables
3. Any blockers or concerns

Best regards,
Manager
        """,
        "timestamp": datetime.now(pytz.utc),
        "category": EmailCategory.MEETING,
        "is_read": False
    },
    {
        "id": str(uuid.uuid4()),
        "subject": "Urgent: Client Presentation Review Needed",
        "sender": "colleague@company.com",
        "recipients": ["you@company.com"],
        "content": """
Hey,

Could you please review the attached client presentation? I need your feedback by EOD today.

Thanks!
Colleague
        """,
        "timestamp": (datetime.now(pytz.utc) - timedelta(hours=2)),
        "category": EmailCategory.IMPORTANT,
        "is_read": False
    },
    {
        "id": str(uuid.uuid4()),
        "subject": "Weekly Newsletter",
        "sender": "newsletter@company.com",
        "recipients": ["all@company.com"],
        "content": """
Company Weekly Newsletter
- New product launch next week
- Team building event on Friday
- IT system maintenance this weekend
        """,
        "timestamp": (datetime.now(pytz.utc) - timedelta(hours=4)),
        "category": EmailCategory.IMPORTANT,
        "is_read": True
    },
    {
        "id": str(uuid.uuid4()),
        "subject": "Follow-up: Client Meeting Action Items",
        "sender": "client@external.com",
        "recipients": ["team@company.com"],
        "content": """
Hello,

Following up on our meeting, here are the action items:
1. Send updated proposal
2. Schedule technical review
3. Share timeline document

Please confirm when these can be completed.

Best regards,
Client
        """,
        "timestamp": (datetime.now(pytz.utc) - timedelta(hours=1)),
        "category": EmailCategory.FOLLOW_UP,
        "is_read": True
    },
    {
        "id": str(uuid.uuid4()),
        "subject": "Special Offer: Limited Time Discount",
        "sender": "marketing@external.com",
        "recipients": ["you@company.com"],
        "content": "Don't miss out on our special offer! Limited time discount available.",
        "timestamp": datetime.now(pytz.utc),
        "category": EmailCategory.SPAM,
        "is_read": False
    }
]

def seed_sample_data():
    """Seed the database with sample emails."""
    print("Seeding sample data...")
    
    # Save each email
    for email_data in sample_emails:
        try:
            db.save_email(email_data)
            print(f"Added email: {email_data['subject']}")
        except Exception as e:
            print(f"Error adding email {email_data['subject']}: {str(e)}")
    
    print("Sample data seeding completed!")

if __name__ == "__main__":
    seed_sample_data()
