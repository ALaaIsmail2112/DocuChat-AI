# app/models/schemas.py
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    file_size: int
    upload_time: datetime
    status: ProcessingStatus

class ProcessingResponse(BaseModel):
    status: ProcessingStatus
    message: str
    document_id: str

class DocumentStatus(BaseModel):
    document_id: str
    status: ProcessingStatus
    filename: str
    upload_time: datetime
    processing_time: Optional[float] = None
    elements_count: Optional[Dict[str, int]] = None

class SourceInfo(BaseModel):
    content_type: str
    content: str
    metadata: Dict[str, Any]

class ImageInfo(BaseModel):
    image_id: str
    filename: str
    path: str
    description: str
    image_base64: Optional[str] = None

class StatusInfo(BaseModel):
    """Information about query processing status"""
    status: str
    message: str
    estimated_wait_time: Optional[str] = None
    action_required: Optional[str] = None

class QueryResponse(BaseModel):
    answer: str
    document_id: str
    processing_time: float
    sources: List[SourceInfo]
    related_images: List[ImageInfo]
    confidence_score: Optional[float] = None
    status_info: Optional[StatusInfo] = None  # New field for status information

class QueryRequest(BaseModel):
    document_id: str
    question: str
    max_results: Optional[int] = 5

class ProcessingStatusResponse(BaseModel):
    """Detailed response for document readiness status"""
    document_id: str
    status: ProcessingStatus
    filename: str
    upload_time: datetime
    processing_time: Optional[float]
    elements_count: Optional[Dict[str, int]]
    ready: bool
    message: str
    estimated_wait: str
    action: str