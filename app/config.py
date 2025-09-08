import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    mongodb_url: str
    database_name: str = "marshee_ai"
    environment: str = "development"
    
    class Config:
        env_file = ".env"

settings = Settings()

TOTAL_STAGES = 7