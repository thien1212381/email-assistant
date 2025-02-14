import streamlit as st
import json
from datetime import datetime
import pytz
import re
import asyncio
from typing import Dict, List

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

async def get_assistant_response(prompt: str) -> str:
    """Get response from assistant asynchronously."""
    return await agent.handle_user_query(prompt)

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
            if len(data) == 0:
                response = "No emails found."
                save_message("assistant", response)
                display_chat_message("assistant", response, "🤖")
            else:
                df = pd.DataFrame(data)
                display_table_message("assistant", df, "🤖")

            is_valid_email_data = len(data) > 0 and "content" in data[0].keys() and "sender" in data[0].keys() and "subject" in data[0].keys()
            if is_valid_email_data:
                if len(data) > 1:
                    response = asyncio.run(generate_summary_emails(data))
                    save_message("assistant", f"Summary emails: {response}")
                    display_chat_message("assistant", f"Summary emails: {response}", "🤖")
                
                if len(data) == 1:
                    email = data[0]
                    category = asyncio.run(classify_email(email))
                    save_message("assistant", f"Classified as:  \n {category}")
                    display_chat_message("assistant", f"Classified as:  \n {category}", "🤖")

                    response = asyncio.run(generate_summary_emails([email]))
                    save_message("assistant", f"Summary email:  \n {response}")
                    display_chat_message("assistant", f"Summary email:  \n {response}", "🤖")
                    
                    if category == "Meetings":
                        meeting_info = asyncio.run(get_meeting_info(email))
                        save_message("assistant", f"Meeting info:  \n {meeting_info}")
                        display_chat_message("assistant", f"Meeting info:  \n {meeting_info}", "🤖")

                    if category == "Important" or category == "Follow-Up":
                        response = asyncio.run(generate_auto_reply(email))
                        save_message("assistant", f"Suggestion reply:  \n {response}")
                        display_chat_message("assistant", f"Suggestion reply:  \n {response}", "🤖")

if __name__ == "__main__":
    main()
