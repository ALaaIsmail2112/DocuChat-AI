import uuid
import base64
from typing import List, Dict
from pathlib import Path
from unstructured.partition.pdf import partition_pdf
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import google.generativeai as genai
from app.config import settings
from app.core.exceptions import ProcessingError
# Add missing imports at the top
import asyncio
import base64
import os
import logging


logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self, document_id: str):
        self.document_id = document_id
        self.doc_folder = Path(settings.IMAGES_FOLDER) / document_id
        self.doc_folder.mkdir(exist_ok=True)
        
        # Initialize models
        self.setup_models()
        
        # Data storage
        self.chunks = None
        self.tables = []
        self.texts = []
        self.images = []
        self.image_descriptions = []
    
    def setup_models(self):
        """Initialize all required models"""
        try:
            # Groq model for text summarization
            self.groq_model = ChatGroq(
                temperature=0.3,
                model='llama-3.1-8b-instant',
                api_key=settings.GROQ_API_KEY
            )
            
            # Gemini model for image processing
            genai.configure(api_key=settings.GENAI_API_KEY)
            self.gemini_model = genai.GenerativeModel(model_name="gemini-1.5-flash")
            
            # Embeddings model
            self.embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-base-en")
            
            logger.info(f"Models initialized for document {self.document_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize models: {e}")
            raise ProcessingError(f"Model initialization failed: {e}", self.document_id)
    
    async def process_document(self, file_path: str) -> Dict[str,int]:
        """Main processing pipeline"""
        try:
            # Step 1: Extract content from PDF
            elements_count = await self.extract_pdf_content(file_path)
            
            # Step 2: Process images and save them
            await self.process_and_save_images()
            
            # Step 3: Create summaries
            await self.create_summaries()
            
            return elements_count
            
        except Exception as e:
            logger.error(f"Document processing failed for {self.document_id}: {e}")
            raise ProcessingError(f"Processing failed: {e}", self.document_id)
    
    async def extract_pdf_content(self, file_path: str) -> Dict[str, int]:
        """Extract content from PDF"""
        logger.info(f"Extracting content from {file_path}")
            # Initialize the table transformer model once

        self.chunks = partition_pdf(
            filename=file_path,
            infer_table_structure=True,
            strategy="hi_res",
            extract_image_block_types=['Image'],
            extract_image_block_to_payload=True,
            chunking_strategy='by_title',
            max_characters=4000,
            combine_text_under_n_chars=1000,
            new_after_n_chars=3000
        )
        
        # Separate elements
        self.tables = []
        self.texts = []
        
        for chunk in self.chunks:
            if 'Table' in str(type(chunk)):
                self.tables.append(chunk)
            elif 'CompositeElement' in str(type(chunk)):
                self.texts.append(chunk)
        
        # Extract images
        self.images = self._extract_images_base64()
        
        elements_count = {
            "texts": len(self.texts),
            "tables": len(self.tables),
            "images": len(self.images)
        }
        
        logger.info(f"Extracted elements: {elements_count}")
        return elements_count
    
    def _extract_images_base64(self) -> List[str]:
        """Extract base64 images from chunks"""
        images = []
        for chunk in self.chunks:
            if hasattr(chunk, 'metadata') and hasattr(chunk.metadata, 'orig_elements'):
                for el in chunk.metadata.orig_elements:
                    if 'Image' in str(type(el)) and hasattr(el.metadata, 'image_base64'):
                        images.append(el.metadata.image_base64)
        return images
    
    async def process_and_save_images(self):
        """Process images, save them to disk, and store metadata"""
        if not self.images:
            return

        logger.info(f"Processing {len(self.images)} images")
        
        # make metadata for each image 
        self.image_metadata = []

        for i, image_b64 in enumerate(self.images):
            try:
                #   create image description
                description = await self._describe_image(image_b64)
                self.image_descriptions.append(description)
                
                # create unique id for eacg image
                unique_id = uuid.uuid4().hex[:8]
                image_filename = f"image_{i+1}_{unique_id}.png"
                image_path = self.doc_folder / image_filename
                
                # save image in desktop
                image_data = base64.b64decode(image_b64)
                with open(image_path, 'wb') as f:
                    f.write(image_data)
                
                logger.info(f"Saved image: {image_path}")
                
                #  make metadata for each image 
                self.image_metadata.append({
                    "filename": image_filename,
                    "path": str(image_path),
                    "description": description,
                    "original_index": i,
                    "unique_id": unique_id  
                })
                
                # Rate limiting handle gemini request
                if (i + 1) % settings.MAX_IMAGES_PER_REQUEST == 0:
                    await asyncio.sleep(60)
                else:
                    await asyncio.sleep(settings.RATE_LIMIT_DELAY)
                    
            except Exception as e:
                logger.error(f"Error processing image {i+1}: {e}")
                self.image_descriptions.append(f"Error processing image: {e}")
                self.image_metadata.append({
                    "filename": None,
                    "path": None,
                    "description": f"Error processing image: {e}",
                    "original_index": i,
                    "unique_id": None
                })

    async def _describe_image(self, image_b64: str) -> str:
        """Generate description for image using Gemini"""
        try:
            prompt = """
            Analyze this image and provide a detailed description focusing on:
            - Any text, formulas, or equations visible
            - Diagrams, charts, or visual representations  
            - Technical concepts or processes shown
            - Key visual elements that convey information
            - Context that would help answer technical questions
            
            Be specific and comprehensive in your description.
            """
            
            response = self.gemini_model.generate_content([
                {"mime_type": "image/png", "data": image_b64},
                prompt
            ])
            
            return response.text if response.text else "No content detected in image"
            
        except Exception as e:
            logger.error(f"Error describing image: {e}")
            return f"Error processing image: {e}"
    
    async def create_summaries(self):
        """Create summaries for texts and tables"""
        # Create prompts
        self.text_prompt = ChatPromptTemplate.from_template("""
        You are an expert at summarizing technical content for retrieval systems.
        Create a comprehensive summary that includes:
        - Key concepts and definitions
        - Technical details and formulas
        - Important relationships and connections
        - Specific terminology that would help answer technical questions
        
        Focus on preserving information that would be valuable for question-answering.
        
        Content: {element}
        
        Summary:""")
        
        self.table_prompt = ChatPromptTemplate.from_template("""
        You are an expert at summarizing tables and structured data.
        Create a summary that includes:
        - What the table shows/represents
        - Key data points and patterns
        - Column headers and data types
        - Important numerical values or trends
        - Context for when this data would be relevant
        
        Table HTML: {element}
        
        Summary:""")
        
        # Create chains
        text_chain = self.text_prompt | self.groq_model | StrOutputParser()
        table_chain = self.table_prompt | self.groq_model | StrOutputParser()
        
        # Process texts
        if self.texts:
            text_content = [{"element": text.text} for text in self.texts]
            self.text_summaries = text_chain.batch(text_content, {'max_concurrency': 3})
        else:
            self.text_summaries = []
        
        # Process tables
        if self.tables:
            table_content = [{"element": table.metadata.text_as_html} for table in self.tables]
            self.table_summaries = table_chain.batch(table_content, {'max_concurrency': 3})
        else:
            self.table_summaries = []
        
        logger.info(f"Created {len(self.text_summaries)} text summaries and {len(self.table_summaries)} table summaries")
