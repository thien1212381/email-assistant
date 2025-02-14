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

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.