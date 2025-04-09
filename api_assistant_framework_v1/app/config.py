# app/config.py

import os
import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional # Import Optional

class Settings(BaseSettings):
    """Manages application settings using Pydantic, loading from .env."""
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore'
    )

    # --- General Project Settings ---
    PROJECT_NAME: str = "API Chat Assistant Framework"
    API_V1_STR: str = "/api/v1"

    # --- Database Configuration ---
    # Default can be overridden by DATABASE_URL in .env
    DATABASE_URL: str = "sqlite+aiosqlite:///./chat_state.db"

    # --- API Specification ---
    # Default can be overridden by API_SPEC_FILE in .env
    API_SPEC_FILE: str = "generic_api.yaml" # Default to generic spec

    # --- Target API Configuration ---
    # Default can be overridden by TARGET_API_BASE_URL in .env
    # Set a default (e.g., None or a placeholder) or make it mandatory
    TARGET_API_BASE_URL: Optional[str] = None # Make it optional or provide a default

    # --- External Service API Keys ---
    # Loaded from .env file or environment variables
    OPENAI_API_KEY: Optional[str] = None
    # Example for a custom API key
    MY_API_KEY: Optional[str] = None # Key for the target API

# Instantiate settings globally
settings = Settings()

# --- Basic Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Log loaded values (avoid logging keys directly in production)
logger.info(f"Settings loaded: PROJECT_NAME={settings.PROJECT_NAME}")
logger.info(f"Database URL: {settings.DATABASE_URL}")
logger.info(f"API Spec File: {settings.API_SPEC_FILE}")
logger.info(f"Target API Base URL: {settings.TARGET_API_BASE_URL}")
# Avoid logging keys: logger.info(f"My API Key Loaded: {'Yes' if settings.MY_API_KEY else 'No'}")

