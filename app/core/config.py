"""Configuration settings for the Trimble Media Coverage Tracker."""
from pydantic_settings import BaseSettings
import os
from typing import List


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Trimble Media Coverage Tracker"
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    
    # Base URL for assistant APIs
    ASSISTANT_BASE_URL: str = "https://api.assistant.trimble.cloud/ui/trimbledeveloperprogram/assistants/v1"
    
    # Excel file settings
    EXCEL_FILE_PATH: str = "Trimble_Media_Coverage_Tracker.xlsx"
    
    # Trimble Identity authentication settings
    TRIMBLE_CLIENT_ID: str = "685cf9be-a21b-489b-bff8-0d4e862ee3c9"
    TRIMBLE_CLIENT_SECRET: str = "986e4d10490c43dda22ffa97f33a0565"
    

    class Config:
        case_sensitive = True
        # If .env file exists, load environment variables from it
        env_file = ".env" if os.path.isfile(".env") else None


settings = Settings() 