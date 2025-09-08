# app/core/shared_store.py
from typing import Dict
from app.services.rag_service import RAGService

# Shared storage that can be imported by multiple modules
document_store: Dict[str, Dict] = {}
rag_services: Dict[str, RAGService] = {}