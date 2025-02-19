from unicodedata import category
import streamlit as st
import json
from datetime import datetime
import pytz
import re
import asyncio
from typing import Dict, List
from urllib.parse import quote
from datetime import timedelta

from app.agent import EmailAgent
from app.database import Database
from app.llm_provider import get_llm_provider
import pandas as pd

# Initialize components
db = Database()
llm_provider = get_llm_provider("openai")
agent = EmailAgent(db=db, llm_provider=llm_provider)

def init_session_state():
    """Initialize session state variables."""  
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    if 'is_init' not in st.session_state:
        st.session_state.is_init = False

    if 'relative_emails' not in st.session_state:
        st.session_state.relative_emails = []

def display_chat_message(role: str, content: str, avatar: str = None):
    """Display a chat message with proper styling."""
    with st.chat_message(role, avatar=avatar):
        st.markdown(content)

def display_table_message(role: str, dataframe: pd.DataFrame, avatar: str = None):
    """Display a chat message with proper styling."""
    with st.chat_message(role, avatar=avatar):
        st.dataframe(dataframe)

def save_message(role: str, content: str):
    """Save message to both session state and database."""
    # Add to session state
    st.session_state.messages.append({"role": role, "content": content})
    # Save to database
    db.add_message(role, content)

async def get_assistant_response(prompt: str) -> dict:
    """Get response from assistant asynchronously."""
    relative_emails = st.session_state.relative_emails
    return await agent.handle_user_query(prompt, relative_emails)

async def generate_summary_emails(emails: List[Dict]) -> str:
    """Get all important and follow-up emails."""
    return await agent.generate_summary_emails(emails)

async def classify_email(email_data: dict) -> str:
    """Classify email into a category."""
    return await agent.classify_email(email_data)

async def get_meeting_info(email_data: dict) -> dict:
    """Extract meeting information from email."""
    return await agent.get_meeting_info(email_data)

async def generate_auto_reply(email_data: dict) -> str:
    """Generate an auto-reply based on email content."""
    return await agent.generate_auto_reply(email_data)

def display_meeting_info(meeting_info: dict):
    if not meeting_info:
        st.warning("No meeting information found in this email.")
        return

    st.subheader("📅 Meeting Details")
    
    # Create three columns for a clean layout
    col1, col2 = st.columns(2)
    
    with col1:
        # Meeting Title and Basic Info
        st.markdown("#### 🎯 Title")
        st.write(meeting_info.get('title', 'No title provided'))
        
        st.markdown("#### 👥 Attendees")
        attendees = meeting_info.get('attendees', [])
        if attendees:
            for attendee in attendees:
                st.write(f"- {attendee}")
        else:
            st.write("No attendees listed")

    with col2:
        # Date and Time Information
        st.markdown("#### 🕒 Date & Time")
        meeting_time = meeting_info.get('datetime')
        if meeting_time:
            if isinstance(meeting_time, str):
                try:
                    meeting_time = datetime.fromisoformat(meeting_time.replace('Z', '+00:00'))
                except ValueError:
                    st.error("Invalid datetime format")
                    return
            
            # Format date and time
            date_str = meeting_time.strftime("%B %d, %Y")
            time_str = meeting_time.strftime("%I:%M %p")
            st.write(f"📅 Date: {date_str}")
            st.write(f"⏰ Time: {time_str}")
            
            # Duration if available
            duration = meeting_info.get('duration')
            if duration:
                st.write(f"⏱️ Duration: {duration} minutes")
        else:
            st.write("Time not specified")

    # Location or Link (full width)
    st.markdown("#### 📍 Location/Link")
    location = meeting_info.get('location', 'No location provided')
    if location.startswith(('http', 'https')):
        st.markdown(f"🔗 [Join Meeting]({location})")
    else:
        st.write(location)

    # Additional Information or Notes
    if 'description' in meeting_info and meeting_info['description']:
        st.markdown("#### 📝 Additional Notes")
        st.write(meeting_info['description'])

    # Add calendar buttons
    st.markdown("#### 📅 Add to Calendar")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Add to Google Calendar"):
            # Generate Google Calendar link
            google_cal_link = create_google_calendar_link(meeting_info)
            st.markdown(f"[Open in Google Calendar]({google_cal_link})")
    
    with col2:
        if st.button("Add to Outlook"):
            # Generate Outlook link
            outlook_link = create_outlook_calendar_link(meeting_info)
            st.markdown(f"[Open in Outlook]({outlook_link})")
    
    with col3:
        if st.button("Download ICS"):
            # Generate ICS file
            ics_content = create_ics_file(meeting_info)
            st.download_button(
                label="Download ICS File",
                data=ics_content,
                file_name="meeting.ics",
                mime="text/calendar"
            )

def create_google_calendar_link(meeting_info: dict) -> str:
    """Create a Google Calendar event link."""
    base_url = "https://calendar.google.com/calendar/render?action=TEMPLATE"
    
    # Format date and time
    start_time = meeting_info['datetime']
    if isinstance(start_time, str):
        start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
    
    # Calculate end time
    duration = meeting_info.get('duration', 60)  # Default 1 hour
    end_time = start_time + timedelta(minutes=duration)
    
    # Format times for URL
    start_str = start_time.strftime('%Y%m%dT%H%M%SZ')
    end_str = end_time.strftime('%Y%m%dT%H%M%SZ')
    
    # Create query parameters
    params = {
        'text': meeting_info.get('title', 'Meeting'),
        'dates': f"{start_str}/{end_str}",
        'details': meeting_info.get('description', ''),
        'location': meeting_info.get('location', ''),
    }
    
    # Build URL
    query_string = '&'.join([f"{k}={quote(str(v))}" for k, v in params.items()])
    return f"{base_url}&{query_string}"

