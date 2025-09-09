# app/redis_service.py - Production-ready Redis service
"""Production-ready Redis service for chat management"""

import redis
import json
import time
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from app.config import settings
import structlog

logger = structlog.get_logger()

class RedisService:
    def __init__(self):
        self.redis_client = None
        self.connection_pool = None
        self.initialized = False
    
    async def initialize(self):
        """Initialize Redis with production settings and retry logic"""
        for attempt in range(3):  # 3 retry attempts
            try:
                # Create connection pool for better performance
                self.connection_pool = redis.ConnectionPool(
                    host=settings.redis_host,
                    port=settings.redis_port,
                    username=settings.redis_username,
                    password=settings.redis_password,
                    db=0,
                    max_connections=20,
                    socket_timeout=30,
                    socket_connect_timeout=30,
                    retry_on_timeout=True,
                    health_check_interval=30,
                    socket_keepalive=True,
                    decode_responses=True
                )
                
                # Create Redis client with connection pool
                self.redis_client = redis.Redis(connection_pool=self.connection_pool)
                
                # Test connection
                result = self.redis_client.ping()
                if not result:
                    raise redis.ConnectionError("Redis ping failed")
                
                self.initialized = True
                logger.info("Redis service initialized successfully")
                return
                
            except Exception as e:
                logger.warning(f"Redis connection attempt {attempt + 1} failed: {e}")
                if attempt == 2:  # Last attempt
                    logger.error("All Redis connection attempts failed")
                    self.initialized = False
                    return
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    def get_chat_key(self, user_id: str) -> str:
        """Get Redis key for user's chat messages"""
        return f"chat:{user_id}"
    
    def get_last_activity_key(self, user_id: str) -> str:
        """Get Redis key for user's last activity timestamp"""
        return f"activity:{user_id}"
    
    async def add_message(self, user_id: str, user_message: str, marshee_response: str):
        """Add message to Redis with error handling"""
        if not self.initialized or not self.redis_client:
            logger.warning("Redis not available - skipping message storage")
            return
        
        try:
            # Validate inputs
            if not user_id or len(user_id) < 3:
                logger.error("Invalid user_id provided")
                return
            
            if not user_message or not marshee_response:
                logger.error("Empty message provided")
                return
            
            chat_key = self.get_chat_key(user_id)
            activity_key = self.get_last_activity_key(user_id)
            
            # Create message object
            message = {
                "user_message": user_message[:2000],  # Limit message length
                "marshee_response": marshee_response[:2000],
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": user_id
            }
            
            # Use pipeline for atomic operations
            pipe = self.redis_client.pipeline()
            pipe.lpush(chat_key, json.dumps(message))
            pipe.set(activity_key, time.time())
            pipe.expire(chat_key, 86400)  # 24 hours TTL
            pipe.expire(activity_key, 86400)
            pipe.execute()
            
            # Check if we need to create summary
            message_count = self.redis_client.llen(chat_key)
            
            if message_count >= 10:  # Configurable threshold
                await self.create_and_save_summary(user_id)
                
            logger.info(f"Added message for user {user_id}, total messages: {message_count}")
            
        except redis.RedisError as e:
            logger.error(f"Redis error adding message for user {user_id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error adding message for user {user_id}: {e}")
    
    async def check_inactive_users(self):
        """Check for users inactive for more than 3 minutes and create summaries"""
        if not self.initialized or not self.redis_client:
            return
        
        try:
            # Get all activity keys
            activity_keys = self.redis_client.keys("activity:*")
            if not activity_keys:
                return
            
            current_time = time.time()
            inactive_threshold = 180  # 3 minutes in seconds
            
            for activity_key in activity_keys:
                try:
                    last_activity = float(self.redis_client.get(activity_key) or 0)
                    
                    # Check if inactive for more than 3 minutes
                    if current_time - last_activity > inactive_threshold:
                        user_id = activity_key.split(":", 1)[1]
                        chat_key = self.get_chat_key(user_id)
                        
                        # Check if user has messages
                        message_count = self.redis_client.llen(chat_key)
                        if message_count > 0:
                            await self.create_and_save_summary(user_id)
                            logger.info(f"Created summary for inactive user {user_id}")
                            
                except (ValueError, IndexError, redis.RedisError) as e:
                    logger.warning(f"Error checking activity for key {activity_key}: {e}")
                    continue
                        
        except Exception as e:
            logger.error(f"Failed to check inactive users: {e}")
    
    async def create_and_save_summary(self, user_id: str):
        """Create summary of chat messages and save to Pinecone"""
        if not self.initialized or not self.redis_client:
            return
        
        try:
            chat_key = self.get_chat_key(user_id)
            
            # Get all messages
            messages = self.redis_client.lrange(chat_key, 0, -1)
            
            if not messages:
                return
            
            # Parse messages
            chat_history = []
            for msg_str in reversed(messages):  # Reverse to get chronological order
                try:
                    msg = json.loads(msg_str)
                    chat_history.append(msg)
                except json.JSONDecodeError:
                    continue
            
            if not chat_history:
                return
            
            # Create summary
            summary = await self.generate_summary(chat_history, user_id)
            
            # Save to Pinecone
            from app.pinecone_service import pinecone_service
            if pinecone_service.is_ready():
                await pinecone_service.save_chat_summary(user_id, summary, chat_history)
            
            # Clear Redis messages after summary
            pipe = self.redis_client.pipeline()
            pipe.delete(chat_key)
            pipe.delete(self.get_last_activity_key(user_id))
            pipe.execute()
            
            logger.info(f"Created and saved summary for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to create summary for user {user_id}: {e}")
    
    async def generate_summary(self, chat_history: List[Dict], user_id: str) -> str:
        """Generate summary of chat conversation"""
        try:
            # Extract key information from conversation
            topics = []
            questions = []
            concerns = []
            
            for msg in chat_history:
                user_msg = msg.get('user_message', '').lower()
                
                # Identify health concerns
                if any(word in user_msg for word in ['sick', 'ill', 'problem', 'worried', 'help', 'vet']):
                    concerns.append(msg.get('user_message', ''))
                
                # Identify questions
                if '?' in user_msg:
                    questions.append(msg.get('user_message', ''))
                
                # Identify topics
                if any(word in user_msg for word in ['food', 'eat', 'groom', 'bath', 'play', 'exercise']):
                    topics.append(user_msg)
            
            # Create structured summary
            summary_parts = [f"Chat summary for user {user_id} on {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"]
            
            if concerns:
                summary_parts.append(f"Health concerns discussed: {'; '.join(concerns[:3])}")
            
            if questions:
                summary_parts.append(f"Questions asked: {'; '.join(questions[:3])}")
            
            if topics:
                summary_parts.append(f"Topics covered: {'; '.join(set(topics[:5]))}")
            
            summary_parts.append(f"Total messages: {len(chat_history)}")
            
            return "\n".join(summary_parts)
            
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return f"Chat summary for user {user_id} - {len(chat_history)} messages exchanged"
    
    def get_current_message_count(self, user_id: str) -> int:
        """Get current message count for user"""
        if not self.initialized or not self.redis_client:
            return 0
        
        try:
            if not user_id or len(user_id) < 3:
                return 0
            
            chat_key = self.get_chat_key(user_id)
            return self.redis_client.llen(chat_key)
        except Exception as e:
            logger.error(f"Failed to get message count: {e}")
            return 0
    
    async def close(self):
        """Close Redis connections"""
        if self.connection_pool:
            self.connection_pool.disconnect()
        self.initialized = False
        logger.info("Redis service closed")
    
    def is_ready(self) -> bool:
        """Check if Redis service is ready"""
        return self.initialized and self.redis_client is not None

# Global instance
redis_service = RedisService()