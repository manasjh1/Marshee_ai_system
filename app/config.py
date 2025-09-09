# app/config.py
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    mongodb_url: str
    database_name: str = "marshee_ai"
    environment: str = "development"
    
    # Pinecone settings
    pinecone_api_key: str = ""
    pinecone_index_name: str = "marshee-ai"
    
    # OpenAI settings
    openai_api_key: str = ""
    
    class Config:
        env_file = ".env"

settings = Settings()

TOTAL_STAGES = 7