import os
from typing import Dict, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class EmailConfig(BaseSettings):
    """Email configuration settings."""
    
    # Provider type (gmail, outlook, etc.)
    provider: str = "gmail"
    
    # Gmail OAuth settings
    gmail_credentials_path: str = os.path.join("config", "credentials.json")
    gmail_token_path: str = os.path.join("config", "token.pickle")
    
    # Sync settings
    sync_interval_minutes: int = 5
    max_emails_per_sync: int = 50
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="EMAIL_",
        extra='allow'  # Allow extra fields from .env
    )

def get_email_config() -> EmailConfig:
    """Get email configuration."""
    return EmailConfig()
