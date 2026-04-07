# DevDocs Copilot

![DevDocs Copilot](https://img.shields.io/badge/DevDocs-Copilot-blue?style=for-the-badge&logo=robot)

An AI-powered document assistant that enables intelligent question-answering based on uploaded PDF documents using Retrieval-Augmented Generation (RAG) technology.

## 🚀 Features

- **PDF Document Upload**: Seamlessly upload multiple PDF files for processing
- **Intelligent Q&A**: Ask questions and receive context-aware answers based solely on document content
- **Local AI Processing**: Runs entirely on your machine with Ollama and Phi3 model
- **Vector Embeddings**: FastEmbed for efficient document chunking and similarity search
- **ChromaDB Integration**: Persistent vector storage for document embeddings
- **Streamlit Interface**: Modern web-based chat interface for easy interaction

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

3. **Verify Ollama setup**:
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

3. **Upload PDF documents**:
   - Click the upload area
   - Select one or more PDF files
   - Wait for ingestion to complete

4. **Start chatting**:
   - Type your questions in the chat input
   - Receive answers based only on the uploaded documents

## 🏗️ Architecture

DevDocs Copilot uses a Retrieval-Augmented Generation (RAG) architecture:

1. **Document Ingestion**: PDFs are loaded using PyMuPDF and split into chunks
2. **Embedding Generation**: FastEmbed creates vector representations of text chunks
3. **Vector Storage**: ChromaDB stores and indexes the embeddings
4. **Retrieval**: Similarity search finds relevant document chunks for queries
5. **Generation**: Phi3 model generates answers using retrieved context
6. **Interface**: Streamlit provides the web-based chat interface

## 📁 Project Structure

```
devdocs/
├── main.py          # Main Streamlit application
├── rag.py           # RAG implementation with DevDocsCopilot class
├── pyproject.toml   # Project configuration and dependencies
└── README.md        # This file
```

## ⚙️ Configuration

- **Model**: Phi3 via Ollama (localhost:11434)
- **Chunk Size**: 400 characters with 50-character overlap
- **Retrieval**: Similarity score threshold of 0.5, top 2 results
- **Temperature**: 0 (deterministic responses)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

