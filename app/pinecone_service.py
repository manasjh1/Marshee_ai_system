# app/pinecone_service.py - Safe version that handles no data
"""Safe Pinecone service that works with or without data"""

import os
from typing import Dict, List
from pinecone import Pinecone
import structlog

logger = structlog.get_logger()

class PineconeService:
    def __init__(self):
        self.pc = None
        self.index = None
        self.openai_client = None
        self.initialized = False
    
    async def initialize(self):
        """Initialize Pinecone (safe initialization)"""
        try:
            # Check if API keys exist
            pinecone_key = os.getenv("PINECONE_API_KEY")
            openai_key = os.getenv("OPENAI_API_KEY")
            
            if not pinecone_key or not openai_key:
                logger.warning("Missing API keys - Pinecone service disabled")
                return
            
            # Initialize Pinecone
            self.pc = Pinecone(api_key=pinecone_key)
            index_name = os.getenv("PINECONE_INDEX_NAME", "marshee-ai")
            
            # Check if index exists
            existing_indexes = self.pc.list_indexes().names()
            if index_name not in existing_indexes:
                logger.warning(f"Pinecone index '{index_name}' not found - will create empty responses")
                return
            
            self.index = self.pc.Index(index_name)
            
            self.initialized = True
            logger.info("Pinecone service initialized successfully")
            
        except Exception as e:
            logger.warning("Pinecone initialization failed - using fallback mode", error=str(e))
            self.initialized = False
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for text (safe)"""
        try:
            if not self.initialized or not self.openai_client:
                return [0.0] * 1536  # Empty embedding
            
            response = self.openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.warning("Embedding generation failed", error=str(e))
            return [0.0] * 1536
    
    def select_namespaces(self, query: str) -> List[str]:
        """Select relevant namespaces based on query"""
        query_lower = query.lower()
        namespaces = ["user_summary"]  # Always include user data
        
        # Simple keyword matching
        if any(word in query_lower for word in ["health", "sick", "disease", "vet"]):
            namespaces.append("health_data")
        
        if any(word in query_lower for word in ["food", "eat", "nutrition", "diet"]):
            namespaces.append("product_data")
        
        if any(word in query_lower for word in ["bath", "groom", "brush", "clean"]):
            namespaces.append("grooming_data")
        
        if any(word in query_lower for word in ["company", "help", "support"]):
            namespaces.append("company_data")
        
        # Default to health if no specific match
        if len(namespaces) == 1:
            namespaces.append("health_data")
        
        return namespaces
    
    async def get_context(self, user_id: str, query: str) -> Dict:
        """Get context for user query (safe - returns empty if no data)"""
        try:
            if not self.initialized or not self.index:
                logger.info("Pinecone not available - returning empty context")
                return {}
            
            # Get query embedding
            embedding = self.get_embedding(query)
            
            # Select namespaces
            namespaces = self.select_namespaces(query)
            
            # Search each namespace
            results = {}
            for namespace in namespaces:
                try:
                    search_result = self.index.query(
                        vector=embedding,
                        top_k=3,
                        include_metadata=True,
                        namespace=namespace
                    )
                    
                    # Format results
                    results[namespace] = []
                    for match in search_result.matches:
                        if match.score > 0.7:  # Only good matches
                            results[namespace].append({
                                "text": match.metadata.get("text", ""),
                                "score": match.score,
                                "type": match.metadata.get("type", "")
                            })
                            
                except Exception as e:
                    logger.warning(f"Search failed for namespace {namespace}", error=str(e))
                    results[namespace] = []
            
            logger.info("Retrieved context", user_id=user_id, namespaces=namespaces)
            return results
            
        except Exception as e:
            logger.warning("Context retrieval failed - returning empty", error=str(e))
            return {}
    
    async def save_user_data(self, user_id: str, user_data: Dict):
        """Save user profile to Pinecone (safe)"""
        try:
            if not self.initialized or not self.index:
                logger.info("Pinecone not available - skipping user data save")
                return
            
            # Create user profile text
            profile_text = f"""
            User: {user_data.get('user_name', 'Unknown')}
            Pet: {user_data.get('pet_name', 'Unknown')}
            Type: {user_data.get('pet_type', 'Unknown')}
            Breed: {user_data.get('pet_breed', 'Unknown')}
            Age: {user_data.get('pet_age', 'Unknown')} years
            Weight: {user_data.get('pet_weight', 'Unknown')} kg
            Gender: {user_data.get('pet_gender', 'Unknown')}
            """
            
            # Get embedding
            embedding = self.get_embedding(profile_text)
            
            # Save to Pinecone
            self.index.upsert(
                vectors=[{
                    "id": f"user_{user_id}",
                    "values": embedding,
                    "metadata": {
                        "text": profile_text,
                        "user_id": user_id,
                        "type": "profile",
                        **user_data
                    }
                }],
                namespace="user_summary"
            )
            
            logger.info("Saved user data to Pinecone", user_id=user_id)
            
        except Exception as e:
            logger.warning("Failed to save user data - continuing without", error=str(e))
    
    def is_ready(self) -> bool:
        """Check if Pinecone service is ready"""
        return self.initialized and self.index is not None

# Global instance
pinecone_service = PineconeService()   