import os
import base64
from typing import List, Dict, Optional
from datetime import datetime
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pickle

from .email_provider import EmailProvider, EmailMessage

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.labels'
]

class GmailProvider(EmailProvider):
    def __init__(self, credentials_path: str = "credentials.json", token_path: str = "token.pickle"):
        """Initialize Gmail provider with OAuth2 credentials."""
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.creds = None
        self.service = None
    
    async def authenticate(self) -> bool:
        """Authenticate using OAuth2."""
        try:
            if os.path.exists(self.token_path):
                with open(self.token_path, 'rb') as token:
                    self.creds = pickle.load(token)
            
            # If credentials are invalid or don't exist, let's get new ones
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES)
                    # Use a fixed port to avoid port conflicts
                    self.creds = flow.run_local_server(port=53011)
                
                # Save the credentials for future use
                with open(self.token_path, 'wb') as token:
                    pickle.dump(self.creds, token)
            
            self.service = build('gmail', 'v1', credentials=self.creds)
            return True
        except Exception as e:
            print(f"Authentication failed: {str(e)}")
            return False
    
    def _parse_message(self, message: Dict) -> EmailMessage:
        """Parse Gmail message into EmailMessage format."""
        # Get the message details
        msg = self.service.users().messages().get(
            userId='me', id=message['id'], format='full'
        ).execute()
        
        headers = msg['payload']['headers']
        subject = next(
            (header['value'] for header in headers if header['name'].lower() == 'subject'),
            '(No Subject)'
        )
        sender = next(
            (header['value'] for header in headers if header['name'].lower() == 'from'),
            'Unknown'
        )
        to = next(
            (header['value'] for header in headers if header['name'].lower() == 'to'),
            ''
        ).split(',')
        
        # Get message body
        if 'parts' in msg['payload']:
            parts = msg['payload']['parts']
            content = ""
            for part in parts:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    if data:
                        content += base64.urlsafe_b64decode(data).decode()
        else:
            data = msg['payload']['body'].get('data', '')
            content = base64.urlsafe_b64decode(data).decode() if data else ''
        
        # Convert timestamp
        timestamp = datetime.fromtimestamp(int(msg['internalDate']) / 1000)
        
        return EmailMessage(
            id=msg['id'],
            subject=subject,
            sender=sender,
            recipients=to,
            content=content,
            timestamp=timestamp,
            thread_id=msg['threadId'],
            labels=msg.get('labelIds', [])
        )
    
    async def fetch_emails(self, 
                          max_results: int = 10,
                          query: str = None,
                          include_spam: bool = False) -> List[EmailMessage]:
        """Fetch emails from Gmail."""
        try:
            # Build the query
            q = []
            if query:
                q.append(query)
            if not include_spam:
                q.append('in:inbox')
            
            # Get messages
            results = self.service.users().messages().list(
                userId='me',
                maxResults=max_results,
                q=' '.join(q)
            ).execute()
            
            messages = results.get('messages', [])
            return [self._parse_message(msg) for msg in messages]
            
        except HttpError as error:
            print(f'An error occurred: {error}')
            return []
    
    async def mark_as_read(self, message_id: str) -> bool:
        """Mark an email as read in Gmail."""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            return True
        except HttpError:
            return False
    
    async def mark_as_unread(self, message_id: str) -> bool:
        """Mark an email as unread in Gmail."""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': ['UNREAD']}
            ).execute()
            return True
        except HttpError:
            return False
    
    async def add_label(self, message_id: str, label: str) -> bool:
        """Add a label to an email in Gmail."""
        try:
            # First, check if label exists, if not create it
            try:
                label_obj = self.service.users().labels().create(
                    userId='me',
                    body={'name': label}
                ).execute()
            except HttpError:
                # Label might already exist
                labels = self.service.users().labels().list(userId='me').execute()
                print(labels)
                label_obj = next(
                    (l for l in labels['labels'] if l['name'].lower() == label.lower()),
                    None
                )
            
            print(label_obj)
            if label_obj:
                self.service.users().messages().modify(
                    userId='me',
                    id=message_id,
                    body={'addLabelIds': [label_obj['id']]}
                ).execute()
                return True
            return False
        except HttpError:
            return False
    
    async def remove_label(self, message_id: str, label: str) -> bool:
        """Remove a label from an email in Gmail."""
        try:
            # Find label ID
            labels = self.service.users().labels().list(userId='me').execute()
            label_obj = next(
                (l for l in labels['labels'] if l['name'] == label),
                None
            )
            
            if label_obj:
                self.service.users().messages().modify(
                    userId='me',
                    id=message_id,
                    body={'removeLabelIds': [label_obj['id']]}
                ).execute()
                return True
            return False
        except HttpError:
            return False
    
    async def send_email(self, 
                        to: List[str],
                        subject: str,
                        content: str,
                        cc: List[str] = None,
                        bcc: List[str] = None,
                        attachments: List[Dict] = None) -> bool:
        """Send an email using Gmail."""
        try:
            message = MIMEMultipart()
            message['to'] = ','.join(to)
            message['subject'] = subject
            
            if cc:
                message['cc'] = ','.join(cc)
            if bcc:
                message['bcc'] = ','.join(bcc)
            
            msg = MIMEText(content)
            message.attach(msg)
            
            # TODO: Handle attachments
            
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            self.service.users().messages().send(
                userId='me',
                body={'raw': raw}
            ).execute()
            return True
        except HttpError:
            return False
    
    async def get_thread(self, thread_id: str) -> List[EmailMessage]:
        """Get all messages in a thread from Gmail."""
        try:
            thread = self.service.users().threads().get(
                userId='me',
                id=thread_id
            ).execute()
            
            return [self._parse_message(msg) for msg in thread['messages']]
        except HttpError:
            return []
