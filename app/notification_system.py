from datetime import datetime, timedelta
from typing import List, Dict, Optional
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from .database import Database, MeetingModel
import pytz

class NotificationSystem:
    def __init__(self, db: Database):
        self.db = db
        self.scheduler = AsyncIOScheduler()
        
    def start(self):
        """Start the scheduler."""
        self.scheduler.start()
        
    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        
    async def schedule_meeting_reminder(self, meeting: Dict):
        """Schedule a reminder for a meeting."""
        # Get meeting time
        meeting_time = meeting['datetime'] if isinstance(meeting['datetime'], datetime) else datetime.fromisoformat(meeting['datetime'])
        
        # Ensure meeting time is timezone-aware
        if meeting_time.tzinfo is None:
            meeting_time = pytz.utc.localize(meeting_time)
        
        # Schedule reminder 15 minutes before
        reminder_time = meeting_time - timedelta(minutes=15)
        
        # Only schedule if the reminder time is in the future
        if reminder_time > datetime.now(pytz.utc):
            self.scheduler.add_job(
                self.send_meeting_reminder,
                'date',
                run_date=reminder_time,
                args=[meeting],
                id=f"reminder_{meeting['id']}"
            )
            
    async def send_meeting_reminder(self, meeting: Dict):
        """Send a reminder notification for a meeting."""
        # In a real application, this would integrate with various notification systems
        # For now, we'll just print to console
        print(f"\n🔔 MEETING REMINDER 🔔")
        print(f"Title: {meeting['title']}")
        print(f"Time: {meeting['datetime']}")
        print(f"Location: {meeting.get('location', 'Not specified')}")
        if 'attendees' in meeting:
            print(f"Attendees: {', '.join(meeting['attendees'])}")
        print()
        
    async def notify_meeting_conflict(self, original_meeting: Dict, conflicts: List[Dict], suggestions: List[str]):
        """Notify about meeting conflicts and suggest alternative times."""
        print(f"\n⚠️ MEETING CONFLICT DETECTED ⚠️")
        print(f"Your meeting '{original_meeting['title']}' at {original_meeting['datetime']} conflicts with:")
        
        for conflict in conflicts:
            print(f"- {conflict['title']} at {conflict['datetime']}")
            
        print("\nSuggested alternative times:")
        for i, time in enumerate(suggestions, 1):
            print(f"{i}. {time}")
        print()
        
    def cancel_reminder(self, meeting_id: str):
        """Cancel a scheduled reminder."""
        try:
            self.scheduler.remove_job(f"reminder_{meeting_id}")
        except:
            pass
            
    def schedule_all_reminders(self):
        """Schedule reminders for all upcoming meetings."""
        with self.db.Session() as session:
            now = datetime.now(pytz.utc)
            upcoming_meetings = session.query(MeetingModel).filter(
                MeetingModel.datetime > now
            ).all()
            
            for meeting in upcoming_meetings:
                meeting_time = meeting.datetime
                if meeting_time.tzinfo is None:
                    meeting_time = pytz.utc.localize(meeting_time)
                
                reminder_time = meeting_time - timedelta(minutes=15)
                asyncio.create_task(
                    self.schedule_meeting_reminder(
                        {
                            'id': meeting.id,
                            'title': meeting.title,
                            'datetime': meeting_time,
                            'location': meeting.location,
                            'attendees': eval(meeting.attendees)
                        }
                    )
                )
