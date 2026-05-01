import os
import tempfile

from flask import Flask, jsonify, request
from flask_cors import CORS

from engine import get_engine, logger
from chat_store import (
    create_chat, list_chats, load_chat, save_chat,
    delete_chat, rename_chat,
)

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


# ── Chats ──────────────────────────────────────────────────────

@app.post("/api/chats")
def create_chat_route():
    body       = request.get_json(force=True)
    session_id = (body.get("session_id") or "").strip()
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400
    chat_id = create_chat(session_id)
    logger.info("CHAT  created  session=%s  chat=%s", session_id[:8], chat_id[:8])
    return jsonify({"chat_id": chat_id, "name": "New chat"}), 201


@app.get("/api/chats")
def list_chats_route():
    session_id = request.args.get("session_id", "").strip()
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400
    return jsonify({"chats": list_chats(session_id)})


@app.get("/api/chats/<chat_id>")
def load_chat_route(chat_id: str):
    session_id = request.args.get("session_id", "").strip()
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400
    chat = load_chat(session_id, chat_id)
    if chat is None:
        return jsonify({"error": "chat not found"}), 404
    return jsonify({"chat_id": chat_id, **chat})


@app.delete("/api/chats/<chat_id>")
def delete_chat_route(chat_id: str):
    session_id = request.args.get("session_id", "").strip()
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400
    # Purge all Chroma chunks for this chat before removing the record
    chat_data = load_chat(session_id, chat_id)
    if chat_data is None:
        return jsonify({"error": "chat not found"}), 404
    engine = get_engine()
    for prefixed in chat_data.get("files", []):
        clean = prefixed.split("::", 1)[-1] if "::" in prefixed else prefixed
        engine.delete_file(clean, chat_id)
    delete_chat(session_id, chat_id)
    return jsonify({"deleted": chat_id})


@app.patch("/api/chats/<chat_id>")
def rename_chat_route(chat_id: str):
    body       = request.get_json(force=True)
    session_id = (body.get("session_id") or "").strip()
    name       = (body.get("name") or "").strip()
    if not session_id or not name:
        return jsonify({"error": "session_id and name are required"}), 400
    rename_chat(session_id, chat_id, name)
    return jsonify({"chat_id": chat_id, "name": name})


# ── Chat (send message) ────────────────────────────────────────

@app.post("/api/chat")
def chat():
    body       = request.get_json(force=True)
    question   = (body.get("question") or "").strip()
    chat_id    = (body.get("chat_id") or "").strip()
    session_id = (body.get("session_id") or "").strip()

    if not question:
        return jsonify({"error": "question is required"}), 400
    if not chat_id or not session_id:
        return jsonify({"error": "chat_id and session_id are required"}), 400

    # Load from chat_store — backend is the source of truth for file filtering
    chat_data = load_chat(session_id, chat_id)
    if chat_data is None:
        return jsonify({"error": "chat not found"}), 404
    history_messages = chat_data.get("messages", [])
    allowed_files    = chat_data.get("files", [])

    engine = get_engine()
    result = engine.ask(question, chat_id, history_messages, allowed_files)

    # Persist updated history (append user + assistant turns)
    history_messages = list(history_messages)   # don't mutate the loaded list
    history_messages.append({"role": "user", "content": question})
    history_messages.append({
        "role":    "assistant",
        "content": result["answer"],
        "intent":  result["intent"],
        "sources": result["sources"],
    })
    save_chat(session_id, chat_id, messages=history_messages)

    return jsonify(result)


# ── Files ──────────────────────────────────────────────────────

@app.get("/api/files")
def list_files():
    chat_id    = request.args.get("chat_id", "").strip()
    session_id = request.args.get("session_id", "").strip()
    if not chat_id or not session_id:
        return jsonify({"error": "chat_id and session_id are required"}), 400
    # chat_store is the source of truth; no Chroma scan needed
    chat_data = load_chat(session_id, chat_id)
    if chat_data is None:
        return jsonify({"error": "chat not found"}), 404
    files = chat_data.get("files", [])
    return jsonify({"files": files})


@app.post("/api/files")
def upload_file():
    chat_id    = request.form.get("chat_id", "").strip()
    session_id = request.form.get("session_id", "").strip()
    if not chat_id or not session_id:
        return jsonify({"error": "chat_id and session_id are required"}), 400
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    f = request.files["file"]
    if f.filename == "":
        return jsonify({"error": "Empty filename"}), 400
    if not f.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are supported"}), 415

    engine = get_engine()

    prefixed = f"{chat_id}::{f.filename}"

    # Validate chat exists and check for duplicates BEFORE writing to disk
    chat_data = load_chat(session_id, chat_id)
    if chat_data is None:
        return jsonify({"error": "chat not found"}), 404
    files = list(chat_data.get("files", []))
    if prefixed in files:
        return jsonify({"error": f'"{f.filename}" is already uploaded in this chat'}), 409

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        f.save(tmp.name)
        tmp_path = tmp.name

    try:
        chunks = engine.ingest(tmp_path, f.filename, chat_id)
    finally:
        os.remove(tmp_path)

    # Record the file in this chat's file list (source of truth)
    files.append(prefixed)
    save_chat(session_id, chat_id, files=files)

    return jsonify({"file_name": prefixed, "chunks": chunks}), 201


@app.delete("/api/files/<path:file_name>")
def delete_file(file_name: str):
    chat_id    = request.args.get("chat_id", "").strip()
    session_id = request.args.get("session_id", "").strip()
    if not chat_id or not session_id:
        return jsonify({"error": "chat_id and session_id are required"}), 400

    # file_name from the URL may be the prefixed or clean name; normalise to clean
    clean = file_name.split("::", 1)[-1] if "::" in file_name else file_name
    prefixed = f"{chat_id}::{clean}"

    # Validate chat exists BEFORE mutating Chroma
    chat_data = load_chat(session_id, chat_id)
    if chat_data is None:
        return jsonify({"error": "chat not found"}), 404

    engine = get_engine()
    engine.delete_file(clean, chat_id)

    # Remove from chat's file list
    files = [f for f in chat_data.get("files", []) if f != prefixed]
    save_chat(session_id, chat_id, files=files)

    return jsonify({"deleted": prefixed, "remaining": files})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)