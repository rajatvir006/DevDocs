#!/bin/env python3
import json
import os
import tempfile
import streamlit as st
from rag import DevDocsCopilot

CHAT_HISTORY_FILE = "messages.json"

st.set_page_config(page_title="DevDocs Copilot")


def load_messages():
    if os.path.exists(CHAT_HISTORY_FILE):
        try:
            with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return [tuple(item) for item in data if isinstance(item, list) and len(item) == 2]
        except Exception:
            return []
    return []


def save_messages():
    with open(CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(list(st.session_state["messages"]), f, ensure_ascii=False, indent=2)


def display_messages():
    st.subheader("Chat")
    for msg, is_user in st.session_state["messages"]:
        with st.chat_message("user" if is_user else "assistant"):
            st.write(msg)


def process_input(query):
    if query and len(query.strip()) > 0:
        with st.spinner("Thinking"):
            agent_text = st.session_state["assistant"].ask(query)

        st.session_state["messages"].append((query, True))
        st.session_state["messages"].append((agent_text, False))
        save_messages()


def read_and_save_file():
    uploader_key = st.session_state.get("uploader_key", 0)
    uploader_state_key = f"file_uploader_{uploader_key}"

    for file in st.session_state[uploader_state_key]:
        if file.name in st.session_state["files"]:
            continue

        st.session_state["files"].add(file.name)

        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(file.getbuffer())
            file_path = tf.name

        with st.session_state["ingestion_spinner"], st.spinner(f"Ingesting {file.name}"):
            st.session_state["assistant"].ingest(file_path, file.name)

        os.remove(file_path)


def delete_file(file_name):
    assistant = st.session_state["assistant"]

    # delete using metadata filter
    if assistant.vector_store is not None:
        assistant.vector_store.delete(where={"source": file_name})

    # remove from tracking
    st.session_state["files"].discard(file_name)

    # clear uploader by changing its key
    st.session_state["uploader_key"] = st.session_state.get("uploader_key", 0) + 1

    # if no files remain, reset the assistant state
    if not st.session_state["files"]:
        assistant.clear()
    else:
        assistant._build_retriever_and_chain()


def page():
    # ✅ initialize FIRST
    if "messages" not in st.session_state:
        st.session_state["messages"] = load_messages()

    if "assistant" not in st.session_state:
        st.session_state["assistant"] = DevDocsCopilot()

    if "files" not in st.session_state:
        if st.session_state["assistant"].vector_store is not None:
            st.session_state["files"] = st.session_state["assistant"].get_source_files()
        else:
            st.session_state["files"] = set()

    if "uploader_key" not in st.session_state:
        st.session_state["uploader_key"] = 0

    st.header("DevDocs Copilot")

    uploader_key = st.session_state.get("uploader_key", 0)

    st.subheader("Upload a document")
    st.file_uploader(
        "Upload document",
        type=["pdf"],
        key=f"file_uploader_{uploader_key}",
        on_change=read_and_save_file,
        label_visibility="collapsed",
        accept_multiple_files=True,
    )

    st.session_state["ingestion_spinner"] = st.empty()

    # ✅ FILE LIST (correct placement)
    st.subheader("📄 Files in DB")

    for file in list(st.session_state["files"]):
        col1, col2 = st.columns([4, 1])

        with col1:
            st.write(file)

        with col2:
            if st.button("❌", key=f"delete_{file}"):
                delete_file(file)
                st.rerun()


    user_input = st.chat_input("Message")
    if user_input:
        process_input(user_input)

    display_messages()


if __name__ == "__main__":
    page()