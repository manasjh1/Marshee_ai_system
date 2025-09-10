# app/handlers/onboarding_handler.py
"""Handle user onboarding flow"""

from app.models import APIRequest, APIResponse, UserData, ChatMessage
from app.services import user_service
from app.pinecone_service import pinecone_service
from app.config import TOTAL_STAGES
import stages

async def handle_onboarding(request: APIRequest, user: UserData) -> APIResponse:
    """Handle onboarding flow"""
    
    # Get current stage
    if not request.stage_id:
        return await get_current_stage(user)
    
    # Process stage submission
    return await process_stage(request, user)

async def get_current_stage(user: UserData) -> APIResponse:
    """Get current stage information"""
    current_stage = user.current_stage
    stage_config = stages.get_stage_config(current_stage)
    
    marshee_response = stages.get_stage_response(current_stage, user.model_dump())
    stage_data = stages.get_stage_data(current_stage, user.model_dump())
    
    question = stage_config["question"].format(
        pet_type=user.pet_type or "pet",
        pet_name=user.pet_name or "your pet"
    )
    
    return APIResponse(
        success=True,
        flow_type="initial",
        stage_id=current_stage,
        stage_number=stage_config["stage_number"],
        total_stages=TOTAL_STAGES,
        question=question,
        marshee_response=marshee_response,
        next_stage=stage_config["next_stage"],
        data=stage_data
    )

async def process_stage(request: APIRequest, user: UserData) -> APIResponse:
    """Process stage submission"""
    stage_config = stages.get_stage_config(request.stage_id)
    
    # Validate input
    if not stages.validate_stage_input(request.stage_id, request.user_message):
        return await handle_validation_error(request, user, stage_config)
    
    # Update user data
    update_data = {
        request.stage_id: request.user_message,
        "current_stage": stage_config["next_stage"]
    }
    
    if request.stage_id not in user.completed_stages:
        user.completed_stages.append(request.stage_id)
        update_data["completed_stages"] = user.completed_stages
    
    # Check if setup complete
    if stage_config["next_stage"] == "complete":
        return await complete_setup(request, update_data)
    
    # Continue to next stage
    return await continue_to_next_stage(request, update_data, stage_config)

async def handle_validation_error(request: APIRequest, user: UserData, stage_config: dict) -> APIResponse:
    """Handle validation error"""
    marshee_response = stages.get_stage_response(request.stage_id, user.model_dump(), is_error=True)
    question = stage_config["question"].format(
        pet_type=user.pet_type or "pet",
        pet_name=user.pet_name or "your pet"
    )
    
    return APIResponse(
        success=False,
        flow_type="initial",
        stage_id=request.stage_id,
        stage_number=stage_config["stage_number"],
        total_stages=TOTAL_STAGES,
        question=question,
        marshee_response=marshee_response,
        next_stage=stage_config["next_stage"],
        data={}
    )

async def complete_setup(request: APIRequest, update_data: dict) -> APIResponse:
    """Complete user setup"""
    import stages.pet_weight as weight_stage
    from app.database import get_database
    
    # Update user
    await user_service.update_user(request.firestore_id, update_data)
    updated_user = await user_service.get_user(request.firestore_id)
    
    # Process weight assessment
    db = get_database()
    assessment = await weight_stage.process_weight_submission(
        db, request.firestore_id, request.user_message, updated_user.model_dump()
    )
    
    # Mark setup complete
    await user_service.complete_user_setup(request.firestore_id)
    
    # Save to Pinecone
    await pinecone_service.save_user_profile(request.firestore_id, updated_user.model_dump())
    
    # Create completion response
    marshee_response = (
        f"Perfect! Setup complete for {updated_user.pet_name}. "
        f"{assessment['message']} "
        f"Ask me anything about {updated_user.pet_name}!"
    )
    
    # Save chat
    await user_service.save_chat(ChatMessage(
        firestore_id=request.firestore_id,
        stage_id=request.stage_id,
        user_message=request.user_message,
        marshee_response=marshee_response,
        question="Final setup"
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

async def continue_to_next_stage(request: APIRequest, update_data: dict, stage_config: dict) -> APIResponse:
    """Continue to next stage"""
    await user_service.update_user(request.firestore_id, update_data)
    
    next_stage_id = stage_config["next_stage"]
    next_stage_config = stages.get_stage_config(next_stage_id)
    
    updated_user = await user_service.get_user(request.firestore_id)
    marshee_response = stages.get_stage_response(next_stage_id, updated_user.model_dump())
    stage_data = stages.get_stage_data(next_stage_id, updated_user.model_dump())
    
    next_question = next_stage_config["question"].format(
        pet_type=updated_user.pet_type or "pet",
        pet_name=updated_user.pet_name or "your pet"
    )
    
    # Save chat
    await user_service.save_chat(ChatMessage(
        firestore_id=request.firestore_id,
        stage_id=request.stage_id,
        user_message=request.user_message,
        marshee_response=marshee_response,
        question=stage_config["question"]
    ))
    
    return APIResponse(
        success=True,
        flow_type="initial",
        stage_id=next_stage_id,
        stage_number=next_stage_config["stage_number"],
        total_stages=TOTAL_STAGES,
        question=next_question,
        marshee_response=marshee_response,
        next_stage=next_stage_config["next_stage"],
        data=stage_data
    )
