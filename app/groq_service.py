# app/groq_service.py
import os
from groq import Groq
from typing import Dict, List
import structlog
from app.prompts import prompts

logger = structlog.get_logger()

class GroqService:
    def __init__(self):
        self.client = None
        self.initialized = False
        self.model = "openai/gpt-oss-120b"
    
    async def initialize(self):
        try:
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                return
            
            self.client = Groq(api_key=api_key)
            self.initialized = True
        except Exception as e:
            logger.error("Groq init failed", error=str(e))
            self.initialized = False
    
    async def generate_response_with_full_context(
        self,
        user_message: str,
        user_data: Dict,
        redis_chat: List[Dict],
        vector_context: Dict
    ) -> str:
        
        if not self.initialized:
            return self._fallback_response(user_message, user_data)
        
        try:
            # Use the new prompts class to build the system prompt
            system_prompt = prompts.build_system_prompt(user_data, redis_chat, vector_context)
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add recent chat (last 6 messages)
            recent_chat = redis_chat[-6:] if len(redis_chat) > 6 else redis_chat
            for chat_msg in recent_chat[:-1]:
                messages.append({"role": "user", "content": chat_msg.get("user_message", "")})
                messages.append({"role": "assistant", "content": chat_msg.get("marshee_response", "")})
            
            messages.append({"role": "user", "content": user_message})
            
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=200,
                stream=False
            )
            
            return completion.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error("Groq generation failed", error=str(e))
            return self._fallback_response(user_message, user_data)
    
    def _fallback_response(self, user_message: str, user_data: Dict) -> str:
        pet_name = user_data.get('pet_name', 'your pet')
        user_name = user_data.get('user_name', 'there')
        
        query_lower = user_message.lower()
        
        if any(word in query_lower for word in ["sick", "health", "vet"]):
            return f"Hi {user_name}! For {pet_name}'s health concerns, please consult your veterinarian. What symptoms are you noticing?"
        elif any(word in query_lower for word in ["food", "nutrition"]):
            return f"Good nutrition is important for {pet_name}! What specific question do you have about {pet_name}'s diet?"
        elif any(word in query_lower for word in ["groom", "bath"]):
            return f"Regular grooming keeps {pet_name} healthy! What grooming help do you need?"
        else:
            return f"Hi {user_name}! I'm here to help with {pet_name}. What would you like to know?"

groq_service = GroqService()