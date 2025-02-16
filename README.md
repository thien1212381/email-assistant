# Email Assistant

An intelligent email assistant powered by LLMs that helps you manage, categorize, and interact with your emails through natural language queries.

## Features

- **Natural Language Queries**: Ask questions about your emails in plain English
- **Email Categorization**: Automatically categorizes emails into:
  - Meetings
  - Important
  - Follow-Up
  - Spam
- **Meeting Detection**: Extracts meeting information from emails
- **Smart Summaries**: Generates concise summaries of emails and email threads
- **Auto-Reply Suggestions**: Generates context-aware reply suggestions
- **Interactive Chat Interface**: Built with Streamlit for easy interaction

## Technical Stack

- **Frontend**: Streamlit
- **Database**: SQLite with SQLAlchemy ORM
- **LLM Integration**: 
  - OpenAI GPT
  - Anthropic Claude
  - Google Gemini
- **Memory**: Conversation memory for context-aware responses

## Project Structure

```
gmail-assistant/
├── app/
│   ├── __init__.py
│   ├── agent.py           # Main email processing logic
│   ├── database.py        # Database models and operations
│   ├── llm_provider.py    # LLM integration and prompts
│   ├── meeting_detector.py # Meeting information extraction
│   ├── models.py          # Pydantic models
│   └── notification_system.py # Notification handling
├── data/
│   └── emails.db         # SQLite database
├── streamlit_app.py      # Streamlit UI
├── seed_data.py         # Sample data generation
└── requirements.txt     # Project dependencies
```

## Database Schema

### Emails Table
```sql
CREATE TABLE emails (
    id TEXT PRIMARY KEY,
    subject TEXT,
    sender TEXT,
    recipients TEXT,  -- JSON string
    content TEXT,
    timestamp DATETIME,
    category TEXT,
    is_read BOOLEAN
)
```

### Meetings Table
```sql
CREATE TABLE meetings (
    id TEXT PRIMARY KEY,
    email_id TEXT,
    title TEXT,
    datetime DATETIME,
    location TEXT,
    attendees TEXT,  -- JSON string
    description TEXT,
    FOREIGN KEY(email_id) REFERENCES emails(id)
)
```

### Messages Table
```sql
CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    role TEXT,
    content TEXT,
    timestamp DATETIME
)
```

## Gmail Integration

The application integrates with Gmail using OAuth2 authentication to access and manage your emails. Here's how it works:

### Authentication Setup

1. Create a Google Cloud Project:
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project or select an existing one
   - Enable the Gmail API for your project
   - Configure the OAuth consent screen
   - Create OAuth 2.0 credentials (Desktop application)
   - Download the credentials and save as `config/credentials.json`

2. Required Scopes:
   ```
   https://www.googleapis.com/auth/gmail.readonly
   https://www.googleapis.com/auth/gmail.send
   https://www.googleapis.com/auth/gmail.modify
   https://www.googleapis.com/auth/gmail.labels
   ```

### Email Processor

The Email Processor is responsible for:

1. **Email Syncing**:
   - Periodically fetches new emails from Gmail
   - Configurable sync interval and batch size
   - Focuses on unread emails by default

2. **Email Processing**:
   - Uses LLM to classify emails into categories:
     - MEETING: Emails about meetings and scheduling
     - IMPORTANT: High-priority emails
     - FOLLOW_UP: Emails needing response
     - SPAM: Unwanted emails
     - UPDATES: System notifications
     - SOCIAL: Social network communications
     - PROMOTIONS: Marketing content
   - Adds Gmail labels based on categories (prefixed with "G.")
   - Extracts meeting information when relevant
   - Stores processed emails in local database

3. **Meeting Detection**:
   - Automatically detects meeting invites
   - Extracts key information:
     - Title
     - Date and time
     - Duration
     - Location/link
     - Attendees
   - Schedules reminders for meetings
   - Checks for scheduling conflicts

### Usage Example

