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

## Project Tree Structure
```
PROJECT_ROOT/
│
├── app/
│
├── api/
│   ├── __init__.py
│   ├── documents.py
│   ├── queries.py
│   └── websocket_status.py
│
├── core/
│   ├── database.py
│   ├── exceptions.py
│   └── shared_store.py
│
├── models/
│   ├── __init__.py
│   └── schemas.py
│
├── services/
│   ├── __init__.py
│   ├── document_process...
│   └── rag_service.py
│
├── __init__.py
├── config.py
├── storage/
└── .env
```
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
## 📌 Key Benefits / Why Use DocuChat AI

DocuChat AI is designed to give you maximum value from your documents. Here’s why it stands out from other systems:

⚡ Real-Time Responses: Instant answers with live WebSocket updates while documents are being processed.

🧠 Multi-Modal Understanding: Extracts and reasons over both text and images, providing a complete understanding of your content.

🔍 Context-Aware Retrieval: Uses a powerful MultiVectorRetriever to deliver accurate, source-backed answers.

📚 Comprehensive Document Processing: Automatically handles PDFs, tables, and images, summarizing and interpreting all content.

🔒 Secure & Efficient: Isolated Qdrant collections, easy data management, and safe deletion of documents.

In short: DocuChat AI is not just a document reader—it’s an intelligent assistant that transforms documents into actionable knowledge.

---
##  🎬 Demo / Screenshots
<img width="1582" height="725" alt="image" src="https://github.com/user-attachments/assets/f4bf3e7c-649e-4b8c-9c34-5928d7ac92fd" />

<img width="1590" height="728" alt="image" src="https://github.com/user-attachments/assets/bccff1f2-57c2-4dc4-804b-5634d5015c7c" />
<img width="1607" height="737" alt="image" src="https://github.com/user-attachments/assets/78585cfa-0220-4e81-ad1e-99551ddb1164" />
<img width="1612" height="733" alt="image" src="https://github.com/user-attachments/assets/d3f2a41b-4157-4646-81ff-02b4347931b2" />
<img width="1537" height="713" alt="image" src="https://github.com/user-attachments/assets/50c7a197-68a1-42c9-a344-139be268ca08" />

---

## ❓ FAQ / Troubleshooting

Q1: My PDF file is too large, what should I do?
A: DocuChat AI handles large files by chunking them automatically. For extremely large PDFs, consider splitting them into smaller sections for faster processing.

Q2: Why is my query taking a long time to return?
A: Processing time depends on document size and complexity. Ensure your system resources are sufficient, or use asynchronous background processing for smooth performance.

Q3: Can I ask follow-up questions on the same document?
A: Absolutely! DocuChat AI supports context-aware follow-ups, maintaining the document context for more accurate answers.

Q4: Is my data safe?
A: Yes. All documents are stored in isolated Qdrant collections and can be permanently deleted via the API.


⭐ **If you're also learning multimodel RAG and Generative AI , feel free to explore the code and see the progression from basic concepts to a full-featured application!**

📧 **Questions or suggestions?** Feel free to open an issue or reach out!

## 📫 Contact

If you have any questions or want to collaborate, feel free to reach out to me:

- ✉️ **Email:** [alaaismailmohamed144@gmail.com](mailto:alaaismailmohamed144@gmail.com)  
- 🔗 **LinkedIn:** [Alaa Ismail](https://www.linkedin.com/in/alaa-ismail-b09493264)


