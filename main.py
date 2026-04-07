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
        with st.spinner(f"Thinking"):
            agent_text = st.session_state["assistant"].ask(query)

        st.session_state["messages"].append((query, True))
        st.session_state["messages"].append((agent_text, False))


def read_and_save_file():
    st.session_state["assistant"].clear()
    st.session_state["messages"] = []
    st.session_state["user_input"] = ""

    for file in st.session_state["file_uploader"]:
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(file.getbuffer())
            file_path = tf.name

        with st.session_state["ingestion_spinner"], st.spinner(f"Ingesting {file.name}"):
            st.session_state["assistant"].ingest(file_path)
        os.remove(file_path)


def page():
    if len(st.session_state) == 0:
        st.session_state["messages"] = []
        st.session_state["assistant"] = DevDocsCopilot()
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

    user_input = st.chat_input("Message")
    if user_input:
        process_input(user_input)
    
    display_messages()


if __name__ == "__main__":
    page()
