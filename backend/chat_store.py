"""
chat_store.py
─────────────
Persistent chat history using a single JSON file.

Storage layout (db/chats.json):
  {
    "<session_id>": {
      "<chat_id>": {
        "name":     "...",
        "messages": [{"role": "user"|"assistant", "content": "...", ...}, ...],
        "files":    ["{chat_id}::{file_name}", ...]
      }
    }
  }

session_id  – lightweight user/browser boundary (never touches ChromaDB)
chat_id     – logical conversation thread
files[]     – exact metadata.source values stored in ChromaDB
"""

import json
import os
import threading
import uuid

_BACKEND_DIR = os.path.dirname(__file__)
_DB_DIR      = os.path.join(_BACKEND_DIR, "db")
_CHATS_FILE  = os.path.join(_DB_DIR, "chats.json")
_lock        = threading.Lock()


# ── Internal helpers ──────────────────────────────────────────

def _read() -> dict:
    os.makedirs(_DB_DIR, exist_ok=True)
    if not os.path.exists(_CHATS_FILE):
        return {}
    with open(_CHATS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _write(data: dict):
    os.makedirs(_DB_DIR, exist_ok=True)
    with open(_CHATS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Public API ────────────────────────────────────────────────

def create_chat(session_id: str, name: str = "New chat") -> str:
    """Create a new chat and return its chat_id."""
    chat_id = str(uuid.uuid4())
    with _lock:
        data = _read()
        data.setdefault(session_id, {})[chat_id] = {
            "name":     name,
            "messages": [],
            "files":    [],
        }
        _write(data)
    return chat_id


def list_chats(session_id: str) -> list:
    """Return summary list [{id, name, message_count, file_count}] for a session."""
    with _lock:
        data = _read()
    chats = data.get(session_id, {})
    return [
        {
            "id":            cid,
            "name":          c.get("name", "New chat"),
            "message_count": len(c.get("messages", [])),
            "file_count":    len(c.get("files", [])),
        }
        for cid, c in chats.items()
    ]


def load_chat(session_id: str, chat_id: str) -> dict | None:
    """
    Return the full chat object, or None if it does not exist.
    Callers that need safe defaults should use: load_chat(...) or {}
    """
    with _lock:
        data = _read()
    return data.get(session_id, {}).get(chat_id)


def save_chat(session_id: str, chat_id: str, *,
              name: str = None, messages: list = None, files: list = None):
    """Partially update a chat. Only provided kwargs are written."""
    with _lock:
        data = _read()
        chat = data.setdefault(session_id, {}).setdefault(chat_id, {
            "name": "New chat", "messages": [], "files": []
        })
        if name     is not None: chat["name"]     = name
        if messages is not None: chat["messages"] = messages
        if files    is not None: chat["files"]    = files
        _write(data)


def delete_chat(session_id: str, chat_id: str):
    """Remove a chat from storage."""
    with _lock:
        data = _read()
        data.get(session_id, {}).pop(chat_id, None)
        _write(data)


def rename_chat(session_id: str, chat_id: str, name: str):
    """Convenience wrapper to rename a chat."""
    save_chat(session_id, chat_id, name=name)
