# DevDocs Copilot

![DevDocs Copilot](https://img.shields.io/badge/DevDocs-Copilot-blue?style=for-the-badge&logo=robot)

An AI-powered document assistant that enables intelligent question-answering based on uploaded PDF documents using Retrieval-Augmented Generation (RAG) technology. Built with LangChain, ChromaDB, and Streamlit for a seamless local-first experience.

## 🚀 Features

- **Multi-Session Chat**: Create, rename, and manage multiple independent chat sessions
- **PDF Document Upload**: Upload multiple PDF files for processing and querying
- **Intelligent Q&A**: Ask questions and receive answers based exclusively on document content
- **Document Management**: View, track, and delete uploaded documents
- **Persistent Storage**: Chat history and embeddings are automatically saved between sessions
- **Local AI Processing**: Runs entirely on your machine with Ollama and Phi3 model
- **Vector Embeddings**: FastEmbed for efficient document chunking and similarity search
- **ChromaDB Integration**: Persistent vector database for fast retrieval

## 🛠️ Tech Stack

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit)
![LangChain](https://img.shields.io/badge/LangChain-1.2+-1C3C3C?style=flat&logo=chainlink)
![ChromaDB](https://img.shields.io/badge/ChromaDB-1.5+-000000?style=flat&logo=chroma)
![Ollama](https://img.shields.io/badge/Ollama-Phi3-000000?style=flat&logo=ollama)
![FastEmbed](https://img.shields.io/badge/FastEmbed-0.8+-FF6B35?style=flat&logo=embed)

## 📋 Prerequisites

- Python 3.12 or higher
- [Ollama](https://ollama.ai/) installed and running locally
- Phi3 model pulled in Ollama (`ollama pull phi3`)

## 🔧 Installation

1. **Clone the repository** (if applicable) or ensure you're in the project directory

2. **Install dependencies using uv**:
   ```bash
   uv pip install -e .
   ```

3. **Verify Ollama is running**:
   ```bash
   ollama serve
   ollama pull phi3
   ```

## 📖 Usage

1. **Start the application**:
   ```bash
   streamlit run main.py
   ```

2. **Open your browser** to the provided local URL (typically http://localhost:8501)

3. **Manage Chat Sessions** (Sidebar):
   - Select an existing chat from the dropdown or create a new one
   - Rename the current chat session
   - Delete a chat session (must keep at least one)
   - Clear all messages in the current chat
   - All conversations auto-save to `chats.json`

4. **Upload PDF Documents**:
   - Click the upload area in the main panel
   - Select one or more PDF files
   - Files are processed and indexed for searching
   - Uploaded files are tracked and can be deleted later

5. **Ask Questions**:
   - Type your questions in the input area
   - The assistant searches relevant document chunks
   - Answers are based exclusively on document content
   - Questions shorter than 3 characters are rejected

6. **Manage Documents**:
   - Uploaded documents are displayed in the session
   - Delete documents to remove them from the knowledge base
   - Deleted documents are removed from ChromaDB

## 🏗️ Architecture

### RAG Pipeline

DevDocs Copilot implements a complete Retrieval-Augmented Generation pipeline:

1. **Document Ingestion** (`ingest` method):
   - Load PDFs using PyMuPDFLoader
   - Extract and clean document text
   - Filter complex metadata entries

2. **Text Chunking**:
   - Split documents into 400-character chunks
   - 50-character overlap between chunks for context continuity
   - Preserve metadata (source file information)

3. **Embedding & Storage**:
   - Generate embeddings using FastEmbed
   - Store in ChromaDB with source metadata
   - Persistent storage in `db/` directory

4. **Retrieval**:
   - Similarity search with threshold of 0.5
   - Return top 2 most relevant chunks
   - Source tracking for document attribution

5. **Answer Generation**:
   - Use Phi3 model (via Ollama)
   - Context-based prompt with strict instructions
   - Deterministic output (temperature = 0)
   - Always responds based on context only

### UI Components

- **Sidebar**: Chat session management and controls
- **Main Panel**: Current chat display, document uploads, query input
- **Session State**: Manages chats, file tracking, UI state using Streamlit's session_state

## 📁 Project Structure

```
devdocs/
├── main.py              # Streamlit application with UI and session management
├── rag.py               # RAG pipeline (DevDocsCopilot class)
├── pyproject.toml       # Project configuration and dependencies
├── chats.json          # Persistent chat history (auto-generated)
├── db/                 # ChromaDB vector store (auto-generated)
└── README.md           # This file
```

## ⚙️ Configuration

### RAG Parameters

- **Model**: Phi3 via Ollama (`http://localhost:11434`)
- **Chunk Size**: 400 characters
- **Chunk Overlap**: 50 characters
- **Retrieval Type**: Similarity score threshold
- **Similarity Threshold**: 0.5
- **Top K Results**: 2
- **Temperature**: 0 (deterministic)

### File Locations

- **Chat History**: `chats.json`
- **Vector Database**: `db/`
- **Temp Files**: System temp directory (cleaned up after upload)

## 🔄 Session Management

- **Chat Sessions**: Independent conversation threads with unique names
- **Session State**: Persisted across Streamlit reruns using `st.session_state`
- **Chat Persistence**: All messages saved to `chats.json` automatically
- **File Tracking**: Uploaded files tracked in memory with source metadata in ChromaDB

## 💡 Key Implementation Details

### Multi-Session Support

- Chat sessions are stored in a dictionary with names as keys
- Each session maintains its own message history
- Switch between sessions with the dropdown selector
- Sessions persist even after app restart

### Document Tracking

- Uploaded files are tracked in a set-based structure
- Metadata includes original filename for deletion
- When a document is deleted, all embeddings with matching source are removed
- ChromaDB deletion uses metadata filtering

### Prompt Engineering

The assistant uses a strict prompt template that:
- Enforces document-only answers
- Rejects queries shorter than 3 characters
- Returns "I don't know based on the document." when context doesn't contain the answer
- Prioritizes phrases directly from documents

## 📖 Usage Examples

### Creating a New Chat
1. Go to sidebar
2. Enter a name in "New chat name" field
3. Press Enter
4. Chat is created and activated

### Uploading Documents
1. Click the upload area
2. Select PDF files
3. Wait for ingestion to complete
4. Files appear in the tracking system

### Querying with Context
1. Upload relevant documents
2. Ask specific questions related to document content
3. Receive answers with document-based context
4. View multiple chat sessions for different topics

## 🎓 Learning Outcomes

From building this project:
- Implementing RAG pipelines with LangChain
- Efficient vector search with ChromaDB
- Streamlit session state management for complex UIs
- LLM prompt engineering for consistency
- PDF processing and text chunking strategies
- Building multi-session applications with persistent state

## 🤝 Contributing

Contributions are welcome! Feel free to submit issues or pull requests.

## 📝 License

This project is open source and available under the MIT License.


