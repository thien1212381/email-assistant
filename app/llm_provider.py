from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import os
import json
import uuid
from dotenv import load_dotenv
from datetime import datetime

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain.chains.conversation.memory import ConversationSummaryMemory
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
import re

load_dotenv()

class LLMProvider(ABC):
    def __init__(self):
        self.memory = ConversationBufferMemory()
        self.llm = self._init_llm()
        self.conversation = ConversationChain(
            llm=self.llm,
            memory=self.memory,
            verbose=True
        )
        
    @abstractmethod
    def _init_llm(self) -> BaseChatModel:
        pass
        
    async def classify_prompt(self, prompt: str) -> str:
        messages = [
            SystemMessage(content="""You are an AI assistant that classifies user queries into different categories. 
Categories:
1. SqlQueryFlow - If the user is asking for data retrieval emails in natural language (e.g., retrieving emails, meetings).
2. ExecutionFlow - If the user wants to process, analyze, summarize, categorize, or take action on follow-up emails or meetings.
3. MorningBriefFlow - If the query contains some words like: "Morning Brief", "Daily Brief", "Morning Summary", "Daily Summary", or "Daily Action Items".
4. Other - If the query does not fit into the above categories.
"""),
                HumanMessage(content=f"""
Classify the following query: {prompt}
Response: The best flow category is:""")
            ]
        response = await self.llm.ainvoke(messages)
        return response.content.strip()
        
    async def classify_email(self, subject: str, content: str) -> str:
        messages = [
            SystemMessage(content="""You are an email classifier. Classify the email into one of these categories:
            - Meetings
            - Important
            - Follow-Up
            - Spam"""),
            HumanMessage(content=f"""Subject: {subject}
Content: {content}

Category:""")
        ]
        
        response = await self.llm.ainvoke(messages)
        return response.content.strip()
        
    async def summarize_email(self, subject: str, content: str) -> str:
        messages = [
            SystemMessage(content="You are an email summarizer. Provide concise summaries of emails."),
            HumanMessage(content=f"""Summarize the following email:
            
Subject: {subject}
Content: {content}""")
        ]
        
        response = await self.llm.ainvoke(messages)
        return response.content.strip()
        
    async def extract_meeting_info(self, subject: str, content: str) -> Optional[Dict]:
        messages = [
            SystemMessage(content="""Extract meeting information from the email and format as JSON with these fields:
            - title: meeting title
            - datetime: ISO format datetime
            - location: meeting location (optional)
            - attendees: list of attendee email addresses
            - description: meeting description/agenda (optional)
            
            Return null if no meeting information is found."""),
            HumanMessage(content=f"""Subject: {subject}
Content: {content}

JSON:""")
        ]
        
        response = await self.llm.ainvoke(messages)
        
        try:
            json_str = response.content.strip()
            print(json_str)
            if json_str.__contains__('```json'):
                matches = re.findall(r'```json\n(.*?)```', json_str, re.DOTALL)
                if matches:
                    json_block = matches[0].strip()
                    return json.loads(json_block)
            return None
        except:
            return None

    async def generate_reply(self, email_thread: List[Dict]) -> str:
        thread_content = "\n\n".join([
            f"From: {email['sender']}\nSubject: {email['subject'][:50]}\nContent: {email['content'][:50]}"
            for email in email_thread
        ])
        
        messages = [
            SystemMessage(content="Generate a professional reply to the email thread."),
            HumanMessage(content=thread_content)
        ]
        
        response = await self.llm.ainvoke(messages)
        return response.content.strip()

    async def generate_daily_summary(self, emails: List[Dict]) -> dict:
        """Generate a comprehensive summary of multiple emails."""
        email_summaries = "\n\n".join([
            f"Email {i+1}:\nFrom: {email['sender']}\nSubject: {email['subject']}\nContent: {email['content']}\nCategory: {email['category']}"
            for i, email in enumerate(emails)
        ])
        
        messages = [
            SystemMessage(content="""Generate a daily summary report in JSON format with the following structure:
            {
                "overview": "Brief overview of email activity",
                "important_items": ["List", "of", "critical items", "requiring attention"],
                "action_items": ["Consolidated", "list of", "actions needed"],
                "deadlines": ["List of", "upcoming deadlines"],
                "priorities": ["Suggested", "priority order", "for handling tasks"]
            }"""),
            HumanMessage(content=f"Here are today's important and follow-up emails:\n\n{email_summaries}")
        ]
        
        response = await self.llm.ainvoke(messages)
        try:
            json_str = response.content.strip()
            if json_str.startswith('```json'):
                json_str = json_str[7:-3]
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {
                "overview": "Failed to parse daily summary",
                "important_items": ["No items to display"],
                "action_items": [],
                "deadlines": [],
                "priorities": []
            }

    async def handle_user_query(self, prompt: str) -> str:
         # Generate a prompt to convert natural language to SQL
        system_prompt = f"Convert the following natural language query into a SQLite query.\n\nTable emails has schemas:\n"
        
        columns = [
            { "name": "id", "type": "String" },
            { "name": "subject", "type": "String" },
            { "name": "sender", "type": "String" },
            { "name": "recipients", "type": "String" },
            { "name": "content", "type": "String" },
            { "name": "timestamp", "type": "DateTime" },
            { "name": "category", "type": "Enum('Meetings','Important','Follow-Up','Spam')" },
            { "name": "is_read", "type": "Boolean" },
        ]
        
        system_prompt += '\n'.join([f"{col['name']} {col['type']}" for col in columns])

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"User Query: {prompt}")
        ]

        response = await self.llm.ainvoke(messages)
        content = response.content.strip()
        if content.__contains__('```sql'):
            matches = re.findall(r'```sql\n(.*?)```', content, re.DOTALL)
            if matches:
                sql_block = matches[0].strip()
                return sql_block
        return ""
        
    async def generate_response_follow_up_email(self, prompt: str, email_data: List[Dict]) -> str:
        email_summaries = "\n\n".join([
            f"Email {i+1}:\nFrom: {email['sender']}\nSubject: {email['subject']}\nContent: {email['content']}\nCategory: {email['category']}"
            for i, email in enumerate(email_data)
        ])

        messages = [
            SystemMessage(content="You are an email assistant. Help users with these email-related queries."),
            HumanMessage(content=f"Email Data: \n\n{email_summaries}. User Prompt: {prompt}")
        ]

        response = await self.llm.ainvoke(messages)
        return response.content.strip()

    async def generate_response(self, prompt: str) -> str:
        messages = [
            SystemMessage(content="You are an email assistant. Help users with their email-related queries."),
            HumanMessage(content=prompt)
        ]
        response = await self.llm.ainvoke(messages)
        return response.content.strip()

    async def save_context(self, input: str, output: str):
        self.memory.save_context({ "input": input}, { "output": output })

class OpenAIProvider(LLMProvider):
    def _init_llm(self) -> BaseChatModel:
        return ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            api_key=os.getenv("OPENAI_API_KEY")
        )

class AnthropicProvider(LLMProvider):
    def _init_llm(self) -> BaseChatModel:
        return ChatAnthropic(
            model="claude-3-opus-20240229",
            temperature=0.7,
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )

class GeminiProvider(LLMProvider):
    def _init_llm(self) -> BaseChatModel:
        return ChatGoogleGenerativeAI(
            model="gemini-pro",
            temperature=0.7,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )

def get_llm_provider(provider_name: str) -> LLMProvider:
    providers = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "gemini": GeminiProvider
    }
    
    if provider_name not in providers:
        raise ValueError(f"Unsupported LLM provider: {provider_name}")
        
    return providers[provider_name]()
