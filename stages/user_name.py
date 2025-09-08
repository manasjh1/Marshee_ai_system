"""Stage 1: User Name"""

STAGE_CONFIG = {
    "stage_id": "user_name",
    "stage_number": 1,
    "question": "What's your name?",
    "type": "text",
    "next_stage": "pet_name",
    "validation": {
        "min_length": 2,
        "max_length": 50,
        "error_message": "Name must be between 2-50 characters"
    }
}

def get_marshee_response(user_data: dict, is_error: bool = False) -> str:
    """Generate Marshee response for this stage"""
    if is_error:
        return "Please provide a valid name. What's your name?"
    
    return "Hi there! I'm Marshee, your pet care assistant. Let's get to know you and your furry friend better. What's your name?"

def validate_input(value: str) -> bool:
    """Validate input for this stage"""
    if not value.strip():
        return False
    if len(value.strip()) < 2 or len(value.strip()) > 50:
        return False
    return True
