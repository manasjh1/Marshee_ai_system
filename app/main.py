# app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime
import structlog

from app.database import connect_to_mongo, close_mongo_connection, get_database
from app.models import APIRequest, APIResponse, UserData, ChatMessage
from app.config import TOTAL_STAGES
import stages

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan"""
    await connect_to_mongo()
    yield
    await close_mongo_connection()

app = FastAPI(
    title="Marshee AI System",
    description="Simple Pet Care Assistant API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def get_user(firestore_id: str) -> UserData:
    """Get or create user"""
    db = get_database()
    user_doc = await db.users.find_one({"firestore_id": firestore_id})
    
    if user_doc:
        return UserData(**user_doc)
    
    # Create new user
    new_user = UserData(firestore_id=firestore_id)
    await db.users.insert_one(new_user.model_dump())
    return new_user

async def update_user(firestore_id: str, update_data: dict):
    """Update user data"""
    db = get_database()
    update_data["updated_at"] = datetime.utcnow()
    await db.users.update_one(
        {"firestore_id": firestore_id},
        {"$set": update_data}
    )

async def save_chat(chat_message: ChatMessage):
    """Save chat message"""
    db = get_database()
    await db.chat_messages.insert_one(chat_message.model_dump())

@app.post("/api/v1/marshee", response_model=APIResponse)
async def marshee_interaction(request: APIRequest):
    """Single endpoint for all Marshee interactions"""
    try:
        # Validate firestore_id
        if not request.firestore_id or len(request.firestore_id) < 5:
            raise HTTPException(status_code=400, detail="Invalid firestore_id")
        
        # Get user
        user = await get_user(request.firestore_id)
        
        # Handle returning user (initial setup complete)
        if user.initial_setup_complete:
            marshee_response = f"Welcome back, {user.user_name or 'there'}! How are you and {user.pet_name or 'your pet'} doing today? How can I help?"
            
            # Save chat if user sent a message
            if request.user_message:
                await save_chat(ChatMessage(
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
        
        # Handle initial setup flow
        current_stage = user.current_stage
        
        # If no stage_id provided, return current stage
        if not request.stage_id:
            stage_config = stages.get_stage_config(current_stage)
            if not stage_config:
                raise HTTPException(status_code=400, detail="Invalid stage")
            
            marshee_response = stages.get_stage_response(current_stage, user.model_dump())
            
            # Get stage data (buttons/dropdown)
            stage_data = stages.get_stage_data(current_stage, user.model_dump())
            
            # Format question with user data
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
        
        # Process stage submission
        stage_config = stages.get_stage_config(request.stage_id)
        if not stage_config:
            raise HTTPException(status_code=400, detail="Invalid stage_id")
        
        # Validate input
        if not stages.validate_stage_input(request.stage_id, request.user_message):
            marshee_response = stages.get_stage_response(request.stage_id, user.model_dump(), is_error=True)
            
            # Format question with user data
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
        
        # Update user data
        update_data = {
            request.stage_id: request.user_message,
            "current_stage": stage_config["next_stage"]
        }
        
        # Add to completed stages
        if request.stage_id not in user.completed_stages:
            user.completed_stages.append(request.stage_id)
            update_data["completed_stages"] = user.completed_stages
        
        # Check if initial setup is complete (weight is the final stage)
        if stage_config["next_stage"] == "complete":
            # Import the weight stage module
            import stages.pet_weight as weight_stage
            
            await update_user(request.firestore_id, update_data)
            
            # Get updated user data for assessment
            updated_user = await get_user(request.firestore_id)
            
            # Process weight and get assessment using stage logic
            db = get_database()
            assessment = await weight_stage.process_weight_submission(
                db,
                request.firestore_id, 
                request.user_message, 
                updated_user.model_dump()
            )
            
            # Mark initial setup complete
            await update_user(request.firestore_id, {
                "initial_setup_complete": True,
                "current_stage": "main_conversation"
            })
            
            # Create response with weight assessment
            base_message = f"Perfect! Now I know all about you and {updated_user.pet_name}."
            weight_message = f" {assessment['message']}"
            help_message = f" I'm here to help with any questions about {updated_user.pet_name}'s health, nutrition, training, or general care. What would you like to know?"
            
            marshee_response = base_message + weight_message + help_message
            
            # Save chat
            await save_chat(ChatMessage(
                firestore_id=request.firestore_id,
                stage_id=request.stage_id,
                user_message=request.user_message,
                marshee_response=marshee_response,
                question=stage_config["question"]
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
        
        await update_user(request.firestore_id, update_data)
        
        # Get next stage
        next_stage_id = stage_config["next_stage"]
        next_stage_config = stages.get_stage_config(next_stage_id)
        
        # Get updated user data
        updated_user = await get_user(request.firestore_id)
        marshee_response = stages.get_stage_response(next_stage_id, updated_user.model_dump())
        
        # Get stage data for next stage
        stage_data = stages.get_stage_data(next_stage_id, updated_user.model_dump())
        
        # Format question with user data
        next_question = next_stage_config["question"].format(
            pet_type=updated_user.pet_type or "pet",
            pet_name=updated_user.pet_name or "your pet"
        )
        
        # Save chat
        await save_chat(ChatMessage(
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
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error", error=str(e), firestore_id=request.firestore_id)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/")
async def root():
    return {"message": "Marshee AI System", "version": "1.0.0", "status": "active"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/api/v1/profile/{firestore_id}")
async def get_user_profile(firestore_id: str):
    """Get user profile with weight assessment"""
    try:
        user = await get_user(firestore_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "success": True,
            "user_profile": user.model_dump(),
            "weight_status": user.weight_assessment.status if user.weight_assessment else "unknown"
        }
        
    except Exception as e:
        logger.error("Failed to get profile", error=str(e), firestore_id=firestore_id)
        raise HTTPException(status_code=500, detail="Internal server error")