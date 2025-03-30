"""Configuration module for TV Series Recommender."""

import os
from dotenv import load_dotenv
from pydantic import BaseSettings, Field
import sys

# Load environment variables from .env file - only in development
if os.getenv("VERCEL") != "1":
    load_dotenv()
    print("Loaded environment variables from .env file")
else:
    print("Running in Vercel environment, skipping .env loading")


class Settings(BaseSettings):
    """Application settings."""

    # API Configuration
    tvdb_api_url: str = Field(default="https://api4.thetvdb.com/v4", env="TVDB_API_URL")
    # Make these optional with default=None, then check them at runtime
    tvdb_api_key: str = Field(default=None, env="TVDB_API_KEY")
    tvdb_pin: str = Field(default=None, env="TVDB_PIN")

    # OpenAI Configuration
    openai_api_key: str = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-3.5-turbo", env="OPENAI_MODEL")

    # Application Configuration
    max_conversation_history: int = Field(default=10, env="MAX_CONVERSATION_HISTORY")
    default_results_limit: int = Field(default=5, env="DEFAULT_RESULTS_LIMIT")

    # FastAPI Configuration
    app_name: str = Field(default="TV Series Recommender", env="APP_NAME")
    app_description: str = Field(
        default="A chatbot that helps users discover TV series based on their preferences using the TVDB API.",
        env="APP_DESCRIPTION"
    )

    # Debug mode
    debug: bool = Field(default=False, env="DEBUG")

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"


# Create settings instance
settings = Settings()


# Print environment variables for debugging
def log_environment_info():
    """Log environment information for debugging."""
    print(f"PYTHONPATH: {os.environ.get('PYTHONPATH')}")
    print(f"Current directory: {os.getcwd()}")
    print(f"Directory contents: {os.listdir('.')}")
    print(f"TVDB_API_KEY set: {'Yes' if os.environ.get('TVDB_API_KEY') else 'No'}")
    print(f"OPENAI_API_KEY set: {'Yes' if os.environ.get('OPENAI_API_KEY') else 'No'}")
    print(f"Available environment variables: {list(os.environ.keys())}")


# Don't validate at import time, do it when actually needed
def validate_config():
    """Validate that all required configuration variables are set."""
    missing_vars = []

    # Check TVDB API key
    if not settings.tvdb_api_key:
        missing_vars.append("TVDB_API_KEY")

    # Check OpenAI API key
    if not settings.openai_api_key:
        missing_vars.append("OPENAI_API_KEY")

    if missing_vars:
        error_message = f"Missing required environment variables: {', '.join(missing_vars)}."
        print(f"ERROR: {error_message}", file=sys.stderr)
        # Don't raise an exception, just return False
        return False, error_message

    return True, "Configuration is valid"