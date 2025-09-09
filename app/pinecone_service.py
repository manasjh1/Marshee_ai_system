# app/pinecone_service.py - Updated without OpenAI
"""Pinecone service using free sentence-transformers for embeddings"""

import os
from typing import Dict, List
from pinecone import Pinecone
import structlog

logger = structlog.get_logger()

class PineconeService:
    def __init__(self):
        self.pc = None
        self.index = None
        self.embedding_model = None
        self.initialized = False
    
    async def initialize(self):
        """Initialize Pinecone with sentence-transformers"""
        try:
            # Check if Pinecone API key exists
            pinecone_key = os.getenv("PINECONE_API_KEY")
            
            if not pinecone_key:
                logger.warning("Missing Pinecone API key - service disabled")
                return
            
            # Initialize sentence-transformers model (free alternative to OpenAI)
            try:
                from sentence_transformers import SentenceTransformer
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')  # Free, fast, good quality
                logger.info("Loaded sentence-transformers model")
            except ImportError:
                logger.warning("sentence-transformers not installed - embeddings disabled")
                return
            
            # Initialize Pinecone
            self.pc = Pinecone(api_key=pinecone_key)
            index_name = os.getenv("PINECONE_INDEX_NAME", "marshee-ai")
            
            # Check if index exists, create if not
            existing_indexes = self.pc.list_indexes().names()
            if index_name not in existing_indexes:
                logger.info(f"Creating Pinecone index '{index_name}'")
                self.pc.create_index(
                    name=index_name,
                    dimension=384,  # all-MiniLM-L6-v2 produces 384-dimensional vectors
                    metric='cosine',
                    spec={
                        'serverless': {
                            'cloud': 'aws',
                            'region': 'us-east-1'
                        }
                    }
                )
            
            self.index = self.pc.Index(index_name)
            self.initialized = True
            logger.info("Pinecone service initialized successfully")
            
        except Exception as e:
            logger.warning("Pinecone initialization failed - using fallback mode", error=str(e))
            self.initialized = False
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using sentence-transformers"""
        try:
            if not self.initialized or not self.embedding_model:
                return [0.0] * 384  # Match sentence-transformers dimension
            
            embedding = self.embedding_model.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.warning("Embedding generation failed", error=str(e))
            return [0.0] * 384
    
    def select_namespaces(self, query: str) -> List[str]:
        """Select relevant namespaces based on query"""
        query_lower = query.lower()
        namespaces = ["user_summary"]  # Always include user data
        
        # Simple keyword matching for the 5 namespaces
        if any(word in query_lower for word in ["health", "sick", "disease", "vet", "illness", "symptom"]):
            namespaces.append("health_data")
        
        if any(word in query_lower for word in ["food", "eat", "nutrition", "diet", "product", "toy", "buy"]):
            namespaces.append("product_data")
        
        if any(word in query_lower for word in ["bath", "groom", "brush", "clean", "hygiene", "care"]):
            namespaces.append("grooming_data")
        
        if any(word in query_lower for word in ["company", "help", "support", "service", "contact"]):
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
    
    async def upload_text_file(self, file_content: str, namespace: str, filename: str):
        """Upload text file content to specified namespace"""
        try:
            if not self.initialized or not self.index:
                raise Exception("Pinecone not initialized")
            
            # Split text into chunks (to avoid too large embeddings)
            chunks = self.split_text_into_chunks(file_content)
            
            vectors = []
            for i, chunk in enumerate(chunks):
                embedding = self.get_embedding(chunk)
                
                vectors.append({
                    "id": f"{filename}_{i}",
                    "values": embedding,
                    "metadata": {
                        "text": chunk,
                        "source": filename,
                        "type": "uploaded_file",
                        "chunk_index": i,
                        "namespace": namespace
                    }
                })
            
            # Upload to Pinecone
            self.index.upsert(vectors=vectors, namespace=namespace)
            
            logger.info(f"Uploaded {len(vectors)} chunks from {filename} to {namespace}")
            return {"success": True, "chunks": len(vectors)}
            
        except Exception as e:
            logger.error(f"Failed to upload file to Pinecone: {e}")
            return {"success": False, "error": str(e)}
    
    def split_text_into_chunks(self, text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """Split text into overlapping chunks"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)
        
        return chunks
    
    def is_ready(self) -> bool:
        """Check if Pinecone service is ready"""
        return self.initialized and self.index is not None

# Global instance
pinecone_service = PineconeService()