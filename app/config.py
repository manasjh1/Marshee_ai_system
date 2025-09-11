import os
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from dotenv import load_dotenv

# Force load .env file
load_dotenv()

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra='allow')
    # MongoDB settings
    mongodb_url: str
    database_name: str = "marshee_ai"
    environment: str = "development"
    
    # Pinecone settings - with fallback to env vars
    pinecone_api_key: str = os.getenv("PINECONE_API_KEY", "")
    pinecone_index_name: str = "marshee-ai"
    
    # Redis settings - with fallback to env vars
    redis_host: str = "redis-15929.c330.asia-south1-1.gce.redis.redis-cloud.com"
    redis_port: int = 15929
    redis_username: str = "default"
    redis_password: str = os.getenv("REDIS_PASSWORD", "")
    
    # Groq settings - with fallback to env vars
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")

settings = Settings()
TOTAL_STAGES = 7