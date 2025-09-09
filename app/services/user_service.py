# app/services/user_service.py
"""User management service"""

from datetime import datetime
from app.database import get_database
from app.models import UserData, ChatMessage
import structlog

logger = structlog.get_logger()

async def get_user(firestore_id: str) -> UserData:
    """Get or create user"""
    db = get_database()
    user_doc = await db.users.find_one({"firestore_id": firestore_id})
    
    if user_doc:
        return UserData(**user_doc)
    
    # Create new user
    new_user = UserData(firestore_id=firestore_id)
    await db.users.insert_one(new_user.model_dump())
    logger.info("Created new user", firestore_id=firestore_id)
    return new_user

async def update_user(firestore_id: str, update_data: dict):
    """Update user data"""
    db = get_database()
    update_data["updated_at"] = datetime.utcnow()
    await db.users.update_one(
        {"firestore_id": firestore_id},
        {"$set": update_data}
    )
    logger.info("Updated user", firestore_id=firestore_id)

async def save_chat(chat_message: ChatMessage):
    """Save chat message"""
    db = get_database()
    await db.chat_messages.insert_one(chat_message.model_dump())

async def complete_user_setup(firestore_id: str):
    """Mark user setup as complete"""
    await update_user(firestore_id, {
        "initial_setup_complete": True,
        "current_stage": "main_conversation"
    })