"""
Configuration settings for EnvAgent.
Loads environment variables and API keys.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Configuration settings for the EnvAgent application."""

    # Maximum number of retry attempts for fixing conda environment errors
    MAX_RETRIES: int = 5

    def __init__(self):
        """Initialize settings by loading from environment variables."""
        self.openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")

        if not self.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY not found in environment variables. "
                "Please create a .env file with your API key. "
                "See .env.example for reference."
            )

    @property
    def api_key(self) -> str:
        """Get the OpenAI API key."""
        if not self.openai_api_key:
            raise ValueError("OpenAI API key is not configured")
        return self.openai_api_key


# Global settings instance
settings = Settings()
