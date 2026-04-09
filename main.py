#!/bin/env python3
import os
import tempfile
import streamlit as st
from streamlit_chat import message
from rag import DevDocsCopilot

st.set_page_config(page_title="DevDocs Copilot")


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


def read_and_save_file():
    st.session_state["user_input"] = ""

    for file in st.session_state["file_uploader"]:
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

    # also remove from file uploader to prevent re-ingestion
    st.session_state["file_uploader"] = [
        f for f in st.session_state["file_uploader"] if f.name != file_name
    ]

    # if no files remain, reset the assistant state
    if not st.session_state["files"]:
        assistant.clear()
    else:
        assistant.retriever = assistant.vector_store.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"k": 2, "score_threshold": 0.5},
        )


def page():
    # ✅ initialize FIRST
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    if "assistant" not in st.session_state:
        st.session_state["assistant"] = DevDocsCopilot()

    if "files" not in st.session_state:
        st.session_state["files"] = set()

    st.header("DevDocs Copilot")

    st.subheader("Upload a document")
    st.file_uploader(
        "Upload document",
        type=["pdf"],
        key="file_uploader",
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
                st.session_state["to_delete"] = file

    # handle deletion after loop to avoid double-click
    if "to_delete" in st.session_state:
        delete_file(st.session_state["to_delete"])
        del st.session_state["to_delete"]


    user_input = st.chat_input("Message")
    if user_input:
        process_input(user_input)

    display_messages()


if __name__ == "__main__":
    page()