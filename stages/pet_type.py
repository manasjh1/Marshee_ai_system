"""Stage 3: Pet Type"""

STAGE_CONFIG = {
    "stage_id": "pet_type",
    "stage_number": 3,
    "question": "What type of pet do you have?",
    "type": "button",
    "next_stage": "pet_gender",
    "options": ["dog", "cat"]
}

def get_marshee_response(user_data: dict, is_error: bool = False) -> str:
    """Generate Marshee response for this stage"""
    if is_error:
        return "Please select a pet type. What type of pet do you have?"
    
    pet_name = user_data.get('pet_name', 'Your pet')
    return f"{pet_name} is such a lovely name! What type of pet is {pet_name}?"

def validate_input(value: str) -> bool:
    """Validate input for this stage"""
    return value.strip().lower() in ["dog", "cat"]

def get_stage_data() -> dict:
    """Get data for this stage (buttons/dropdown options)"""
    return {"buttons": ["dog", "cat"]}
