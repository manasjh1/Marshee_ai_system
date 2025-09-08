from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class APIRequest(BaseModel):
    firestore_id: str
    stage_id: str = ""
    user_message: str = ""

class APIResponse(BaseModel):
    success: bool
    flow_type: str = ""
    stage_id: str = ""
    stage_number: int = 0
    total_stages: int = 0
    question: str = ""
    marshee_response: str = ""
    next_stage: str = ""
    data: Dict[str, Any] = {}

class UserData(BaseModel):
    firestore_id: str
    user_name: Optional[str] = None
    pet_name: Optional[str] = None
    pet_type: Optional[str] = None
    pet_gender: Optional[str] = None
    pet_breed: Optional[str] = None
    pet_age: Optional[str] = None
    pet_weight: Optional[str] = None
    weight_assessment: Optional[dict] = None
    current_stage: str = "user_name"
    completed_stages: list = []
    initial_setup_complete: bool = False
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()

class ChatMessage(BaseModel):
    firestore_id: str
    stage_id: str
    user_message: str
    marshee_response: str
    question: str
    created_at: datetime = datetime.utcnow()
