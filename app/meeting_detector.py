from datetime import datetime, timedelta
from typing import List, Optional, Dict
import uuid
import random
import pytz
from .database import Database, EmailModel, MeetingModel
from .llm_provider import LLMProvider

class MeetingDetector:
    def __init__(self, db: Database, llm_provider: LLMProvider):
        self.db = db
        self.llm = llm_provider
        
    async def detect_meeting(self, email_data: dict) -> Optional[Dict]:
        """Detect if an email contains meeting information."""
        meeting_info = await self.llm.extract_meeting_info(
            subject=email_data['subject'],
            content=email_data['content']
        )
        
        if not meeting_info:
            return None
            
        # Ensure meeting has a unique ID
        meeting_info['id'] = str(uuid.uuid4())
            
        # Convert datetime string to datetime object
        meeting_time = datetime.fromisoformat(meeting_info['datetime'])
        if meeting_time.tzinfo is None:
            meeting_time = pytz.utc.localize(meeting_time)
        meeting_info['datetime'] = meeting_time
            
        # Save meeting to database
        with self.db.Session() as session:
            meeting = MeetingModel(
                id=meeting_info['id'],
                email_id=email_data['id'],
                title=meeting_info['title'],
                datetime=meeting_info['datetime'],
                attendees=str(meeting_info['attendees']),
                location=meeting_info.get('location'),
                description=meeting_info.get('description')
            )
            session.add(meeting)
            session.commit()
            
        return meeting_info
        
    def check_conflicts(self, meeting_time: datetime) -> List[Dict]:
        """Check for meeting conflicts within a time window."""
        # Ensure meeting_time is timezone-aware
        if meeting_time.tzinfo is None:
            meeting_time = pytz.utc.localize(meeting_time)
            
        start_window = meeting_time - timedelta(minutes=30)
        end_window = meeting_time + timedelta(minutes=30)
        
        with self.db.Session() as session:
            conflicts = session.query(MeetingModel).filter(
                MeetingModel.datetime.between(start_window, end_window)
            ).all()
            
            return [self._meeting_to_dict(meeting) for meeting in conflicts]
            
    def generate_alternative_times(self, meeting_time: datetime, conflicts: List[Dict]) -> List[str]:
        """Generate alternative times for a meeting."""
        # Ensure meeting_time is timezone-aware
        if meeting_time.tzinfo is None:
            meeting_time = pytz.utc.localize(meeting_time)
            
        alternative_times = []
        attempts = 0
        while len(alternative_times) < 3 and attempts < 10:
            attempts += 1
            alternative_time = meeting_time + timedelta(hours=random.randint(1, 24))
            
            # Convert conflict datetimes to datetime objects if they're strings
            conflict_times = []
            for conflict in conflicts:
                conflict_time = conflict['datetime']
                if isinstance(conflict_time, str):
                    conflict_time = datetime.fromisoformat(conflict_time)
                if conflict_time.tzinfo is None:
                    conflict_time = pytz.utc.localize(conflict_time)
                conflict_times.append(conflict_time)
            
            # Check for conflicts
            has_conflict = False
            for conflict_time in conflict_times:
                if alternative_time > conflict_time - timedelta(minutes=30) and alternative_time < conflict_time + timedelta(minutes=30):
                    has_conflict = True
                    break
                    
            if not has_conflict:
                with self.db.Session() as session:
                    existing_meetings = session.query(MeetingModel).filter(
                        MeetingModel.datetime == alternative_time
                    ).all()
                    if not existing_meetings:
                        alternative_times.append(alternative_time.isoformat())
                
        return alternative_times
        
    def get_upcoming_meetings(self, hours_ahead: int = 24) -> List[Dict]:
        """Get upcoming meetings within the specified time window."""
        now = datetime.now(pytz.utc)
        end_time = now + timedelta(hours=hours_ahead)
        
        with self.db.Session() as session:
            meetings = session.query(MeetingModel).filter(
                MeetingModel.datetime.between(now, end_time)
            ).all()
            
            return [self._meeting_to_dict(meeting) for meeting in meetings]
            
    def _meeting_to_dict(self, meeting: MeetingModel) -> Dict:
        """Convert a MeetingModel to a dictionary."""
        meeting_time = meeting.datetime
        if meeting_time.tzinfo is None:
            meeting_time = pytz.utc.localize(meeting_time)
            
        return {
            'id': meeting.id,
            'email_id': meeting.email_id,
            'title': meeting.title,
            'datetime': meeting_time,
            'attendees': eval(meeting.attendees),
            'location': meeting.location,
            'description': meeting.description
        }
