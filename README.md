# DevDocs Copilot: RAG-based Document QA System

## Overview
DevDocs Copilot is a Retrieval-Augmented Generation (RAG) based chat system designed to answer user questions strictly based on uploaded PDF documents. It features user authentication, a conversational chat interface, document isolation per chat session, and specialized handling for different query types including factual queries, summaries, and code extraction. The system enforces strict grounding rules to ensure zero hallucination outside of the provided documents, and uses the Groq API for fast, cloud-based LLM inference.

## Features
* **User Authentication:** JWT-based register/login with bcrypt password hashing. Sessions persist across browser reloads.
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

1. **Auth Gate:** User registers or logs in. A JWT token is issued and stored client-side.
2. **User Query:** The authenticated user submits a question. The JWT is sent with every request.
3. **Follow-up Detection & Rewrite:** The system checks if the query relies on previous context. If so, it rewrites the question into a self-contained query.
4. **Intent Classification:** The Groq LLM classifies the query into an actionable intent. If classification fails, it falls back to `general` safely.
5. **Retrieval:** ChromaDB is queried using the rewritten query, filtering strictly by documents uploaded in the current chat session.
6. **Context Assembly:** Retrieved chunks are passed through a Python-level post-filter to guarantee isolation.
7. **Answer Generation:** The context and question are passed to a prompt template to generate the final response via Groq API.

## Tech Stack
* **Backend Framework:** Flask, Python
* **Authentication:** Flask-JWT-Extended + bcrypt
* **LLM Orchestration:** LangChain
* **LLM Provider:** Groq API (`llama-3.3-70b-versatile`)
* **Vector Database:** ChromaDB (local persistence)
* **Embeddings:** FastEmbed — `bge-small-en-v1.5` (runs locally, no API key needed)
* **Document Parsing:** PyMuPDF
* **Frontend:** React + Vite
* **Environment Management:** python-dotenv

## Example Usage

**Query 1: Factual Retrieval**
* **User:** "What is a heap?"
* **System:** "A heap is a specialized tree-based data structure that satisfies the heap property."

**Query 2: Multi-Concept Reasoning**
* **User:** "Explain priority queue and its relation to heap"
* **System:** Structured Markdown response combining both concepts and their relationship.

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
* **Vague Follow-ups:** Extremely short or vague queries ("tell me more about it") may fail retrieval if the similarity score falls below the threshold.
* **Truncated Code Extraction:** Long code blocks split across chunk boundaries may return incomplete code during raw extraction.
* **Single-process Persistence:** `chats.json` and `users.json` use a threading lock — safe for single-worker use but requires a cross-process lock or SQLite under multi-worker Gunicorn.

## Setup Instructions

1. **Clone the repository and set up a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```

2. **Install backend dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   Create a file named `.env` inside the `backend/` directory:
   ```env
   GROQ_API_KEY="your-groq-api-key-here"
   JWT_SECRET_KEY="any-long-random-secret-string"
   ```
   - Get a free Groq API key at [console.groq.com](https://console.groq.com)
   - Generate a JWT secret: `python -c "import secrets; print(secrets.token_hex(32))"`
   - The `.env` file is listed in `.gitignore` and will never be committed.

4. **Run the backend:**
   ```bash
   cd backend
   python app.py
   ```
   The API will be available at `http://localhost:5000`.

5. **Run the frontend:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   The UI will be available at `http://localhost:3000`.

> **For production deployments**, use a WSGI server and set `FLASK_DEBUG=false`:
> ```bash
> pip install gunicorn
> gunicorn -w 1 -b 0.0.0.0:5000 app:app
> ```

## Deployment Notes (Render / Railway / VPS)

| Item | Notes |
|---|---|
| Backend | Deploy `backend/` as a Python web service using `gunicorn -w 1 -b 0.0.0.0:$PORT app:app` |
| Frontend | Deploy `frontend/` as a static site; set API base URL to your backend's public URL |
| Environment variables | Set `GROQ_API_KEY`, `JWT_SECRET_KEY`, `FLASK_DEBUG=false` in the platform's env settings |
| Persistent storage | `db/` directory (ChromaDB + chats.json + users.json) must be on a persistent volume |
| CORS | Update `origins` in `app.py` from `"*"` to your frontend's deployed URL |

## Tests
Basic evaluation scripts are included under `/tests` to validate performance and conversational behavior:
```bash
# From project root
python tests/test_basic.py
python tests/test_behavior.py
python tests/test_performance.py
```

## Future Improvements
* **Context-Aware Chunking:** Use a code-aware text splitter to prevent class/function definitions from being truncated across chunk boundaries.
* **Cross-process Persistence:** Replace `chats.json` / `users.json` with SQLite for safe multi-worker deployments.
* **Rate Limit Retry Logic:** Add exponential backoff for Groq API `429 Too Many Requests` responses under heavy load.
* **Google OAuth:** Add "Sign in with Google" as an alternative to email/password auth.
