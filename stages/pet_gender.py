"""Stage 4: Pet Gender"""

STAGE_CONFIG = {
    "stage_id": "pet_gender",
    "stage_number": 4,
    "question": "What's your pet's gender?",
    "type": "button",
    "next_stage": "pet_breed",
    "options": ["male", "female"]
}

def get_marshee_response(user_data: dict, is_error: bool = False) -> str:
    """Generate Marshee response for this stage"""
    if is_error:
        return "Please select your pet's gender."
    
    pet_name = user_data.get('pet_name', 'Your pet')
    pet_type = user_data.get('pet_type', 'pet')
    return f"Great! {pet_name} is a {pet_type}. Is {pet_name} male or female?"

def validate_input(value: str) -> bool:
    """Validate input for this stage"""
    return value.strip().lower() in ["male", "female"]

def get_stage_data(user_data: dict = None) -> dict:
    """Get data for this stage (buttons/dropdown options)"""
    return {"buttons": ["male", "female"]}