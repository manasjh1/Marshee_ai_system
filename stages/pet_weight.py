"""Stage 7: Pet Weight - Final Stage with Assessment"""

from datetime import datetime

STAGE_CONFIG = {
    "stage_id": "pet_weight",
    "stage_number": 7,
    "question": "What's your pet's weight (in kg)?",
    "type": "text",
    "next_stage": "complete",
    "validation": {
        "min_value": 0.5,
        "max_value": 100,
        "type": "number",
        "error_message": "Pet weight must be between 0.5 and 100 kg"
    }
}

def get_marshee_response(user_data: dict, is_error: bool = False) -> str:
    if is_error:
        return "Please provide a valid weight between 0.5 and 100 kg. What's your pet's weight?"
    
    pet_age = user_data.get('pet_age', '')
    pet_name = user_data.get('pet_name', 'Your pet')
    
    return f"{pet_age} years old! {pet_name} sounds lovely. What's {pet_name}'s weight in kilograms?"

def validate_input(value: str) -> bool:
    try:
        weight = float(value.strip())
        return 0.5 <= weight <= 100
    except ValueError:
        return False

async def get_weight_assessment(db, breed: str, gender: str, age: str, weight: float) -> dict:
    """Get weight assessment from MongoDB data"""
    if not all([breed, gender, age]):
        return {
            "status": "incomplete",
            "message": "Weight recorded successfully!",
            "weight_range": "Unknown",
            "current_weight": weight,
            "deviation_percent": 0
        }
    
    # Convert age to months for lookup
    try:
        age_months = int(age) * 12
    except ValueError:
        age_months = 24  # Default to 2 years
    
    # Find closest age match in database
    breed_data = await db.breed_weights.find_one({
        "breed": breed.lower().replace(" ", "_"),
        "gender": gender.lower(),
        "age_months": {"$lte": age_months}
    }, sort=[("age_months", -1)])
    
    if not breed_data:
        # Fallback to any data for this breed/gender
        breed_data = await db.breed_weights.find_one({
            "breed": breed.lower().replace(" ", "_"),
            "gender": gender.lower()
        })
    
    if not breed_data:
        return {
            "status": "unknown",
            "message": "Weight standards not available for this breed/gender combination. Weight recorded successfully!",
            "weight_range": "Unknown",
            "current_weight": weight,
            "deviation_percent": 0
        }
    
    min_weight = breed_data["min_weight"]
    max_weight = breed_data["max_weight"]
    ideal_weight = (min_weight + max_weight) / 2
    
    # Calculate deviation
    deviation_percent = ((weight - ideal_weight) / ideal_weight) * 100
    
    # Determine status
    if weight < min_weight:
        if abs(deviation_percent) > 15:
            status = "severely_underweight"
            message = "Based on breed standards, your pet appears to be significantly underweight. Please consult a veterinarian for proper nutritional guidance."
        else:
            status = "underweight"
            message = "Based on breed standards, your pet appears to be underweight. Consider consulting a veterinarian about proper nutrition."
    elif weight > max_weight:
        if deviation_percent > 15:
            status = "obese"
            message = "Based on breed standards, your pet appears to be significantly overweight. Please consult a veterinarian about a weight management plan."
        elif deviation_percent > 5:
            status = "overweight"
            message = "Based on breed standards, your pet appears to be slightly overweight. Consider adjusting diet and exercise routines."
        else:
            status = "healthy"
            message = "Based on breed standards, your pet's weight appears to be in a healthy range!"
    else:
        status = "healthy"
        message = "Based on breed standards, your pet's weight appears to be in a healthy range for their breed, age, and gender."
    
    return {
        "status": status,
        "message": message,
        "weight_range": f"{min_weight}-{max_weight} kg",
        "current_weight": weight,
        "deviation_percent": round(deviation_percent, 1)
    }

async def save_weight_assessment_to_profile(db, firestore_id: str, assessment_data: dict):
    """Save weight assessment to user profile"""
    # Update user profile with weight assessment
    await db.users.update_one(
        {"firestore_id": firestore_id},
        {"$set": {
            "weight_assessment": {
                "status": assessment_data["status"],
                "message": assessment_data["message"],
                "weight_range": assessment_data["weight_range"],
                "current_weight": assessment_data["current_weight"],
                "deviation_percent": assessment_data["deviation_percent"],
                "assessed_at": datetime.utcnow()
            },
            "updated_at": datetime.utcnow()
        }}
    )

async def process_weight_submission(db, firestore_id: str, weight_str: str, user_data: dict) -> dict:
    """Process weight submission and return assessment"""
    weight = float(weight_str)
    
    # Get weight assessment
    assessment = await get_weight_assessment(
        db,
        user_data.get('pet_breed', ''),
        user_data.get('pet_gender', ''),
        user_data.get('pet_age', ''),
        weight
    )
    
    # Save assessment to profile
    await save_weight_assessment_to_profile(db, firestore_id, assessment)
    
    return assessment