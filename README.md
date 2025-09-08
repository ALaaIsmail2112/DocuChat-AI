# 📄 DocuChat AI

**DocuChat AI** is an advanced, high-performance **Retrieval-Augmented Generation (RAG)** system designed to **maximize the value of your documents**. It goes far beyond traditional text analysis, leveraging a **sophisticated multi-modal architecture** to intelligently extract, interpret, and reason over both textual and visual content. Powered by **FastAPI** ⚡ for a fast and reliable backend, and **Qdrant** 🔍 for ultra-efficient vector search, DocuChat AI delivers **accurate, context-aware, and instant responses** directly from your documents. Whether it’s complex reports, images, or mixed media, this system ensures **trustworthy insights, real-time performance, and seamless document comprehension**.  

---

## ✨ Key Features

- 🧠 **Intelligent Document Processing**: Automatically partitions PDFs, extracting text, tables, and images for complete understanding.  
- 🏗️ **Robust RAG Architecture**: Uses a powerful **MultiVectorRetriever** to deliver context-aware answers, citing sources from the original document.  
- 🚀 **High-Performance API**: Built with **FastAPI** for document uploads, queries, and status tracking.  
- ⏳ **Asynchronous Background Processing**: Documents are processed in the background for smooth user experience.  
- 📡 **Real-time WebSocket Updates**: Instant updates on your document’s processing.  
- 🔒 **Efficient Data Management**: Documents and data are managed in isolated **Qdrant** collections, with simple API endpoints for permanent deletion.

---

## 🛠️ Workflow and Architecture

DocuChat AI follows a **streamlined, high-performance workflow**, from document upload to query response.

### 1️⃣ Document Upload
- Users upload PDF files to `POST /api/v1/document/upload`.  
- A unique `document_id` is generated, and metadata (filename, size, status) is stored in memory.  
- A **background task** begins processing to keep the API responsive.  

### 2️⃣ Document Processing
- **Partitioning**: Breaks the document into text, tables, and images using `unstructured.io`.  
- **Summarization & Description**:  
  - Text and tables are summarized via **Groq llama-3.1** ✨  
  - Images are converted to descriptive text using **Google Gemini Pro Vision** 🖼️  
- **Status Updates**: Real-time updates via **WebSocket** 🔄  

### 3️⃣ Vectorization and Storage
- **Vector Embeddings**: Extracted content is converted into numerical vectors using **Hugging Face** embeddings.  
- **Qdrant Vectorstore**: Vectors and metadata are stored in collections named by `document_id`.  
- **Multi-Vector Retrieval**: **LangChain MultiVectorRetriever** links dense vectors to full-text chunks for rich context.  

### 4️⃣ Query and Generation
- **Retrieval**: Queries sent to `POST /api/v1/query` are vectorized and searched in Qdrant. Relevant chunks are retrieved.  
- **Generation**: Retrieved chunks are provided as context to **Groq llama-3.1**.  
- **Answering**: Generates concise, accurate answers with source references and related images. ✅  

---

## ⚙️ Technologies Used

- **FastAPI** ⚡: High-performance web framework for the API  
- **Qdrant** 🔍: Efficient vector search engine  
- **Unstructured.io** 📝: Advanced document partitioning and extraction  
- **LangChain** 🔗: Orchestrates sophisticated RAG pipelines  
- **Groq** ⚡: High-speed LLM for summarization and answer generation  
- **Google AI Studio** 🖼️: Converts images to text  
- **WebSocket** 🔄: Real-time, bidirectional communication

---
## 🏛️ Architecture Diagram
  <img width="1024" height="682" alt="image" src="https://github.com/user-attachments/assets/e0b028b7-2f83-46a3-88d5-ba62d4f226af" />

---