def create_outlook_calendar_link(meeting_info: dict) -> str:
    """Create an Outlook Web calendar event link."""
    base_url = "https://outlook.live.com/calendar/0/deeplink/compose"
    
    # Format date and time
    start_time = meeting_info['datetime']
    if isinstance(start_time, str):
        start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
    
    # Calculate end time
    duration = meeting_info.get('duration', 60)
    end_time = start_time + timedelta(minutes=duration)
    
    # Format times for URL
    start_str = start_time.strftime('%Y-%m-%dT%H:%M:%S')
    end_str = end_time.strftime('%Y-%m-%dT%H:%M:%S')
    
    # Create query parameters
    params = {
        'subject': meeting_info.get('title', 'Meeting'),
        'startdt': start_str,
        'enddt': end_str,
        'body': meeting_info.get('description', ''),
        'location': meeting_info.get('location', ''),
    }
    
    # Build URL
    query_string = '&'.join([f"{k}={quote(str(v))}" for k, v in params.items()])
    return f"{base_url}?{query_string}"

def create_ics_file(meeting_info: dict) -> str:
    """Create an ICS file content for calendar events."""
    # Format date and time
    start_time = meeting_info['datetime']
    if isinstance(start_time, str):
        start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
    
    # Calculate end time
    duration = meeting_info.get('duration', 60)
    end_time = start_time + timedelta(minutes=duration)
    
    # Format times for ICS
    start_str = start_time.strftime('%Y%m%dT%H%M%SZ')
    end_str = end_time.strftime('%Y%m%dT%H%M%SZ')
    
    # Create ICS content
    ics_content = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Email Assistant//Meeting//EN",
        "BEGIN:VEVENT",
        f"DTSTART:{start_str}",
        f"DTEND:{end_str}",
        f"SUMMARY:{meeting_info.get('title', 'Meeting')}",
        f"DESCRIPTION:{meeting_info.get('description', '')}",
        f"LOCATION:{meeting_info.get('location', '')}",
        "END:VEVENT",
        "END:VCALENDAR"
    ]
    
    return "\r\n".join(ics_content)

def main():
    st.set_page_config(
        page_title="Email Assistant",
        page_icon="📧",
        layout="wide"
    )
    
    st.title("📧 Email Assistant")
    
    # Initialize session state
    init_session_state()
    
    if st.session_state.is_init == False:
        messages = db.get_messages()
        st.session_state.messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        st.session_state.is_init = True
        st.rerun()
    
    # Main chat interface
    st.header("💬 Chat with Assistant")
    
    # Display chat history
    for message in st.session_state.messages:
        display_chat_message(
            role=message["role"],
            content=message["content"],
            avatar="🤖" if message["role"] == "assistant" else "👤"
        )
    
    # Chat input
    if prompt := st.chat_input("Ask me anything about your emails..."):
        # Save and display user message
        save_message("user", prompt)
        display_chat_message("user", prompt, "👤")
        
        # Generate and save assistant response
        with st.spinner("Generating response..."):
            data = asyncio.run(get_assistant_response(prompt))
            flow_category = data.get("flow_category")
            match flow_category:
                case "SqlQueryFlow":
                    emails = data.get("emails")
                    if len(emails) == 0:
                        response = "No emails found."
                        save_message("assistant", response)
                        display_chat_message("assistant", response, "🤖")
                    else:
                        df = pd.DataFrame(emails)
                        display_table_message("assistant", df, "🤖")
                        st.session_state.relative_emails = emails

                    is_valid_email_data = len(emails) > 0 and "content" in emails[0].keys() and "sender" in emails[0].keys() and "subject" in emails[0].keys()
                    if is_valid_email_data:
                        if len(emails) > 1:
                            limit_emails = emails[:5]
                            response = asyncio.run(generate_summary_emails(limit_emails))
                            save_message("assistant", f"Summary emails: {response}")
                            display_chat_message("assistant", f"Summary emails: {response}", "🤖")
                        
                        if len(emails) == 1:
                            email = emails[0]
                            category = email['category'] # get email category

                            response = asyncio.run(generate_summary_emails([email]))
                            save_message("assistant", f"Summary email:  \n {response}")
                            display_chat_message("assistant", f"Summary email:  \n {response}", "🤖")
                            
                            if category == "Meetings":
                                meeting_info = asyncio.run(get_meeting_info(email))
                                if meeting_info:
                                    display_meeting_info(meeting_info)
                                else:
                                    st.warning("No meeting information found in this email.")
                                save_message("assistant", f"Meeting info:  \n {meeting_info}")

                            if category == "Important" or category == "Follow-Up":
                                response = asyncio.run(generate_auto_reply(email))
                                save_message("assistant", f"Suggestion reply:  \n {response}")
                                display_chat_message("assistant", f"Suggestion reply:  \n {response}", "🤖")
                    pass
                case "MorningBriefFlow":
                    morning_summary = data.get("summary")
                    save_message("assistant", f"Morning summary:  \n {morning_summary}")
                    display_chat_message("assistant", f"Morning summary:  \n {morning_summary}", "🤖")
                    pass
                case "ExecutionFlow":
                    response = data.get("response")
                    save_message("assistant", f"Follow up email:  \n {response}")
                    display_chat_message("assistant", f"Follow up email:  \n {response}", "🤖")
                    pass
                case "Other":
                    pass


if __name__ == "__main__":
    main()
