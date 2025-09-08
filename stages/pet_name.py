"""Stage 2: Pet Name"""

STAGE_CONFIG = {
    "stage_id": "pet_name",
    "stage_number": 2,
    "question": "What's your pet's name?",
    "type": "text",
    "next_stage": "pet_type",
    "validation": {
        "min_length": 1,
        "max_length": 30,
        "error_message": "Pet name must be between 1-30 characters"
    }
}

def get_marshee_response(user_data: dict, is_error: bool = False) -> str:
    """Generate Marshee response for this stage"""
    if is_error:
        return "Please provide a valid pet name. What's your pet's name?"
    
    user_name = user_data.get('user_name', '')
    return f"Nice to meet you, {user_name}! Now tell me about your pet. What's your pet's name?"

def validate_input(value: str) -> bool:
    """Validate input for this stage"""
    if not value.strip():
        return False
    if len(value.strip()) < 1 or len(value.strip()) > 30:
        return False
    return True