```python
from app.gmail_provider import GmailProvider
from app.database import Database
from app.agent import EmailAgent
from app.llm_provider import get_llm_provider
from app.email_processor import EmailProcessor

async def main():
    # Initialize components
    db = Database()
    llm = get_llm_provider("openai")
    agent = EmailAgent(db, llm)
    
    # Initialize Gmail provider
    gmail = GmailProvider(
        credentials_path="config/credentials.json",
        token_path="config/token.pickle"
    )
    
    # Create email processor
    processor = EmailProcessor(
        email_provider=gmail,
        database=db,
        agent=agent,
        sync_interval=300,  # 5 minutes
        max_emails_per_sync=15
    )
    
    # Start processing
    await processor.start()
```

### Configuration

The email processor can be configured through environment variables:

```env
EMAIL_PROVIDER=gmail
EMAIL_SYNC_INTERVAL_MINUTES=5
EMAIL_MAX_EMAILS_PER_SYNC=15
OPENAI_API_KEY=your_api_key
```

### Gmail Labels

The processor automatically creates and manages Gmail labels:

- G.MEETING
- G.IMPORTANT
- G.FOLLOW_UP
- G.SPAM
- G.UPDATES
- G.SOCIAL
- G.PROMOTIONS

The "G." prefix is used to avoid conflicts with Gmail's built-in labels.

### Database Integration

Processed emails are stored in SQLite with the following schema:

```sql
CREATE TABLE emails (
    id TEXT PRIMARY KEY,
    subject TEXT,
    sender TEXT,
    recipients TEXT,  -- JSON string
    content TEXT,
    timestamp DATETIME,
    thread_id TEXT,
    category TEXT,
    is_read BOOLEAN,
    labels TEXT,      -- JSON string
    provider_type TEXT,
    last_synced DATETIME
)
```

This allows for:
- Local email search and filtering
- Offline access to email content
- Quick retrieval of categorized emails
- Meeting information tracking

## Setup and Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/gmail-assistant.git
cd gmail-assistant
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
# Create .env file
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GOOGLE_API_KEY=your_google_key
```

5. Initialize the database with sample data:
```bash
python seed_data.py
```

6. Run the application:
```bash
streamlit run streamlit_app.py
```

## Usage Examples

Here are some example queries you can try:

- "Show me all unread emails"
- "What meetings do I have today?"
- "Show me important emails from last week"
- "Find emails that need follow-up"
- "Show me emails from [sender@example.com]"
- "What's in my spam folder?"

## Features in Detail

### Natural Language Query Processing
The assistant converts natural language queries into SQL queries using LLM. It maintains conversation context to provide more relevant responses.

### Email Categorization
Emails are automatically categorized using LLM analysis of the subject and content. Categories include:
- Meetings: Emails containing meeting invitations or updates
- Important: High-priority communications
- Follow-Up: Emails requiring action or response
- Spam: Low-priority or marketing emails

### Meeting Detection
The system automatically extracts meeting details including:
- Date and time
- Location (physical or virtual)
- Attendees
- Meeting description/agenda

### Smart Summaries
For each email or thread, the system can generate:
- Concise summaries
- Key points
- Action items
- Relevant context from conversation history

## TODO

### 1. Morning Brief Enhancement
- [ ] Implement dedicated morning brief functionality on chat UI
  - [ ] Daily email summary categorized by priority
  - [ ] Today's meeting schedule
  - [ ] Important follow-ups and pending responses
  - [ ] Key metrics and statistics (email volume, response times)
  - [ ] Customizable brief templates

### 2. Meeting Management Improvements on chat UI and notifications
- [ ] Smart meeting reminders with configurable timing
- [ ] Meeting conflict detection and resolution
- [ ] Suggest alternative meeting times based on calendar availability

### 3. Video Demo

### 4. LLM Context and Flow Improvements
- [ ] Enhanced conversation context management
  - [ ] Multi-turn conversation support
  - [ ] Context-aware response generation
  - [ ] Action chaining (e.g., classify → summarize → schedule)
  - [ ] User preference learning
  - [ ] Conversation history integration
  - [ ] Improved prompt engineering for better context retention

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.