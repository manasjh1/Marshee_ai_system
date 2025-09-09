import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    mongodb_url: str
    database_name: str = "marshee_ai"
    environment: str = "development"
    
    # Pinecone settings
    pinecone_api_key: str = ""
    pinecone_index_name: str = "marshee-ai"
    
    # Redis Cloud settings
    redis_host: str = "redis-15929.c330.asia-south1-1.gce.redis.redis-cloud.com"
    redis_port: int = 15929
    redis_username: str = "default"
    redis_password: str = ""  # Your Redis password
    redis_url: str = ""  # Will be constructed from above or used directly
    
    class Config:
        env_file = ".env"

settings = Settings()

TOTAL_STAGES = 7