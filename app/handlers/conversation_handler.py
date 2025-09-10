# app/handlers/conversation_handler.py - Minimal conversation handler
from app.models import APIRequest, APIResponse, UserData, ChatMessage
from app.services import user_service
from app.pinecone_service import pinecone_service
from app.redis_service import redis_service
from app.groq_service import groq_service

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