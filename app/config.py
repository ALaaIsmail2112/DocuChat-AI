import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # API Configuration
    DEBUG: bool = True
    HOST: str = "localhost"
    PORT: int = 8000
    
    # API Keys
    GROQ_API_KEY: str
    GENAI_API_KEY: str
    
    # Database
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    
    # Folders
    BASE_DIR: Path = Path(__file__).parent.parent
    UPLOAD_FOLDER: str = "storage/uploads"
    IMAGES_FOLDER: str = "storage/images"
    PROCESSED_DOCS_FOLDER: str = "storage/processed"
    TEMP_FOLDER: str = "storage/temp"
    
    # CORS
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # Processing limits
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    MAX_IMAGES_PER_REQUEST: int = 15
    RATE_LIMIT_DELAY: int = 4
    
    class Config:
        env_file = ".env"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create directories
        for folder in [self.UPLOAD_FOLDER, self.IMAGES_FOLDER, 
                      self.PROCESSED_DOCS_FOLDER, self.TEMP_FOLDER]:
            os.makedirs(folder, exist_ok=True)

settings = Settings()
