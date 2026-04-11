#!/bin/env python3
import json
import os
import tempfile
import streamlit as st
from rag import DevDocsCopilot

CHAT_HISTORY_FILE = "chats.json"

st.set_page_config(page_title="DevDocs Copilot")


def load_chats():
    if os.path.exists(CHAT_HISTORY_FILE):
        try:
            with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                chats = {}
                for name, messages in data.items():
                    if isinstance(messages, list):
                        chats[name] = [tuple(item) for item in messages if isinstance(item, list) and len(item) == 2]
                if chats:
                    return chats
        except Exception:
            pass
    return {"Default": []}


def save_chats():
    serializable = {
        name: [[msg, is_user] for msg, is_user in history]
        for name, history in st.session_state["chats"].items()
    }
    with open(CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2)


def get_current_chat_messages():
    current = st.session_state["current_chat"]
    return st.session_state["chats"].setdefault(current, [])


def add_chat(chat_name: str):
    chat_name = chat_name.strip()
    if not chat_name or chat_name in st.session_state["chats"]:
        return
    st.session_state["chats"][chat_name] = []
    st.session_state["current_chat"] = chat_name
    save_chats()


def create_chat():
    chat_name = st.session_state.get("new_chat_name", "").strip()
    if not chat_name:
        st.toast("Enter a chat name.")
        return
    if chat_name in st.session_state["chats"]:
        st.toast("That chat name already exists.")
        return
    add_chat(chat_name)
    st.session_state["clear_new_chat_name"] = True


def rename_chat(new_name: str):
    current = st.session_state["current_chat"]
    new_name = new_name.strip()
    if not new_name or new_name == current or new_name in st.session_state["chats"]:
        return

    st.session_state["chats"][new_name] = st.session_state["chats"].pop(current)
    st.session_state["current_chat"] = new_name
    save_chats()


def rename_current_chat():
    new_name = st.session_state.get("rename_chat_name", "").strip()
    if not new_name:
        st.toast("Enter a new chat name.")
        return
    current = st.session_state["current_chat"]
    if new_name == current:
        st.toast("This is already the current chat name.")
        return
    if new_name in st.session_state["chats"]:
        st.toast("That chat name already exists.")
        return
    rename_chat(new_name)
    st.session_state["clear_rename_chat_name"] = True


def delete_chat(chat_name: str):
    if chat_name not in st.session_state["chats"]:
        return

    st.session_state["chats"].pop(chat_name)
    if not st.session_state["chats"]:
        st.session_state["chats"]["Default"] = []
    st.session_state["current_chat"] = next(iter(st.session_state["chats"]))
    save_chats()


def clear_current_chat():
    current = st.session_state["current_chat"]
    if current not in st.session_state["chats"]:
        return

    if not st.session_state["chats"][current]:
        st.toast("Current chat is already cleared.")
        return

    st.session_state["chats"][current] = []
    save_chats()


def process_input(query):
    if not query or not query.strip():
        return

    with st.spinner("Thinking"):
        assistant_text = st.session_state["assistant"].ask(query)

    current_messages = get_current_chat_messages()
    current_messages.append((query, True))
    current_messages.append((assistant_text, False))
    save_chats()


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
    if "chats" not in st.session_state:
        st.session_state["chats"] = load_chats()
    if "current_chat" not in st.session_state:
        st.session_state["current_chat"] = next(iter(st.session_state["chats"]))
    if "new_chat_name" not in st.session_state:
        st.session_state["new_chat_name"] = ""
    if "rename_chat_name" not in st.session_state:
        st.session_state["rename_chat_name"] = ""
    if "clear_new_chat_name" not in st.session_state:
        st.session_state["clear_new_chat_name"] = False
    if "clear_rename_chat_name" not in st.session_state:
        st.session_state["clear_rename_chat_name"] = False
    if "assistant" not in st.session_state:
        st.session_state["assistant"] = DevDocsCopilot()
    if "files" not in st.session_state:
        if st.session_state["assistant"].vector_store is not None:
            st.session_state["files"] = st.session_state["assistant"].get_source_files()
        else:
            st.session_state["files"] = set()
    if "uploader_key" not in st.session_state:
        st.session_state["uploader_key"] = 0

    if st.session_state["clear_new_chat_name"]:
        st.session_state["new_chat_name"] = ""
        st.session_state["clear_new_chat_name"] = False

    if st.session_state["clear_rename_chat_name"]:
        st.session_state["rename_chat_name"] = ""
        st.session_state["clear_rename_chat_name"] = False

    with st.sidebar:
        st.header("Chats")
        chat_names = list(st.session_state["chats"].keys())
        selected_chat = st.selectbox(
            "Choose session",
            chat_names,
            index=chat_names.index(st.session_state["current_chat"]) if st.session_state["current_chat"] in chat_names else 0,
            key="chat_selector",
        )
        if selected_chat != st.session_state["current_chat"]:
            st.session_state["current_chat"] = selected_chat

        st.write("---")
        st.text_input(
            "New chat name",
            value=st.session_state["new_chat_name"],
            key="new_chat_name",
            placeholder="Type name and press Enter",
            on_change=create_chat,
        )

        if len(st.session_state["chats"]) > 1:
            st.button("🗑️ Delete chat", on_click=delete_chat, args=(st.session_state["current_chat"],))
        else:
            st.warning("Keep at least one chat.")

        st.button("🧹 Clear current chat", on_click=clear_current_chat)

        st.write("---")
        st.text_input(
            "Rename current chat",
            value=st.session_state["rename_chat_name"],
            key="rename_chat_name",
            placeholder="Type new name and press Enter",
            on_change=rename_current_chat,
        )

    st.header("DevDocs Copilot")
    st.subheader(f"Chat: {st.session_state['current_chat']}")

    st.subheader("Upload a document")
    uploader_key = st.session_state.get("uploader_key", 0)
    st.file_uploader(
        "Upload document",
        type=["pdf"],
        key=f"file_uploader_{uploader_key}",
        on_change=read_and_save_file,
        label_visibility="collapsed",
        accept_multiple_files=True,
    )

    st.session_state["ingestion_spinner"] = st.empty()

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

    for msg, is_user in get_current_chat_messages():
        with st.chat_message("user" if is_user else "assistant"):
            st.write(msg)


if __name__ == "__main__":
    page()