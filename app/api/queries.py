# app/api/queries.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os
from app.config import settings
from app.models.schemas import QueryRequest, QueryResponse
from app.core.shared_store import rag_services, document_store
from app.core.exceptions import DocumentNotFoundError, ProcessingError
from app.models.schemas import ProcessingStatus
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/query", response_model=QueryResponse)
async def query_document(request: QueryRequest):
    """Query a processed document with professional status handling"""
    
    # Check if document exists
    if request.document_id not in document_store:
        raise DocumentNotFoundError(request.document_id)
    
    # Get document info
    doc_info = document_store[request.document_id]
    
    # Handle different processing states professionally
    if doc_info["status"] == ProcessingStatus.PENDING:
        return QueryResponse(
            answer="📋 Your document is currently queued for processing. Please wait a moment and try again.",
            document_id=request.document_id,
            processing_time=0.0,
            sources=[],
            related_images=[],
            confidence_score=0.0,
            status_info={
                "status": ProcessingStatus.PENDING,
                "message": "Document is queued for processing",
                "estimated_wait_time": "1-2 minutes"
            }
        )
    
    elif doc_info["status"] == ProcessingStatus.PROCESSING:
        return QueryResponse(
            answer="⚡ Your document is currently being processed. This usually takes 1-2 minutes depending on document complexity. Please try your query again in a moment.",
            document_id=request.document_id,
            processing_time=0.0,
            sources=[],
            related_images=[],
            confidence_score=0.0,
            status_info={
                "status": ProcessingStatus.PROCESSING,
                "message": "Document is being processed",
                "estimated_wait_time": "30-120 seconds"
            }
        )
    
    elif doc_info["status"] == ProcessingStatus.FAILED:
        return QueryResponse(
            answer="❌ Unfortunately, there was an error processing your document. Please try uploading the document again or contact support if the issue persists.",
            document_id=request.document_id,
            processing_time=0.0,
            sources=[],
            related_images=[],
            confidence_score=0.0,
            status_info={
                "status": ProcessingStatus.FAILED,
                "message": "Document processing failed",
                "action_required": "Re-upload document or contact support"
            }
        )
    
    # Document is completed - proceed with normal query
    if request.document_id not in rag_services:
        raise ProcessingError("RAG service not available", request.document_id)
    
    try:
        rag_service = rag_services[request.document_id]
        response = await rag_service.query(
            question=request.question,
            max_results=request.max_results or 5
        )
        
        # Add success status info
        response.status_info = {
            "status": ProcessingStatus.COMPLETED,
            "message": "Query completed successfully"
        }
        
        logger.info(f"Query processed successfully for document {request.document_id}")
        return response
        
    except Exception as e:
        logger.error(f"Query failed for document {request.document_id}: {e}")
        return QueryResponse(
            answer="🔧 There was a technical issue processing your query. Please try again or contact support if the problem continues.",
            document_id=request.document_id,
            processing_time=0.0,
            sources=[],
            related_images=[],
            confidence_score=0.0,
            status_info={
                "status": "error",
                "message": f"Query processing error: {str(e)}",
                "action_required": "Try again or contact support"
            }
        )

@router.get("/query-status/{document_id}")
async def get_query_readiness(document_id: str):
    """Check if document is ready for querying"""
    
    if document_id not in document_store:
        raise DocumentNotFoundError(document_id)
    
    doc_info = document_store[document_id]
    
    status_messages = {
        ProcessingStatus.PENDING: {
            "ready": False,
            "message": "Document is queued for processing",
            "estimated_wait": "1-2 minutes",
            "action": "Please wait and check again"
        },
        ProcessingStatus.PROCESSING: {
            "ready": False,
            "message": "Document is currently being processed",
            "estimated_wait": "30-120 seconds",
            "action": "Processing in progress, please wait"
        },
        ProcessingStatus.COMPLETED: {
            "ready": True,
            "message": "Document is ready for queries",
            "estimated_wait": "0 seconds",
            "action": "You can now ask questions about this document"
        },
        ProcessingStatus.FAILED: {
            "ready": False,
            "message": "Document processing failed",
            "estimated_wait": "N/A",
            "action": "Please re-upload the document"
        }
    }
    
    status_info = status_messages.get(doc_info["status"], {
        "ready": False,
        "message": "Unknown status",
        "estimated_wait": "Unknown",
        "action": "Please check document status"
    })
    
    return {
        "document_id": document_id,
        "status": doc_info["status"],
        "filename": doc_info["filename"],
        "upload_time": doc_info["upload_time"],
        "processing_time": doc_info.get("processing_time"),
        "elements_count": doc_info.get("elements_count"),
        **status_info
    }

# Alternative endpoint that takes document_id from URL path
@router.post("/query/{document_id}", response_model=QueryResponse)
async def query_document_by_path(document_id: str, request: QueryRequest):
    """Query a processed document with document_id in path"""
    request.document_id = document_id
    return await query_document(request)

@router.get("/image/{document_id}/{filename}")
async def get_image(document_id: str, filename: str):
    """Get an image file"""
    
    if document_id not in document_store:
        raise DocumentNotFoundError(document_id)
    
    image_path = os.path.join(settings.IMAGES_FOLDER, document_id, filename)
    
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image not found")
    
    return FileResponse(
        path=image_path,
        media_type="image/png",
        filename=filename
    )

@router.get("/document-images/{document_id}")
async def list_document_images(document_id: str):
    """List all images for a document"""
    
    if document_id not in document_store:
        raise DocumentNotFoundError(document_id)
    
    image_folder = os.path.join(settings.IMAGES_FOLDER, document_id)
    
    if not os.path.exists(image_folder):
        return {"images": []}
    
    images = []
    for filename in os.listdir(image_folder):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            images.append({
                "filename": filename,
                "url": f"/api/v1/image/{document_id}/{filename}"
            })
    
    return {"images": images}