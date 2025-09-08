from fastapi import FastAPI
from fastapi.responses import  HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
from app.config import settings
from app.api import documents, queries
from app.core.database import init_database
from app.core.exceptions import setup_exception_handlers
from app.api import websocket_status


def create_application() -> FastAPI:
    """Create FastAPI application with all configurations"""
    
    app = FastAPI(
        title="Multi-Modal RAG API",
        description="Professional RAG system for multi-modal document processing",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc"
    )
    
    # Setup CORS   # to handle deploy with fronted as html and js 
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Setup exception handlers
    setup_exception_handlers(app)
    
    # Mount static files  # to handle request images from client we make this mount static files 
    app.mount("/images", StaticFiles(directory=settings.IMAGES_FOLDER), name="images")
    
    # Include routers
    app.include_router(websocket_status.router, prefix="/api/v1", tags=["websocket"])
    app.include_router(documents.router, prefix="/api/v1", tags=["Documents"])
    app.include_router(queries.router, prefix="/api/v1", tags=["Queries"])
    
    # Serve index.html at root path
    @app.get("/", response_class=HTMLResponse)
    async def read_root():
        # Check if index.html exists in current directory
        if os.path.exists("index.html"):
            with open("index.html", "r", encoding="utf-8") as f:
                return f.read()
        else:
            return """ sorry file index.html not found in your directory """
    
    # Initialize database on startup
    @app.on_event("startup")
    async def startup_event():
        await init_database()
    
    return app

app = create_application()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )