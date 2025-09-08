import uuid
import os
import base64
import re
from typing import List, Dict
from langchain_community.vectorstores import Qdrant
from langchain.storage import InMemoryStore
from langchain_core.documents import Document
from langchain.retrievers.multi_vector import MultiVectorRetriever
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from app.config import settings
from app.core.database import get_qdrant_client
from app.services.document_processor import DocumentProcessor
from app.models.schemas import QueryResponse, SourceInfo, ImageInfo
from app.core.exceptions import ProcessingError
from qdrant_client.models import Distance, VectorParams
import logging

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self, document_id: str, processor: DocumentProcessor):
        self.document_id = document_id
        self.processor = processor
        self.image_metadata = []

        self.setup_vectorstore()
        self.setup_rag_chain()

    def setup_vectorstore(self):
        try:
            client = get_qdrant_client()
            collection_name = f"doc_{self.document_id}"
            client.recreate_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE)
            )
            self.vectorstore = Qdrant(client=client, collection_name=collection_name, embeddings=self.processor.embeddings)
            self.store = InMemoryStore()
            self.id_key = 'doc_id'
            self.retriever = MultiVectorRetriever(vectorstore=self.vectorstore, docstore=self.store, id_key=self.id_key)
            logger.info(f"Vector store setup completed for {self.document_id}")
        except Exception as e:
            logger.error(f"Vector store setup failed: {e}")
            raise ProcessingError(f"Vector store setup failed: {e}", self.document_id)

    def build_vector_database(self):
        """Add text, table, image summaries safely"""
        try:
            # Text
            if self.processor.text_summaries:
                doc_ids = [str(uuid.uuid4()) for _ in self.processor.texts]
                summary_docs = [
                    Document(page_content=summary, metadata={self.id_key: doc_ids[i], "content_type": "text"})
                    for i, summary in enumerate(self.processor.text_summaries)
                ]
                self.retriever.vectorstore.add_documents(summary_docs)
                self.retriever.docstore.mset(list(zip(doc_ids, self.processor.texts)))

            # Table
            if self.processor.table_summaries:
                table_ids = [str(uuid.uuid4()) for _ in self.processor.tables]
                table_docs = [
                    Document(page_content=summary, metadata={self.id_key: table_ids[i], "content_type": "table"})
                    for i, summary in enumerate(self.processor.table_summaries)
                ]
                self.retriever.vectorstore.add_documents(table_docs)
                self.retriever.docstore.mset(list(zip(table_ids, self.processor.tables)))

            # Images - Enhanced handling
            if self.processor.image_descriptions and hasattr(self.processor, 'image_metadata'):
                img_ids = [str(uuid.uuid4()) for _ in self.processor.images]

                for i, desc in enumerate(self.processor.image_descriptions):
                    # Get image metadata
                    if i < len(self.processor.image_metadata):
                        image_meta = self.processor.image_metadata[i]
                        filename = image_meta.get("filename")
                        path = image_meta.get("path")
                        unique_id = image_meta.get("unique_id")
                    else:
                        unique_id = uuid.uuid4().hex[:8]
                        filename = f"image_{i+1}_{unique_id}.png"
                        path = str(self.processor.doc_folder / filename)

                    # Store local image metadata for retrieval
                    self.image_metadata.append({
                        "id": img_ids[i],
                        "filename": filename,
                        "description": desc,
                        "path": path,
                        "unique_id": unique_id,
                        "index": i
                    })

                    # Create document for vector store
                    img_doc = Document(
                        page_content=desc,
                        metadata={
                            self.id_key: img_ids[i],
                            "content_type": "image",
                            "filename": filename,
                            "path": path,
                            "description": desc,
                            "image_index": i,
                            "unique_id": unique_id
                        }
                    )
                    self.retriever.vectorstore.add_documents([img_doc])

                    # Store in docstore
                    self.retriever.docstore.mset([
                        (img_ids[i], {
                            "filename": filename,
                            "path": path,
                            "description": desc,
                            "image_index": i,
                            "unique_id": unique_id
                        })
                    ])

            logger.info(f"Vector database built successfully for {self.document_id}")
        except Exception as e:
            logger.error(f"Failed to build vector database: {e}")
            raise ProcessingError(f"Vector database build failed: {e}", self.document_id)

    def setup_rag_chain(self):
        self.rag_model = ChatGroq(model_name="llama-3.1-8b-instant", temperature=0.1, api_key=settings.GROQ_API_KEY)

    async def query(self, question: str, max_results: int = 5) -> QueryResponse:
        import time
        start_time = time.time()
        try:
            docs = self.retriever.invoke(question, k=max_results)
            parsed_docs = self._parse_documents(docs)
            context = self._build_context(parsed_docs)
            prompt = self._build_prompt(question, context)
            response = self.rag_model.invoke([HumanMessage(content=prompt)])
            answer = response.content
            
            # Get related images using improved method
            related_images = self._get_related_images(question, max_results)
            sources = self._build_sources(parsed_docs)
            processing_time = time.time() - start_time
            
            return QueryResponse(
                answer=answer,
                document_id=self.document_id,
                processing_time=processing_time,
                sources=sources,
                related_images=related_images
            )
        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise ProcessingError(f"Query failed: {e}", self.document_id)

    def _parse_documents(self, docs) -> Dict[str, List]:
        texts, tables, images = [], [], []
        for doc in docs:
            try:
                if isinstance(doc, str):
                    print('wooooooooooooooooooooooooo')
                    texts.append(doc)
                    continue
                if hasattr(doc, 'metadata'):
                    md = doc.metadata
                    ctype = md.get('content_type', 'text') if isinstance(md, dict) else 'text'
                    if ctype == 'text':
                        texts.append(doc)
                    elif ctype == 'table':
                        tables.append(doc)
                    elif ctype == 'image':
                        images.append(doc)
                    else:
                        texts.append(doc)
                else:
                    texts.append(doc)
            except Exception as e:
                logger.warning(f"Error parsing document: {e}")
                texts.append(doc)
        return {"texts": texts, "tables": tables, "images": images}

    def _extract_content(self, doc) -> str:
        """Safely extract content from different document types"""
        try:
            # For Document objects with page_content
            if hasattr(doc, 'page_content'):
                return str(doc.page_content)
            
            # For unstructured elements (CompositeElement, etc.)
            elif hasattr(doc, 'text'):
                return str(doc.text)
            
            # For elements with __str__ method
            elif hasattr(doc, '__str__'):
                return str(doc)
            
            # For tuples (description, image_data)
            elif isinstance(doc, (tuple, list)) and len(doc) >= 1:
                return str(doc[0])
            
            # Fallback
            else:
                print('zeroooooooooooooooooooooooo')
                return str(doc)
                
        except Exception as e:
            logger.warning(f"Error extracting content: {e}")
            return "Content extraction failed"

    def _build_context(self, parsed_docs: Dict[str, List]) -> str:
        parts = []
        if parsed_docs["texts"]:
            parts.append("**TEXT CONTEXT:**")
            for i, doc in enumerate(parsed_docs["texts"], 1):
                content = self._extract_content(doc)
                if len(content) > 1000:
                    content = content[:1000] + "..."
                parts.append(f"{i}. {content}")
            parts.append("")
        if parsed_docs["tables"]:
            parts.append("**TABLE CONTEXT:**")
            for i, doc in enumerate(parsed_docs["tables"], 1):
                content = self._extract_content(doc)
                if len(content) > 1000:
                    content = content[:1000] + "..."
                parts.append(f"{i}. {content}")
            parts.append("")
        if parsed_docs["images"]:
            parts.append("**IMAGE CONTEXT:**")
            for i, doc in enumerate(parsed_docs["images"], 1):
                if hasattr(doc, 'metadata') and isinstance(doc.metadata, dict):
                    description = doc.metadata.get('description', 'Image from document')
                else:
                    description = "Image contains relevant visual information"
                parts.append(f"{i}. {description}")
            parts.append("")
        return "\n".join(parts)

    def _build_prompt(self, question: str, context: str) -> str:
        return f"""You are an expert AI assistant that answers questions based on provided context from technical documents.

**CONTEXT:**
{context}

**QUESTION:** {question}

**ANSWER:**"""



    def _get_related_images(self, question: str, max_results: int = 5) -> List[ImageInfo]:
        """Retrieve related images directly from all_docs with Base64 encoding"""
        related_images = []

        try:
            # Get all documents
            all_docs = self.retriever.invoke(question, k=max_results * 2)  # extra to filter
            print('all_docs', all_docs)

            image_paths = []

            # Extract paths from dicts or strings using regex
            for doc in all_docs:
                if isinstance(doc, dict) and 'path' in doc:
                    image_paths.append(doc)
                elif isinstance(doc, str):
                    match = re.search(r"'path'\s*:\s*'([^']+)'", doc)
                    if match:
                        # create a pseudo-dict to unify later processing
                        image_paths.append({'path': match.group(1)})

            print(f"Found {len(image_paths)} potential image docs")

            # Process image paths
            for i, meta in enumerate(image_paths[:max_results]):
                filename = meta.get("filename", f"image_{i}.png")
                description = meta.get("description", "Related image from document")
                image_path = meta.get("path", None)

                image_base64 = None
                if image_path and os.path.exists(image_path):
                    with open(image_path, "rb") as f:
                        image_base64 = base64.b64encode(f.read()).decode("utf-8")

                related_images.append(
                    ImageInfo(
                        image_id=meta.get("unique_id", f"img_{i}"),
                        filename=filename,
                        path=image_path or "",
                        description=description,
                        image_base64=image_base64
                    )
                )

            print(f"Found {len(related_images)} related images", [img.image_id for img in related_images])
            return related_images

        except Exception as e:
            logger.error(f"Error retrieving related images: {e}")
            return []

    def _build_sources(self, parsed_docs: Dict[str, List]) -> List[SourceInfo]:
        sources = []
        for content_type, docs in parsed_docs.items():
            for doc in docs:
                try:
                    if isinstance(doc, str):
                        sources.append(SourceInfo(
                            content_type="text", 
                            content=doc[:500]+"..." if len(doc)>500 else doc, 
                            metadata={}
                        ))
                        continue
                    
                    content = self._extract_content(doc)
                    if len(content) > 500:
                        content = content[:500]+"..."
                    
                    md = {}
                    if hasattr(doc, 'metadata'):
                        md_obj = getattr(doc, 'metadata')
                        if isinstance(md_obj, dict):
                            md = self._serialize_metadata(md_obj)
                        elif hasattr(md_obj, '__dict__'):
                            md = self._serialize_metadata(md_obj.__dict__)
                        else:
                            md = {"metadata_type": str(type(md_obj))}
                    
                    sources.append(SourceInfo(
                        content_type=content_type, 
                        content=content, 
                        metadata=md
                    ))
                    
                except Exception as e:
                    logger.warning(f"Error building source for {content_type}: {e}")
                    continue
        return sources

    def _serialize_metadata(self, metadata_dict: Dict) -> Dict:
        """Convert metadata to serializable values"""
        serialized = {}
        for key, value in metadata_dict.items():
            try:
                if isinstance(value, list):
                    serialized_list = []
                    for item in value:
                        if hasattr(item, '__class__') and 'unstructured' in str(item.__class__):
                            if hasattr(item, 'text'):
                                serialized_list.append(str(item.text))
                            else:
                                serialized_list.append(str(item))
                        else:
                            serialized_list.append(item)
                    serialized[key] = serialized_list
                elif hasattr(value, '__class__') and 'unstructured' in str(value.__class__):
                    if hasattr(value, 'text'):
                        serialized[key] = str(value.text)
                    else:
                        serialized[key] = str(value)
                else:
                    serialized[key] = value
            except Exception as e:
                logger.warning(f"Error serializing metadata key {key}: {e}")
                serialized[key] = f"Unserializable: {type(value)}"
        
        return serialized