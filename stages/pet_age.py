"""Stage 5: Pet Age"""

STAGE_CONFIG = {
    "stage_id": "pet_age",
    "stage_number": 5,
    "question": "What's your pet's age (in years)?",
    "type": "text",
    "next_stage": "pet_weight",
    "validation": {
        "min_value": 1,
        "max_value": 25,
        "type": "number",
        "error_message": "Pet age must be between 1 and 25 years"
    }
}

def get_marshee_response(user_data: dict, is_error: bool = False) -> str:
    """Generate Marshee response for this stage"""
    if is_error:
        return "Please provide a valid age between 1 and 25 years. What's your pet's age?"
    
    pet_breed = user_data.get('pet_breed', '')
    pet_type = user_data.get('pet_type', 'pet')
    pet_name = user_data.get('pet_name', 'your pet')
    
    return f"A {pet_breed}! They're wonderful {pet_type}s. How old is {pet_name}?"

def validate_input(value: str) -> bool:
    """Validate input for this stage"""
    try:
        age = float(value.strip())
        return 1 <= age <= 25
    except ValueError:
        return False