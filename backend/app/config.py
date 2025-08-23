from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./qa_system.db"
    
    # JWT
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # AWS
    aws_region: str = "us-east-1"
    aws_s3_bucket_input: str = "qa-system-input"
    aws_s3_bucket_output: str = "qa-system-output"
    
    # OpenAI
    openai_api_key: str = ""
    openai_max_retries: int = 3
    openai_backoff_base_seconds: float = 2.0
    openai_request_timeout_seconds: int = 45
    
    # Transcribe
    transcribe_max_wait_seconds: int = 900
    transcribe_poll_interval_seconds: float = 5.0
    
    # CORS
    allowed_origins: List[str] = ["http://localhost:3000"]
    
    # Demo seeding
    auto_seed_demo: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
