"""Configuration module for TV Series Recommender."""

import os
from dotenv import load_dotenv
from pydantic import BaseSettings, Field

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings."""

    # API Configuration
    tvdb_api_url: str = Field(default="https://api4.thetvdb.com/v4", env="TVDB_API_URL")
    tvdb_api_key: str = Field(..., env="TVDB_API_KEY")
    tvdb_pin: str = Field(default=None, env="TVDB_PIN")

    # OpenAI Configuration
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
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


def validate_config():
    """Validate that all required configuration variables are set."""
    required_vars = [
        ("TVDB_API_KEY", settings.tvdb_api_key),
        ("OPENAI_API_KEY", settings.openai_api_key),
    ]

    missing_vars = [var_name for var_name, var_value in required_vars if not var_value]

    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}. "
            "Please check your .env file."
        )