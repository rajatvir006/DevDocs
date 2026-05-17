# DevDocs Copilot: RAG-based Document QA System

## Overview
DevDocs Copilot is a Retrieval-Augmented Generation (RAG) based chat system designed to answer user questions strictly based on uploaded PDF documents. It features a conversational interface, document isolation per chat session, and specialized handling for different types of user intents, including factual queries, summaries, and code extraction. The system enforces strict grounding rules to ensure zero hallucination outside of the provided documents, and uses the Groq API for fast, cloud-based LLM inference.

## Features
* **Document Ingestion:** Parses and chunks PDF documents into manageable segments.
* **Vector Search:** Uses local FastEmbed embeddings and ChromaDB for similarity-based retrieval.
* **Intent Classification:** Automatically categorizes user queries into specific intents (`general`, `specific`, `summarize`, `code`) to apply the most effective prompt.
* **Query Rewriting:** Detects follow-up questions and rewrites them into self-contained queries using chat history.
* **Strict Grounding:** Refuses to answer questions that cannot be supported by the uploaded document.
* **Raw Code Extraction:** Uses a fast-path bypass to return raw code blocks directly from context, preventing LLM syntax hallucinations.
* **Session Isolation:** Strict double-layer isolation (Chroma filter + Python post-filter) ensures no cross-chat data leakage.
* **Graceful Error Handling:** LLM API failures are caught and surfaced as clean user-facing messages rather than HTTP 500 crashes.

## Architecture & Data Flow
The system processes queries through a deterministic, multi-step pipeline:

1. **User Query:** The user submits a question.
2. **Follow-up Detection & Rewrite:** The system checks if the query relies on previous context (e.g., using pronouns like "it" or "that"). If so, it uses the chat history to rewrite the question into a fully self-contained query.
3. **Intent Classification:** The Groq LLM classifies the query into an actionable intent (`specific`, `summarize`, `code`, `general`). If classification fails due to an API error, it falls back to `general` safely.
4. **Retrieval:** The system queries ChromaDB using the rewritten query, filtering strictly by the documents uploaded in the current chat session.
5. **Context Assembly:** The retrieved document chunks are assembled into a context block and passed through a Python-level post-filter to guarantee isolation.
6. **Answer Generation:** Based on the classified intent, the context and question are passed to a prompt template to generate the final response via the Groq API. API errors return a graceful fallback message.

## Tech Stack
* **Backend Framework:** Flask, Python
* **LLM Orchestration:** LangChain
* **LLM Provider:** Groq API (`llama-3.3-70b-versatile`)
* **Vector Database:** ChromaDB (local persistence)
* **Embeddings:** FastEmbed — `bge-small-en-v1.5` (runs locally, no API key needed)
* **Document Parsing:** PyMuPDF
* **Environment Management:** python-dotenv

## Example Usage

**Query 1: Factual Retrieval**
* **User:** "What is a heap?"
* **System:** "A heap is a specialized tree-based data structure that satisfies the heap property."

**Query 2: Multi-Concept Reasoning**
* **User:** "Explain priority queue and its relation to heap"
* **System:** Structured Markdown response combining both concepts and their relationship, sourced from the document.

**Query 3: Out-of-Bounds Question**
* **User:** "What is the capital of France?"
* **System:** "I don't know based on the document."

**Query 4: Code Extraction**
* **User:** "Give code for heap implementation"
* **System:** Returns the raw Python code block directly extracted from the PDF chunk in ~2 seconds.

**Query 5: Code Follow-up**
* **User:** "Explain this code"
* **System:** Natural language explanation of the extracted code, grounded in the document context.

## Limitations
* **Vague Follow-ups:** Extremely short or vague queries ("tell me more about it") may fail retrieval if the similarity score falls below the threshold, returning "I don't know based on the document."
* **Truncated Code Extraction:** The chunking process can split long code blocks across chunk boundaries. The extraction bypass may return incomplete code if the full class spans multiple chunks.
* **Single-process Persistence:** The `chats.json` store uses a threading lock, which is safe for single-process use but would require a cross-process lock or SQLite under a multi-worker production server.

## Setup Instructions

1. **Clone the repository and set up a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure your Groq API Key:**
   Create a file named `.env` inside the `backend/` directory with the following content:
   ```env
   GROQ_API_KEY="your-groq-api-key-here"
   ```
   Get a free API key at [console.groq.com](https://console.groq.com). The `.env` file is listed in `.gitignore` and will never be committed.

4. **Run the backend:**
   ```bash
   cd backend
   python app.py
   ```
   The API will be available at `http://localhost:5000`.

5. **Run the frontend (optional):**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

> **For production deployments**, set `FLASK_DEBUG=false` (default) in your environment and use a WSGI server:
> ```bash
> pip install gunicorn
> gunicorn -w 1 -b 0.0.0.0:5000 app:app
> ```

Basic evaluation scripts are included under `/tests` to validate performance and conversational behavior.

## Future Improvements
* **Context-Aware Chunking:** Use a code-aware text splitter to prevent class/function definitions from being truncated across chunk boundaries during ingestion.
* **Cross-process Persistence:** Replace `chats.json` with SQLite or add a `filelock` for safe multi-worker deployments.
* **Rate Limit Retry Logic:** Add exponential backoff for Groq API `429 Too Many Requests` responses under heavy load.
