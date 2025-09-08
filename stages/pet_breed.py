"""Stage 5: Pet Breed"""

STAGE_CONFIG = {
    "stage_id": "pet_breed",
    "stage_number": 5,
    "question": "What breed is your {pet_type}?",
    "type": "dropdown",
    "next_stage": "pet_age",
    "options": {
        "dog": ["labrador", "german_shepherd", "golden_retriever", "indie", "pomeranian", 
               "beagle", "rottweiler", "chihuahua", "pug", "rajapalayam"],
        "cat": ["persian", "siamese", "maine_coon", "british_shorthair", "bengal",
               "ragdoll", "russian_blue", "scottish_fold", "bombay", "indian_billi"]
    }
}

def get_marshee_response(user_data: dict, is_error: bool = False) -> str:
    """Generate Marshee response for this stage"""
    if is_error:
        return "Please select a valid breed. What breed is your pet?"
    
    pet_name = user_data.get('pet_name', 'Your pet')
    pet_type = user_data.get('pet_type', 'pet')
    return f"Great! {pet_name} is a {pet_type}. What breed is {pet_name}?"

def validate_input(value: str) -> bool:
    """Validate input for this stage"""
    all_breeds = []
    for breeds in STAGE_CONFIG["options"].values():
        all_breeds.extend(breeds)
    return value.strip().lower() in all_breeds

def get_stage_data(user_data: dict = None) -> dict:
    """Get data for this stage (buttons/dropdown options)"""
    if not user_data:
        # Default to dog breeds if no user data
        return {"dropdown_options": STAGE_CONFIG["options"]["dog"]}
    
    pet_type = user_data.get('pet_type', 'dog')
    options = STAGE_CONFIG["options"].get(pet_type, STAGE_CONFIG["options"]["dog"])
    return {"dropdown_options": options}