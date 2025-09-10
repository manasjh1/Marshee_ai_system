# app/handlers/conversation_handler.py - Minimal conversation handler
from app.models import APIRequest, APIResponse, UserData, ChatMessage
from app.services import user_service
from app.pinecone_service import pinecone_service
from app.redis_service import redis_service
from app.groq_service import groq_service
import random # Added random module

async def handle_conversation(request: APIRequest, user: UserData) -> APIResponse:
    if request.user_message:
        return await process_user_message(request, user)
    else:
        return await welcome_back_user(user)

async def process_user_message(request: APIRequest, user: UserData) -> APIResponse:
    user_id = request.firestore_id
    user_message = request.user_message
    
    # Get context from all sources
    redis_chat = await redis_service.get_current_chat(user_id)
    vector_context = await pinecone_service.get_context_for_llm(user_id, user_message)
    
    # Generate response
    marshee_response = await groq_service.generate_response_with_full_context(
        user_message=user_message,
        user_data=user.model_dump(),
        redis_chat=redis_chat,
        vector_context=vector_context
    )
    
    # Store in Redis (auto-summary at 10 messages)
    await redis_service.add_message(user_id, user_message, marshee_response)
    
    # Store in MongoDB
    await user_service.save_chat(ChatMessage(
        firestore_id=user_id,
        stage_id="main_conversation",
        user_message=user_message,
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
    greetings = [
        f"Hey, {user.user_name}! It's great to see you again. What's new with {user.pet_name}?",
        f"Welcome back, {user.user_name}! How are you and {user.pet_name} doing today?",
        f"Glad you're back, {user.user_name}! What can I help you with for {user.pet_name}?",
        f"Hi, {user.user_name}! Let's talk pets. How can I help you and {user.pet_name}?"
    ]
    
    marshee_response = random.choice(greetings)
    
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