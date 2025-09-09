# app/main.py - Clean and simple
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database import connect_to_mongo, close_mongo_connection
from app.pinecone_service import pinecone_service
from app.models import APIRequest, APIResponse
from app.handlers import onboarding_handler, conversation_handler

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown"""
    await connect_to_mongo()
    await pinecone_service.initialize()
    yield
    await close_mongo_connection()

app = FastAPI(
    title="Marshee AI",
    description="Pet Care Assistant",
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

@app.post("/api/v1/marshee", response_model=APIResponse)
async def marshee_interaction(request: APIRequest):
    """Main endpoint"""
    try:
        if not request.firestore_id or len(request.firestore_id) < 5:
            raise HTTPException(status_code=400, detail="Invalid firestore_id")
        
        # Check if user completed setup
        from app.services import user_service
        user = await user_service.get_user(request.firestore_id)
        
        if user.initial_setup_complete:
            # Handle main conversation with Pinecone
            return await conversation_handler.handle_conversation(request, user)
        else:
            # Handle onboarding flow
            return await onboarding_handler.handle_onboarding(request, user)
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/")
async def root():
    return {"message": "Marshee AI", "status": "active"}

@app.get("/health")
async def health():
    return {"status": "healthy"}