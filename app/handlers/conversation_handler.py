# app/handlers/conversation_handler.py - Updated with Redis integration
"""Handle main conversation with Redis chat management and Pinecone context"""

from app.models import APIRequest, APIResponse, UserData, ChatMessage
from app.services import user_service
from app.pinecone_service import pinecone_service
from app.redis_service import redis_service
import structlog

logger = structlog.get_logger()

async def handle_conversation(request: APIRequest, user: UserData) -> APIResponse:
    """Handle main conversation with Redis and Pinecone integration"""
    
    if request.user_message:
        return await process_user_message(request, user)
    else:
        return await welcome_back_user(user)

async def process_user_message(request: APIRequest, user: UserData) -> APIResponse:
    """Process user message with Redis tracking and Pinecone context"""
    
    try:
        # Try to get context from Pinecone
        context = await pinecone_service.get_context(request.firestore_id, request.user_message)
    except Exception as e:
        logger.warning("Pinecone context unavailable", error=str(e))
        context = {}
    
    # Build response (works with or without context)
    marshee_response = await build_response(request.user_message, user, context)
    
    # Add message to Redis for tracking and potential summary
    try:
        await redis_service.add_message(
            user_id=request.firestore_id,
            user_message=request.user_message,
            marshee_response=marshee_response
        )
        
        # Get current message count for display
        message_count = redis_service.get_current_message_count(request.firestore_id)
        logger.info(f"User {request.firestore_id} has {message_count} messages in current session")
        
    except Exception as e:
        logger.warning(f"Redis tracking failed: {e}")
    
    # Save chat to MongoDB (for permanent record)
    await user_service.save_chat(ChatMessage(
        firestore_id=request.firestore_id,
        stage_id="main_conversation",
        user_message=request.user_message,
        marshee_response=marshee_response,
        question="How can I help you?"
    ))
    
    return APIResponse(
        success=True,
        flow_type="main",
        stage_id="main_conversation",
        stage_number=1,
        total_stages=0,
        question="How can I help you?",
        marshee_response=marshee_response,
        next_stage="",
        data={}
    )

async def welcome_back_user(user: UserData) -> APIResponse:
    """Welcome back returning user"""
    marshee_response = f"Welcome back, {user.user_name}! How are you and {user.pet_name} doing today?"
    
    return APIResponse(
        success=True,
        flow_type="main",
        stage_id="main_conversation",
        stage_number=1,
        total_stages=0,
        question="How can I help you?",
        marshee_response=marshee_response,
        next_stage="",
        data={}
    )

async def build_response(user_message: str, user: UserData, context: dict) -> str:
    """Build response with or without context"""
    
    pet_name = user.pet_name or "your pet"
    user_name = user.user_name or "there"
    
    # Check if we have context data
    has_context = context and any(len(results) > 0 for results in context.values())
    
    if has_context:
        # Response with context
        total_results = sum(len(results) for results in context.values())
        response = f"Hi {user_name}! I found {total_results} relevant pieces of information about {pet_name}. "
        
        # Simple context-based response
        if any("health" in key for key in context.keys()):
            response += f"I can help with {pet_name}'s health concerns. "
        elif any("product" in key for key in context.keys()):
            response += f"I found some product recommendations for {pet_name}. "
        elif any("grooming" in key for key in context.keys()):
            response += f"Here's what I know about grooming {pet_name}. "
        elif any("user_summary" in key for key in context.keys()):
            response += f"Based on our previous conversations about {pet_name}, "
        
        response += "What specific information would you like?"
    else:
        # Response without context (fallback)
        response = f"Hi {user_name}! I'm here to help you with {pet_name}. "
        
        # Simple keyword-based responses
        query_lower = user_message.lower()
        if any(word in query_lower for word in ["sick", "health", "vet", "illness"]):
            response += f"I understand you're concerned about {pet_name}'s health. For any serious symptoms, please contact your vet immediately. "
        elif any(word in query_lower for word in ["food", "eat", "nutrition", "diet"]):
            response += f"Good nutrition is important for {pet_name}. High-quality food with meat as the first ingredient is usually best. "
        elif any(word in query_lower for word in ["groom", "bath", "brush", "clean"]):
            response += f"Regular grooming keeps {pet_name} healthy and clean. "
        else:
            response += f"I'm here to help with any questions about {pet_name}'s care. "
        
        response += "What would you like to know?"
    
    logger.info("Built response", 
               user_id=user.firestore_id,
               has_context=has_context,
               query=user_message[:50])
    
    return response