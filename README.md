# DevDocs Copilot: RAG-based Document QA System

## Overview
DevDocs Copilot is a Retrieval-Augmented Generation (RAG) based chat system designed to answer user questions strictly based on uploaded PDF documents. It features a conversational interface, document isolation per chat session, and specialized handling for different types of user intents, including factual queries, summaries, and code extraction. The system is designed with strict grounding rules to ensure zero hallucination outside of the provided documents.

## Features
* **Document Ingestion:** Parses and chunks PDF documents into manageable segments.
* **Vector Search:** Uses embeddings and similarity search to retrieve relevant context.
* **Intent Classification:** Automatically categorizes user queries into specific intents (general, specific, summarize, code) to apply the most effective prompt.
* **Query Rewriting:** Detects follow-up questions and rewrites them into self-contained queries using chat history.
* **Strict Grounding:** Refuses to answer questions that cannot be supported by the uploaded document.
* **Raw Code Extraction:** Uses a fast-path bypass to return raw, unformatted code blocks directly from the context, preventing LLM syntax hallucinations.
* **Session Isolation:** Strict boundaries ensure users cannot cross-pollinate context or leak data between different chat sessions.

## Architecture & Data Flow
The system processes queries through a deterministic, multi-step pipeline:

1. **User Query:** The user submits a question.
2. **Follow-up Detection & Rewrite:** The system checks if the query relies on previous context (e.g., using pronouns). If so, it uses the chat history to rewrite the question into a self-contained query.
3. **Intent Classification:** An LLM classifies the query into an actionable intent (`specific`, `summarize`, `code`, `general`).
4. **Retrieval:** The system queries the vector database using the rewritten query, filtering strictly by the documents uploaded in the current chat session.
5. **Context Assembly:** The retrieved document chunks are assembled into a context block.
6. **Answer Generation:** Based on the classified intent, the context and question are passed to a specific prompt template to generate the final response.

## Tech Stack
* **Backend Framework:** Flask, Python
* **LLM Orchestration:** LangChain
* **Vector Database:** ChromaDB
* **Embeddings:** FastEmbed (Local)
* **LLM Provider:** Ollama (Local models)
* **Document Parsing:** PyMuPDF

## Example Usage

**Query 1: Factual Retrieval**
* **User:** "What is a heap?"
* **System:** "A heap is a specialized tree-based data structure that satisfies the heap property where for any given node C, if P is its parent node, then key(P) >= key(C)."

**Query 2: Multi-Concept Reasoning**
* **User:** "Explain priority queue and its relation to heap"
* **System:** "A Priority Queue is a specialized queue where each element has a priority associated with it. It is often implemented using heaps, which allow for efficient priority-based operations like insertion and extraction of the maximum or minimum element due to their structure."

**Query 3: Out-of-Bounds Question**
* **User:** "What is the capital of France?"
* **System:** "I don't know based on the document."

**Query 4: Code Extraction**
* **User:** "Give code for heap implementation"
* **System:** Returns the raw Python code block directly extracted from the PDF chunk.

## Limitations
* **Conversational Memory:** The system occasionally struggles to resolve vague pronouns ("it", "that") and overly brief queries ("why?", "what about that?"), leading to context loss or generic fallback responses.
* **Code Explanations:** The intent classifier treats queries like "Explain this code" as requests to *extract* code rather than explain it. This triggers the raw bypass and returns fragmented text instead of an LLM-generated explanation.
* **Truncated Code Extraction:** The document chunking process can split long code blocks. If a code block spans multiple chunks, the raw extraction bypass may return incomplete code.

## Setup Instructions

1. **Clone the repository and set up a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: .\venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the local LLM server:**
   Ensure Ollama is installed and running locally on port 11434. Pull your desired model (e.g., `phi3` or `llama3`).

4. **Run the application:**
   ```bash
   cd backend
   python app.py
   ```
   The API will be available at `http://localhost:5000`.

Basic evaluation scripts are included under `/tests` to validate performance and conversational behavior.

## Future Improvements
* **Refine the Intent Classifier:** Adjust prompts to properly differentiate between requests to *extract* code and requests to *explain* code.
* **Context-Aware Chunking:** Implement code-aware text splitters to prevent syntax blocks from being truncated across chunk boundaries during ingestion.
* **Enhanced Query Rewriting:** Improve the chat history formatter to provide richer context to the rewriting LLM, preventing context loss on vague follow-ups.
