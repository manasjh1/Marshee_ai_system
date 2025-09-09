# app/upload_handler.py - New file for handling uploads
"""Handle file uploads and vectorization"""

from fastapi import UploadFile, HTTPException
from app.pinecone_service import pinecone_service
import structlog

logger = structlog.get_logger()

ALLOWED_NAMESPACES = [
    "health_data",
    "product_data", 
    "grooming_data",
    "company_data",
    "training_data",
    "custom_data"
]

async def handle_file_upload(file: UploadFile, namespace: str) -> dict:
    """Handle text file upload and vectorization"""
    
    # Validate namespace
    if namespace not in ALLOWED_NAMESPACES:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid namespace. Allowed: {ALLOWED_NAMESPACES}"
        )
    
    # Validate file type
    if not file.filename.endswith('.txt'):
        raise HTTPException(
            status_code=400,
            detail="Only .txt files are supported"
        )
    
    try:
        # Read file content
        content = await file.read()
        text_content = content.decode('utf-8')
        
        if not text_content.strip():
            raise HTTPException(status_code=400, detail="File is empty")
        
        # Upload to Pinecone
        result = await pinecone_service.upload_text_file(
            file_content=text_content,
            namespace=namespace,
            filename=file.filename
        )
        
        if result["success"]:
            logger.info(f"Successfully uploaded {file.filename} to {namespace}")
            return {
                "success": True,
                "message": f"File uploaded successfully to {namespace}",
                "filename": file.filename,
                "namespace": namespace,
                "chunks_created": result["chunks"]
            }
        else:
            raise HTTPException(status_code=500, detail=result["error"])
            
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be valid UTF-8 text")
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail="Upload failed")

def get_namespace_info() -> dict:
    """Get information about available namespaces"""
    return {
        "available_namespaces": ALLOWED_NAMESPACES,
        "descriptions": {
            "health_data": "Pet health information, symptoms, treatments, medical advice",
            "product_data": "Product recommendations, food, toys, supplies, reviews", 
            "grooming_data": "Grooming tips, care instructions, hygiene, maintenance",
            "company_data": "Company information, services, policies, support",
            "user_summary": "User profiles and pet information (auto-managed)"
        }
    }