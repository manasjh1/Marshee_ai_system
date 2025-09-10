# app/main.py - Minimal main file
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.redis_service import redis_service
from app.database import connect_to_mongo, close_mongo_connection
from app.pinecone_service import pinecone_service
from app.groq_service import groq_service
from app.models import APIRequest, APIResponse
from app.handlers import onboarding_handler, conversation_handler

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    await pinecone_service.initialize()
    await redis_service.initialize()
    await groq_service.initialize()
    yield
    await close_mongo_connection()

app = FastAPI(title="Marshee AI", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/v1/marshee", response_model=APIResponse)
async def marshee_interaction(request: APIRequest):
    try:
        if not request.firestore_id or len(request.firestore_id) < 5:
            raise HTTPException(status_code=400, detail="Invalid firestore_id")
        
        from app.services import user_service
        user = await user_service.get_user(request.firestore_id)
        
        if user.initial_setup_complete:
            return await conversation_handler.handle_conversation(request, user)
        else:
            return await onboarding_handler.handle_onboarding(request, user)
            
    except HTTPException:
        raise
    except Exception:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in API: {e}")
        print(f"Full traceback: {error_details}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/")
async def root():
    return {"message": "Marshee AI", "status": "active"}

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "services": {
            "groq": "ready" if groq_service.initialized else "unavailable",
            "pinecone": "ready" if pinecone_service.is_ready() else "unavailable",
            "redis": "ready" if redis_service.is_ready() else "unavailable"
        }
    }