"""Configuration settings for the Trimble Media Coverage Tracker."""
from pydantic_settings import BaseSettings
import os
from typing import List, Union, Dict, Any, Optional


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Trimble Media Coverage Tracker"
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    
    # Base URL for assistant APIs
    ASSISTANT_BASE_URL: str = "https://agw.construction-integration.trimble.cloud/trimbledeveloperprogram/assistants/v1"
    
    # Excel file settings
    EXCEL_FILE_PATH: str = "Trimble_Media_Coverage_Tracker.xlsx"
    

    class Config:
        case_sensitive = True
        # If .env file exists, load environment variables from it
        env_file = ".env" if os.path.isfile(".env") else None


settings = Settings() 