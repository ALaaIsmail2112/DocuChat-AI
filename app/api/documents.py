# app/api/documents.py
from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks
import os
import uuid
import shutil
from datetime import datetime
from app.config import settings
from app.models.schemas import *
from app.services.document_processor import DocumentProcessor
from app.services.rag_service import RAGService
from app.core.exceptions import InvalidFileError
from app.core.shared_store import document_store, rag_services
import time

import logging
logger = logging.getLogger(__name__)

router = APIRouter()


async def process_document_background(document_id: str):
    """Enhanced background task with status broadcasting"""

    start_time = time.time()
    
    try:
        doc_info = document_store[document_id]
        file_path = doc_info["file_path"]
        
        # Update status to processing
        document_store[document_id]["status"] = ProcessingStatus.PROCESSING
        
        # Import here to avoid circular import
        try:
            from app.api.websocket_status import broadcast_status_update
            await broadcast_status_update(document_id)
        except ImportError:
            pass  # WebSocket not available, continue without it
        
        logger.info(f"Started processing document {document_id}")
        
        # Initialize processor
        processor = DocumentProcessor(document_id)
        
        # Process document with progress updates
        logger.info(f"Extracting content from document {document_id}")
        elements_count = await processor.process_document(file_path)
        
        logger.info(f"Building vector database for document {document_id}")
        # Create RAG service
        rag_service = RAGService(document_id, processor)
        rag_service.build_vector_database()
        
        # Store RAG service
        rag_services[document_id] = rag_service
        
        # Update document status to completed
        processing_time = time.time() - start_time
        document_store[document_id].update({
            "status": ProcessingStatus.COMPLETED,
            "processing_time": processing_time,
            "elements_count": elements_count
        })
        
        # Broadcast completion
        try:
            from app.api.websocket_status import broadcast_status_update
            await broadcast_status_update(document_id)
        except ImportError:
            pass
        
        logger.info(f"Document {document_id} processed successfully in {processing_time:.2f}s")
        logger.info(f"Elements extracted: {elements_count}")
        
    except Exception as e:
        logger.error(f"Background processing failed for {document_id}: {e}")
        document_store[document_id]["status"] = ProcessingStatus.FAILED
        document_store[document_id]["error_message"] = str(e)
        
        # Broadcast failure
        try:
            from app.api.websocket_status import broadcast_status_update
            await broadcast_status_update(document_id)
        except ImportError:
            pass

@router.post("/upload-document", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload a PDF document for processing"""
    
    # Validate file
    if not file.filename.endswith('.pdf'):
        raise InvalidFileError("Only PDF files are allowed")
    
    if file.size > settings.MAX_FILE_SIZE:
        raise InvalidFileError(f"File too large. Max size: {settings.MAX_FILE_SIZE} bytes")
    
    # Generate document ID
    document_id = str(uuid.uuid4())
    
    # Save file
    file_path = os.path.join(settings.UPLOAD_FOLDER, f"{document_id}_{file.filename}")
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Store document info
        document_store[document_id] = {
            "filename": file.filename,
            "file_path": file_path,
            "file_size": file.size,
            "upload_time": datetime.now(),
            "status": ProcessingStatus.PENDING,
            "processing_time": None,
            "elements_count": None
        }
        
        logger.info(f"Document uploaded: {document_id} - {file.filename}")
        
        return DocumentUploadResponse(
            document_id=document_id,
            filename=file.filename,
            file_size=file.size,
            upload_time=datetime.now(),
            status=ProcessingStatus.PENDING
        )
        
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail="Upload failed")

@router.post("/process-document/{document_id}", response_model=ProcessingResponse)
async def process_document(document_id: str, background_tasks: BackgroundTasks):
    """Start processing a uploaded document"""
    
    if document_id not in document_store:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc_info = document_store[document_id]
    
    if doc_info["status"] == ProcessingStatus.PROCESSING:
        return ProcessingResponse(
            status=ProcessingStatus.PROCESSING,
            message="Document is already being processed. You'll be notified when it's ready.",
            document_id=document_id
        )
    
    if doc_info["status"] == ProcessingStatus.COMPLETED:
        return ProcessingResponse(
            status=ProcessingStatus.COMPLETED,
            message="Document has already been processed and is ready for queries.",
            document_id=document_id
        )
    
    # Start background processing
    background_tasks.add_task(process_document_background, document_id)
    
    # Update status
    document_store[document_id]["status"] = ProcessingStatus.PROCESSING
    
    return ProcessingResponse(
        status=ProcessingStatus.PROCESSING,
        message="Document processing has started. This usually takes 1-2 minutes. You can check the status or wait for completion notification.",
        document_id=document_id
    )

@router.get("/document-status/{document_id}", response_model=DocumentStatus)
async def get_document_status(document_id: str):
    """Get the processing status of a document"""
    
    if document_id not in document_store:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc_info = document_store[document_id]
    
    return DocumentStatus(
        document_id=document_id,
        status=doc_info["status"],
        filename=doc_info["filename"],
        upload_time=doc_info["upload_time"],
        processing_time=doc_info["processing_time"],
        elements_count=doc_info["elements_count"]
    )

@router.get("/documents", response_model=List[DocumentStatus])
async def list_documents():
    """List all uploaded documents"""
    
    documents = []
    for document_id, doc_info in document_store.items():
        documents.append(DocumentStatus(
            document_id=document_id,
            status=doc_info["status"],
            filename=doc_info["filename"],
            upload_time=doc_info["upload_time"],
            processing_time=doc_info["processing_time"],
            elements_count=doc_info["elements_count"]
        ))
    
    return documents

@router.post("/query/{document_id}", response_model=QueryResponse)
async def query_document(document_id: str, query_request: QueryRequest):
    """Query a processed document"""
    
    # Check if document exists
    if document_id not in document_store:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check if document is processed
    if document_store[document_id]["status"] != ProcessingStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Document is not processed yet")
    
    # Check if RAG service exists
    if document_id not in rag_services:
        raise HTTPException(status_code=500, detail="RAG service not found for this document")
    
    try:
        rag_service = rag_services[document_id]
        response = await rag_service.query(
            question=query_request.question,
            max_results=query_request.max_results
        )
        
        logger.info(f"Query processed for document {document_id}: {query_request.question}")
        return response
        
    except Exception as e:
        logger.error(f"Query failed for document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@router.delete("/document/{document_id}")
async def delete_document(document_id: str):
    """Delete a document and its associated data"""
    
    if document_id not in document_store:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        # Remove files
        doc_info = document_store[document_id]
        if os.path.exists(doc_info["file_path"]):
            os.remove(doc_info["file_path"])
        
        # Remove image folder
        image_folder = os.path.join(settings.IMAGES_FOLDER, document_id)
        if os.path.exists(image_folder):
            shutil.rmtree(image_folder)
        
        # Remove from storage
        del document_store[document_id]
        if document_id in rag_services:
            del rag_services[document_id]
        
        logger.info(f"Document {document_id} deleted successfully")
        
        return {"message": "Document deleted successfully"}
        
    except Exception as e:
        logger.error(f"Failed to delete document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete document")