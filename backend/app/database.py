from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings
import boto3
import json
import logging
import os

logger = logging.getLogger(__name__)

def get_secret_value(secret_name: str, key: str = None) -> str:
    """Get secret from AWS Secrets Manager or environment variable"""
    try:
        # Try AWS Secrets Manager first
        session = boto3.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=settings.aws_region
        )
        
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        secret = json.loads(get_secret_value_response['SecretString'])
        
        if key:
            return secret.get(key, "")
        return secret
    except Exception as e:
        logger.warning(f"Could not get secret {secret_name}: {e}")
        # Fallback to environment variable
        import os
        if key:
            return os.getenv(key, "")
        return os.getenv(secret_name.replace("/", "_").replace("-", "_").upper(), "")

# Get database URL preferring environment variable and settings; avoid network calls at import time
database_url = os.getenv("DATABASE_URL") or settings.database_url

engine = create_engine(database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
