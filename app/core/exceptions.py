from fastapi import Request # HTTPException
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)
# ده بيخلق logger باسم الملف الحالي (__name__) عشان نقدر نسجل أي error أو warning ونرجع نعرف مصدره بسهولة.

class DocumentNotFoundError(Exception):
    def __init__(self, document_id: str):
        self.document_id = document_id
        super().__init__(f"Document {document_id} not found")

class ProcessingError(Exception):
    def __init__(self, message: str, document_id: str):
        self.message = message
        self.document_id = document_id
        super().__init__(message)

class InvalidFileError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

def setup_exception_handlers(app):
    @app.exception_handler(DocumentNotFoundError)
    async def document_not_found_handler(request: Request, exc: DocumentNotFoundError):
        return JSONResponse(
            status_code=404,
            content={"error": "Document not found", "document_id": exc.document_id}
        )
    
    @app.exception_handler(ProcessingError)
    async def processing_error_handler(request: Request, exc: ProcessingError):
        return JSONResponse(
            status_code=500,
            content={"error": exc.message, "document_id": exc.document_id}
        )
    
    @app.exception_handler(InvalidFileError)
    async def invalid_file_handler(request: Request, exc: InvalidFileError):
        return JSONResponse(
            status_code=400,
            content={"error": exc.message}
        )