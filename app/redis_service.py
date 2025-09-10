import redis
import json
import time
from datetime import datetime
from typing import List, Dict
from app.config import settings
import structlog

logger = structlog.get_logger()

class RedisService:
    def __init__(self):
        self.redis_client = None
        self.initialized = False
        self.SUMMARY_THRESHOLD = 10
    
    async def initialize(self):
        try:
            self.redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                decode_responses=True,
                username=settings.redis_username,
                password=settings.redis_password,
                socket_connect_timeout=30,
                socket_timeout=10,
                retry_on_timeout=True
            )
            self.redis_client.ping()
            self.initialized = True
            logger.info("Redis connected successfully")
        except Exception as e:
            logger.warning("Redis unavailable, continuing without it", error=str(e))
            self.initialized = False
    
    async def add_message(self, user_id: str, user_message: str, marshee_response: str):
        if not self.initialized:
            return
        
        try:
            message = {
                "id": f"{user_id}_{int(time.time() * 1000)}",
                "user_message": user_message[:2000],
                "marshee_response": marshee_response[:2000],
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": user_id
            }
            
            chat_key = f"chat:{user_id}"
            self.redis_client.lpush(chat_key, json.dumps(message))
            self.redis_client.expire(chat_key, 86400)
            
            message_count = self.redis_client.llen(chat_key)
            if message_count >= self.SUMMARY_THRESHOLD:
                await self.create_and_save_summary(user_id)
                
        except Exception as e:
            logger.warning("Redis operation failed", error=str(e))
    
    async def get_current_chat(self, user_id: str) -> List[Dict]:
        if not self.initialized:
            return []
        
        try:
            messages = self.redis_client.lrange(f"chat:{user_id}", 0, -1)
            chat_history = []
            for msg_str in reversed(messages):
                try:
                    chat_history.append(json.loads(msg_str))
                except json.JSONDecodeError:
                    continue
            return chat_history
        except Exception as e:
            logger.warning("Failed to get chat history", error=str(e))
            return []
    
    async def create_and_save_summary(self, user_id: str):
        if not self.initialized:
            return
        
        try:
            chat_key = f"chat:{user_id}"
            messages = self.redis_client.lrange(chat_key, 0, -1)
            
            if not messages:
                return
            
            chat_history = []
            for msg_str in reversed(messages):
                try:
                    chat_history.append(json.loads(msg_str))
                except json.JSONDecodeError:
                    continue
            
            if len(chat_history) < 5:  # Only create summary if we have enough messages
                return
                
            summary = await self._generate_summary(chat_history, user_id)
            
            # Save to Pinecone
            try:
                from app.pinecone_service import pinecone_service
                if pinecone_service.is_ready():
                    await pinecone_service.save_chat_summary_to_user_history(user_id, summary, chat_history)
                    logger.info(f"Summary created for user {user_id}")
            except Exception as e:
                logger.warning("Failed to save summary to Pinecone", error=str(e))
            
            # Clear Redis messages after summary
            self.redis_client.delete(chat_key)
            
        except Exception as e:
            logger.warning("Summary creation failed", error=str(e))
    
    async def _generate_summary(self, chat_history: List[Dict], user_id: str) -> str:
        try:
            from app.groq_service import groq_service
            
            if groq_service.initialized:
                conversation_text = ""
                for msg in chat_history:
                    conversation_text += f"User: {msg.get('user_message', '')}\nMarshee: {msg.get('marshee_response', '')}\n\n"
                
                completion = groq_service.client.chat.completions.create(
                    model=groq_service.model,
                    messages=[
                        {"role": "system", "content": "Summarize this pet care conversation focusing on key topics, health concerns, and advice given."},
                        {"role": "user", "content": f"Summarize:\n\n{conversation_text[:3000]}"}  # Limit input size
                    ],
                    temperature=0.3,
                    max_tokens=500
                )
                
                summary = completion.choices[0].message.content.strip()
                return f"Summary ({datetime.utcnow().strftime('%Y-%m-%d')}):\n{summary}\nMessages: {len(chat_history)}"
            
        except Exception as e:
            logger.warning("Groq summary failed", error=str(e))
        
        # Fallback summary
        return f"Chat summary for {user_id} - {len(chat_history)} messages exchanged on {datetime.utcnow().strftime('%Y-%m-%d')}"
    
    def get_current_message_count(self, user_id: str) -> int:
        if not self.initialized:
            return 0
        try:
            return self.redis_client.llen(f"chat:{user_id}")
        except:
            return 0
    
    def is_ready(self) -> bool:
        return self.initialized

redis_service = RedisService()