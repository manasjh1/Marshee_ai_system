# app/pinecone_service.py - Fixed to read API key correctly and setup namespaces
import os
from typing import Dict, List
from datetime import datetime
from pinecone import Pinecone
from app.config import settings
import structlog
import time

logger = structlog.get_logger()

class PineconeService:
    def __init__(self):
        self.pc = None
        self.index = None
        self.embedding_model = None
        self.initialized = False
        self.namespaces = ["user_history", "health_data", "product_data", "grooming_data", "company_data"]
    
    async def initialize(self):
        try:
            # Try multiple ways to get the API key
            pinecone_key = settings.pinecone_api_key or os.getenv("PINECONE_API_KEY")
            
            if not pinecone_key:
                logger.warning("Pinecone API key not found in settings or environment")
                return
            
            logger.info(f"Found Pinecone API key: {pinecone_key[:10]}...")
            
            try:
                from sentence_transformers import SentenceTransformer
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Loaded sentence transformer model")
            except Exception as e:
                logger.warning("sentence-transformers not available", error=str(e))
                return
            
            # Initialize Pinecone
            self.pc = Pinecone(api_key=pinecone_key)
            index_name = settings.pinecone_index_name or "marshee-ai"
            
            # Check if index exists
            existing_indexes = self.pc.list_indexes().names()
            if index_name not in existing_indexes:
                logger.info(f"Creating Pinecone index: {index_name}")
                self.pc.create_index(
                    name=index_name,
                    dimension=384,
                    metric='cosine',
                    spec={'serverless': {'cloud': 'aws', 'region': 'us-east-1'}}
                )
                # Wait for index to be ready
                logger.info("Waiting for index to be ready...")
                time.sleep(15)
            
            self.index = self.pc.Index(index_name)
            
            # Verify index is ready
            stats = self.index.describe_index_stats()
            logger.info(f"Index stats: {stats}")
            
            self.initialized = True
            logger.info("Pinecone initialized successfully")
            logger.info(f"Available namespaces: {self.namespaces}")
            
        except Exception as e:
            logger.error("Pinecone initialization failed", error=str(e))
            self.initialized = False
    
    def get_embedding(self, text: str) -> List[float]:
        try:
            if self.initialized and self.embedding_model:
                return self.embedding_model.encode(text).tolist()
        except Exception as e:
            logger.warning("Embedding generation failed", error=str(e))
        return [0.0] * 384
    
    def select_namespaces(self, query: str) -> List[str]:
        query_lower = query.lower()
        namespaces = ["user_history"]  # Always include user history
        
        if any(word in query_lower for word in ["health", "sick", "vet", "illness", "medical", "symptom"]):
            namespaces.append("health_data")
        if any(word in query_lower for word in ["food", "nutrition", "product", "toy", "buy", "recommend"]):
            namespaces.append("product_data")
        if any(word in query_lower for word in ["groom", "bath", "clean", "brush", "hygiene"]):
            namespaces.append("grooming_data")
        if any(word in query_lower for word in ["company", "support", "policy", "service", "help"]):
            namespaces.append("company_data")
        
        # Default to health if no specific match
        if len(namespaces) == 1:
            namespaces.append("health_data")
        
        return namespaces
    
    async def get_context_for_llm(self, user_id: str, query: str) -> Dict:
        if not self.initialized:
            return {}
        
        try:
            embedding = self.get_embedding(query)
            namespaces = self.select_namespaces(query)
            results = {}
            
            for namespace in namespaces:
                try:
                    if namespace == "user_history":
                        search_result = self.index.query(
                            vector=embedding,
                            top_k=5,
                            include_metadata=True,
                            namespace=namespace,
                            filter={"user_id": user_id}
                        )
                    else:
                        search_result = self.index.query(
                            vector=embedding,
                            top_k=3,
                            include_metadata=True,
                            namespace=namespace
                        )
                    
                    results[namespace] = []
                    threshold = 0.5 if namespace == "user_history" else 0.7
                    
                    for match in search_result.matches:
                        if match.score > threshold:
                            results[namespace].append({
                                "text": match.metadata.get("text", ""),
                                "score": match.score,
                                "type": match.metadata.get("type", ""),
                                "created_at": match.metadata.get("created_at", "")
                            })
                except Exception as e:
                    logger.warning(f"Search failed for {namespace}", error=str(e))
                    results[namespace] = []
            
            return results
        except Exception as e:
            logger.warning("Context retrieval failed", error=str(e))
            return {}
    
    async def save_user_profile(self, user_id: str, user_data: Dict):
        if not self.initialized:
            return
        
        try:
            profile_text = f"""User Profile:
User: {user_data.get('user_name', 'Unknown')}
Pet: {user_data.get('pet_name', 'Unknown')} ({user_data.get('pet_type', 'Unknown')})
Breed: {user_data.get('pet_breed', 'Unknown')}
Age: {user_data.get('pet_age', 'Unknown')} years
Weight: {user_data.get('pet_weight', 'Unknown')} kg
Gender: {user_data.get('pet_gender', 'Unknown')}
Setup completed: {datetime.utcnow().strftime('%Y-%m-%d')}"""
            
            embedding = self.get_embedding(profile_text)
            
            self.index.upsert(
                vectors=[{
                    "id": f"profile_{user_id}",
                    "values": embedding,
                    "metadata": {
                        "text": profile_text,
                        "user_id": user_id,
                        "type": "user_profile",
                        "created_at": datetime.utcnow().isoformat(),
                        **{k: v for k, v in user_data.items() if isinstance(v, (str, int, float, bool))}
                    }
                }],
                namespace="user_summary"
            )
            logger.info(f"User profile saved for {user_id}")
        except Exception as e:
            logger.warning("Profile save failed", error=str(e))
    
    async def save_chat_summary_to_user_history(self, user_id: str, summary: str, chat_history: List[Dict]):
        if not self.initialized:
            return
        
        try:
            embedding = self.get_embedding(summary)
            summary_id = f"summary_{user_id}_{int(time.time())}"
            
            self.index.upsert(
                vectors=[{
                    "id": summary_id,
                    "values": embedding,
                    "metadata": {
                        "text": summary,
                        "user_id": user_id,
                        "type": "chat_summary",
                        "message_count": len(chat_history),
                        "created_at": datetime.utcnow().isoformat()
                    }
                }],
                namespace="user_history"
            )
            logger.info(f"Chat summary saved to user_history for {user_id}")
        except Exception as e:
            logger.warning("Summary save failed", error=str(e))
    
    async def get_namespace_stats(self):
        """Get statistics for all namespaces"""
        if not self.initialized:
            return {}
        
        try:
            stats = self.index.describe_index_stats()
            return stats
        except Exception as e:
            logger.warning("Failed to get namespace stats", error=str(e))
            return {}
    
    def is_ready(self) -> bool:
        return self.initialized

pinecone_service = PineconeService()