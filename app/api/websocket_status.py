# app/api/websocket_status.py
from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from typing import Dict, List
import json
import asyncio
from app.api.documents import document_store
from app.models.schemas import ProcessingStatus
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Store active WebSocket connections
active_connections: Dict[str, List[WebSocket]] = {}

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, document_id: str):
        await websocket.accept()
        if document_id not in self.active_connections:
            self.active_connections[document_id] = []
        self.active_connections[document_id].append(websocket)
        logger.info(f"WebSocket connected for document {document_id}")

    def disconnect(self, websocket: WebSocket, document_id: str):
        if document_id in self.active_connections:
            if websocket in self.active_connections[document_id]:
                self.active_connections[document_id].remove(websocket)
            if not self.active_connections[document_id]:
                del self.active_connections[document_id]
        logger.info(f"WebSocket disconnected for document {document_id}")

    async def send_status_update(self, document_id: str, status_data: dict):
        if document_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[document_id]:
                try:
                    await connection.send_text(json.dumps(status_data))
                except:
                    disconnected.append(connection)
            
            # Clean up disconnected connections
            for conn in disconnected:
                self.active_connections[document_id].remove(conn)

manager = ConnectionManager()

@router.websocket("/ws/status/{document_id}")
async def websocket_endpoint(websocket: WebSocket, document_id: str):
    await manager.connect(websocket, document_id)
    
    try:
        # Send initial status
        if document_id in document_store:
            doc_info = document_store[document_id]
            initial_status = {
                "type": "status_update",
                "document_id": document_id,
                "status": doc_info["status"],
                "filename": doc_info["filename"],
                "upload_time": doc_info["upload_time"].isoformat() if doc_info["upload_time"] else None,
                "processing_time": doc_info.get("processing_time"),
                "elements_count": doc_info.get("elements_count")
            }
            await websocket.send_text(json.dumps(initial_status))
        
        # Keep connection alive and monitor status changes
        last_status = None
        while True:
            if document_id in document_store:
                current_status = document_store[document_id]["status"]
                if current_status != last_status:
                    doc_info = document_store[document_id]
                    status_update = {
                        "type": "status_change",
                        "document_id": document_id,
                        "status": current_status,
                        "filename": doc_info["filename"],
                        "processing_time": doc_info.get("processing_time"),
                        "elements_count": doc_info.get("elements_count"),
                        "message": get_status_message(current_status)
                    }
                    await websocket.send_text(json.dumps(status_update))
                    last_status = current_status
                    
                    # If completed or failed, send final message and close
                    if current_status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED]:
                        final_message = {
                            "type": "final_status",
                            "document_id": document_id,
                            "status": current_status,
                            "ready_for_queries": current_status == ProcessingStatus.COMPLETED
                        }
                        await websocket.send_text(json.dumps(final_message))
                        break
            
            await asyncio.sleep(2)  # Check every 2 seconds
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, document_id)
    except Exception as e:
        logger.error(f"WebSocket error for document {document_id}: {e}")
        manager.disconnect(websocket, document_id)

def get_status_message(status: ProcessingStatus) -> str:
    """Get user-friendly status message"""
    messages = {
        ProcessingStatus.PENDING: "Your document is queued for processing...",
        ProcessingStatus.PROCESSING: "Processing your document... This may take 1-2 minutes.",
        ProcessingStatus.COMPLETED: "✅ Processing complete! You can now ask questions about your document.",
        ProcessingStatus.FAILED: "❌ Processing failed. Please try uploading your document again."
    }
    return messages.get(status, "Status unknown")

# Helper function to broadcast status updates (call this from document processor)
async def broadcast_status_update(document_id: str):
    """Call this function when document status changes"""
    if document_id in document_store:
        doc_info = document_store[document_id]
        status_data = {
            "type": "status_update",
            "document_id": document_id,
            "status": doc_info["status"],
            "filename": doc_info["filename"],
            "processing_time": doc_info.get("processing_time"),
            "elements_count": doc_info.get("elements_count"),
            "message": get_status_message(doc_info["status"])
        }
        await manager.send_status_update(document_id, status_data)