"""
auth.py
───────
User registration and login using JWT.

Storage layout (db/users.json):
  {
    "<email>": {
      "name":     "...",
      "password": "<bcrypt hash>"
    }
  }
"""

import json
import os

import bcrypt
from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token

_BACKEND_DIR = os.path.dirname(__file__)
_DB_DIR      = os.path.join(_BACKEND_DIR, "db")
_USERS_FILE  = os.path.join(_DB_DIR, "users.json")

auth_bp = Blueprint("auth", __name__)


# ── Internal helpers ──────────────────────────────────────────

def _read_users() -> dict:
    os.makedirs(_DB_DIR, exist_ok=True)
    if not os.path.exists(_USERS_FILE):
        return {}
    with open(_USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_users(data: dict):
    os.makedirs(_DB_DIR, exist_ok=True)
    with open(_USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Routes ────────────────────────────────────────────────────

@auth_bp.post("/api/auth/register")
def register():
    body     = request.get_json(force=True)
    name     = (body.get("name") or "").strip()
    email    = (body.get("email") or "").strip().lower()
    password = (body.get("password") or "").strip()

    if not name or not email or not password:
        return jsonify({"error": "name, email and password are required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    users = _read_users()
    if email in users:
        return jsonify({"error": "An account with this email already exists"}), 409

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    users[email] = {"name": name, "password": hashed}
    _write_users(users)

    # Issue token immediately so the user is logged in after registering
    token = create_access_token(identity=email)
    return jsonify({"token": token, "name": name, "email": email}), 201


@auth_bp.post("/api/auth/login")
def login():
    body     = request.get_json(force=True)
    email    = (body.get("email") or "").strip().lower()
    password = (body.get("password") or "").strip()

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    users = _read_users()
    user  = users.get(email)
    if not user or not bcrypt.checkpw(password.encode(), user["password"].encode()):
        return jsonify({"error": "Invalid email or password"}), 401

    token = create_access_token(identity=email)
    return jsonify({"token": token, "name": user["name"], "email": email})
