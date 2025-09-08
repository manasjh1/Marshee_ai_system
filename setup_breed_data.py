"""Setup breed weight standards in MongoDB - Standalone Script"""

import asyncio
import motor.motor_asyncio
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

BREED_WEIGHT_DATA = [
    
    # Golden Retriever - Male
    {"breed": "golden_retriever", "gender": "male", "age_months": 0, "min_weight": 0.2, "max_weight": 0.45},
    {"breed": "golden_retriever", "gender": "male", "age_months": 1, "min_weight": 2.3, "max_weight": 4.5},
    {"breed": "golden_retriever", "gender": "male", "age_months": 2, "min_weight": 4.5, "max_weight": 9.0},
    {"breed": "golden_retriever", "gender": "male", "age_months": 3, "min_weight": 9.0, "max_weight": 13.6},
    {"breed": "golden_retriever", "gender": "male", "age_months": 4, "min_weight": 13.6, "max_weight": 18.0},
    {"breed": "golden_retriever", "gender": "male", "age_months": 5, "min_weight": 18.0, "max_weight": 22.7},
    {"breed": "golden_retriever", "gender": "male", "age_months": 6, "min_weight": 22.7, "max_weight": 27.2},
    {"breed": "golden_retriever", "gender": "male", "age_months": 7, "min_weight": 25.0, "max_weight": 29.5},
    {"breed": "golden_retriever", "gender": "male", "age_months": 8, "min_weight": 27.2, "max_weight": 31.8},
    {"breed": "golden_retriever", "gender": "male", "age_months": 9, "min_weight": 29.5, "max_weight": 34.0},
    {"breed": "golden_retriever", "gender": "male", "age_months": 10, "min_weight": 29.5, "max_weight": 34.0},
    {"breed": "golden_retriever", "gender": "male", "age_months": 11, "min_weight": 31.8, "max_weight": 36.3},
    {"breed": "golden_retriever", "gender": "male", "age_months": 12, "min_weight": 31.8, "max_weight": 38.6},
    {"breed": "golden_retriever", "gender": "male", "age_months": 24, "min_weight": 34.0, "max_weight": 40.8},
    {"breed": "golden_retriever", "gender": "male", "age_months": 36, "min_weight": 34.0, "max_weight": 43.1},

    # Golden Retriever - Female (from page 1 - data appears incomplete in PDF, using typical ranges)
    {"breed": "golden_retriever", "gender": "female", "age_months": 0, "min_weight": 0.2, "max_weight": 0.4},
    {"breed": "golden_retriever", "gender": "female", "age_months": 1, "min_weight": 2.0, "max_weight": 4.1},
    {"breed": "golden_retriever", "gender": "female", "age_months": 2, "min_weight": 3.6, "max_weight": 8.2},
    {"breed": "golden_retriever", "gender": "female", "age_months": 3, "min_weight": 8.2, "max_weight": 12.3},
    {"breed": "golden_retriever", "gender": "female", "age_months": 4, "min_weight": 12.3, "max_weight": 16.8},
    {"breed": "golden_retriever", "gender": "female", "age_months": 5, "min_weight": 15.9, "max_weight": 21.3},
    {"breed": "golden_retriever", "gender": "female", "age_months": 6, "min_weight": 18.1, "max_weight": 25.0},
    {"breed": "golden_retriever", "gender": "female", "age_months": 7, "min_weight": 20.4, "max_weight": 27.2},
    {"breed": "golden_retriever", "gender": "female", "age_months": 8, "min_weight": 22.7, "max_weight": 29.5},
    {"breed": "golden_retriever", "gender": "female", "age_months": 9, "min_weight": 25.0, "max_weight": 31.8},
    {"breed": "golden_retriever", "gender": "female", "age_months": 10, "min_weight": 25.0, "max_weight": 32.7},
    {"breed": "golden_retriever", "gender": "female", "age_months": 11, "min_weight": 26.3, "max_weight": 34.0},
    {"breed": "golden_retriever", "gender": "female", "age_months": 12, "min_weight": 27.2, "max_weight": 36.3},
    {"breed": "golden_retriever", "gender": "female", "age_months": 24, "min_weight": 29.5, "max_weight": 38.6},
    {"breed": "golden_retriever", "gender": "female", "age_months": 36, "min_weight": 29.5, "max_weight": 40.8},

    # Labrador Retriever - Male
    {"breed": "labrador", "gender": "male", "age_months": 0, "min_weight": 0.2, "max_weight": 0.7},
    {"breed": "labrador", "gender": "male", "age_months": 1, "min_weight": 3.6, "max_weight": 6.8},
    {"breed": "labrador", "gender": "male", "age_months": 2, "min_weight": 5.4, "max_weight": 9.1},
    {"breed": "labrador", "gender": "male", "age_months": 3, "min_weight": 9.1, "max_weight": 13.6},
    {"breed": "labrador", "gender": "male", "age_months": 4, "min_weight": 11.3, "max_weight": 18.1},
    {"breed": "labrador", "gender": "male", "age_months": 5, "min_weight": 13.6, "max_weight": 22.7},
    {"breed": "labrador", "gender": "male", "age_months": 6, "min_weight": 15.9, "max_weight": 27.2},
    {"breed": "labrador", "gender": "male", "age_months": 7, "min_weight": 18.1, "max_weight": 29.5},
    {"breed": "labrador", "gender": "male", "age_months": 8, "min_weight": 20.4, "max_weight": 31.8},
    {"breed": "labrador", "gender": "male", "age_months": 9, "min_weight": 22.7, "max_weight": 34.0},
    {"breed": "labrador", "gender": "male", "age_months": 10, "min_weight": 24.9, "max_weight": 36.3},
    {"breed": "labrador", "gender": "male", "age_months": 11, "min_weight": 27.2, "max_weight": 38.6},
    {"breed": "labrador", "gender": "male", "age_months": 12, "min_weight": 29.5, "max_weight": 40.8},
    {"breed": "labrador", "gender": "male", "age_months": 24, "min_weight": 29.5, "max_weight": 40.8},
    {"breed": "labrador", "gender": "male", "age_months": 36, "min_weight": 29.5, "max_weight": 40.8},

]


async def setup_breed_data():
    """Insert breed weight data into MongoDB"""
    # Connect to MongoDB
    mongodb_url = os.getenv("MONGODB_URL")
    database_name = os.getenv("DATABASE_NAME", "marshee_ai")
    
    client = motor.motor_asyncio.AsyncIOMotorClient(mongodb_url)
    db = client[database_name]
    
    try:
        # Test connection
        await client.admin.command('ping')
        print("Connected to MongoDB")
        
        # Clear existing data
        await db.breed_weights.delete_many({})
        print("Cleared existing breed weight data")
        
        # Insert new data
        result = await db.breed_weights.insert_many(BREED_WEIGHT_DATA)
        print(f"Inserted {len(result.inserted_ids)} breed weight records")
        
        # Verify insertion
        count = await db.breed_weights.count_documents({})
        print(f"Total records in database: {count}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(setup_breed_data())
