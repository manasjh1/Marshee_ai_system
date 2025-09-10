import motor.motor_asyncio
from app.config import settings
import structlog

logger = structlog.get_logger()

class Database:
    client = None
    database = None
    connected = False

db = Database()

async def connect_to_mongo():
    """Connect to MongoDB with graceful failure handling"""
    try:
        db.client = motor.motor_asyncio.AsyncIOMotorClient(
            settings.mongodb_url,
            serverSelectionTimeoutMS=5000,  # 5 second timeout
            connectTimeoutMS=5000
        )
        db.database = db.client[settings.database_name]
        
        # Test connection
        await db.client.admin.command('ping')
        db.connected = True
        logger.info("Connected to MongoDB")
        
    except Exception as e:
        logger.warning("MongoDB unavailable, continuing without it", error=str(e))
        db.connected = False
        db.client = None
        db.database = None

async def close_mongo_connection():
    """Close MongoDB connection"""
    if db.client:
        db.client.close()
        logger.info("Disconnected from MongoDB")

def get_database():
    """Get database instance - returns None if not connected"""
    if db.connected and db.database is not None:
        return db.database
    return None