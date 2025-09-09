# data/setup_pinecone_data.py
"""Organized Pinecone data setup"""

import asyncio
from app.pinecone_service import pinecone_service
from data.sample_data import get_all_sample_data

async def setup_pinecone_data():
    """Setup all Pinecone data"""
    try:
        await pinecone_service.initialize()
        print("✅ Pinecone initialized")
        
        # Get organized sample data
        all_data = get_all_sample_data()
        
        # Upload data to each namespace
        for namespace, data in all_data.items():
            if data:  # Only if data exists
                await upload_namespace_data(namespace, data)
        
        print("\n🎉 All data uploaded successfully!")
        
        # Test search
        await test_search()
        
    except Exception as e:
        print(f"❌ Error: {e}")

async def upload_namespace_data(namespace: str, data: list):
    """Upload data to specific namespace"""
    try:
        # Convert to Pinecone format
        pinecone_data = []
        for item in data:
            pinecone_data.append({
                "id": item["id"],
                "text": item["content"],
                "type": item["type"],
                "source": item["source"],
                "extra_metadata": item.get("metadata", {})
            })
        
        # Upload using service
        embedding = pinecone_service.get_embedding(pinecone_data[0]["text"])
        
        vectors = []
        for item in pinecone_data:
            vectors.append({
                "id": item["id"],
                "values": pinecone_service.get_embedding(item["text"]),
                "metadata": {
                    "text": item["text"],
                    "type": item["type"],
                    "source": item["source"],
                    **item["extra_metadata"]
                }
            })
        
        # Upload in batches
        batch_size = 50
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            pinecone_service.index.upsert(vectors=batch, namespace=namespace)
        
        print(f"✅ Uploaded {len(vectors)} items to {namespace}")
        
    except Exception as e:
        print(f"❌ Failed to upload {namespace}: {e}")

async def test_search():
    """Test search functionality"""
    test_queries = [
        "My dog is not eating",
        "Best food for cats",
        "How to groom my pet",
        "Company services"
    ]
    
    print("\n🔍 Testing search...")
    for query in test_queries:
        context = await pinecone_service.get_context("test_user", query)
        total_results = sum(len(results) for results in context.values())
        print(f"Query: '{query}' → {total_results} results")

if __name__ == "__main__":
    asyncio.run(setup_pinecone_data())