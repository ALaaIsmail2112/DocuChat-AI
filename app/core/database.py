# app/core/database.py
import qdrant_client
from qdrant_client.models import Distance, VectorParams
from app.config import settings
import logging
from fastapi import HTTPException
logger = logging.getLogger(__name__)

class QdrantManager:
    def __init__(self):
        self.client = None
    
    async def connect(self):
        try:
            self.client = qdrant_client.QdrantClient(
                host=settings.QDRANT_HOST, 
                port=settings.QDRANT_PORT
            )
            logger.info("Connected to Qdrant successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise
    
    def create_collection(self, collection_name: str):
        try:
            self.client.recreate_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE)
            )
            logger.info(f"Collection {collection_name} created successfully")
        except Exception as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")
            raise

qdrant_manager = QdrantManager()

async def init_database():
    await qdrant_manager.connect()

def get_qdrant_client():
    if qdrant_manager.client is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    return qdrant_manager.client
