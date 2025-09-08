import motor.motor_asyncio
from app.config import settings
import structlog

logger = structlog.get_logger()

class Database:
    client = None
    database = None

db = Database()

async def connect_to_mongo():
    """Connect to MongoDB"""
    try:
        db.client = motor.motor_asyncio.AsyncIOMotorClient(settings.mongodb_url)
        db.database = db.client[settings.database_name]
        await db.client.admin.command('ping')
        logger.info("Connected to MongoDB")
    except Exception as e:
        logger.error("Failed to connect to MongoDB", error=str(e))
        raise

async def close_mongo_connection():
    """Close MongoDB connection"""
    if db.client:
        db.client.close()
        logger.info("Disconnected from MongoDB")

def get_database():
    """Get database instance"""
    return db.database