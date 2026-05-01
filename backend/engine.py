import os
import re
import logging
from typing import Optional

import yaml

try:
    from langchain_chroma import Chroma
except ImportError:
    from langchain_community.vectorstores import Chroma

from langchain_ollama import ChatOllama
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
from langchain_core.prompts import PromptTemplate
from langchain_community.vectorstores.utils import filter_complex_metadata

# ── Logging ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("devdocs")
_log_file = os.path.join(os.path.dirname(__file__), "classification.log")
_fh = logging.FileHandler(_log_file, encoding="utf-8")
_fh.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s", "%Y-%m-%d %H:%M:%S"))
logger.addHandler(_fh)

# ── Config ────────────────────────────────────────────────────
_BACKEND_DIR = os.path.dirname(__file__)

def _load_yaml(filename):
    with open(os.path.join(_BACKEND_DIR, filename), "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

CONFIG  = _load_yaml("config.yaml")
PROMPTS = _load_yaml("prompts.yaml")

# ── Prompt builders ───────────────────────────────────────────
def _render_classifier_shots(shots):
    return "\n".join(
        f"  {i}. Query : \"{ex['user']}\"\n     Label : {ex['label']}"
        for i, ex in enumerate(shots, 1)
    )

def _render_answer_shots(shots):
    blocks = []
    for i, ex in enumerate(shots, 1):
        ctx = ex.get("context", "").strip() or "(no context needed)"
        a   = ex.get("answer", "").strip()
        blocks.append(
            f"  Example {i}\n  Context  : {ctx}\n  Question : {ex.get('question','').strip()}\n  Answer   :\n"
            + "\n".join(f"    {l}" for l in a.splitlines())
        )
    return "\n\n".join(blocks)

def _build_classifier_prompt():
    cfg = PROMPTS["classifier"]
    return (
        cfg["system"].rstrip()
        + "\n\n── FEW-SHOT EXAMPLES ────────────────────────────────────\n"
        + _render_classifier_shots(cfg.get("few_shots", []))
        + "\n─────────────────────────────────────────────────────────\n\nQuery: {question}"
    )

def _build_answer_prompt(intent):
    p = PROMPTS["prompts"][intent]
    return (
        p["template"]
        .replace("{system}", p["system"].rstrip())
        .replace("{few_shots}", _render_answer_shots(p.get("few_shots", [])))
    )

_ANSWER_PROMPTS = {
    intent: PromptTemplate.from_template(_build_answer_prompt(intent))
    for intent in PROMPTS["prompts"]
}
_CLASSIFIER_PROMPT = PromptTemplate.from_template(_build_classifier_prompt())

# ── History formatter (accepts plain list of message dicts) ───
def _format_history(messages: list) -> str:
    max_turns = CONFIG.get("history", {}).get("max_turns", 6)
    msgs = messages[-(max_turns * 2):]
    if not msgs:
        return "No previous conversation."
    lines = ["Conversation so far:"]
    for msg in msgs:
        if msg.get("role") == "user":
            content = msg.get("content", "").strip()
            lines.append(f"- User: {content}")
    return "\n".join(lines)

# ── PDF ingestion ─────────────────────────────────────────────
HEADERS_TO_SPLIT = [("#","H1"),("##","H2"),("###","H3"),("####","H4")]

def _pdf_to_chunks(pdf_path: str, prefixed_source: str) -> list:
    """
    Load a PDF and split into chunks.
    prefixed_source is stored verbatim in metadata.source = "{chat_id}::{file_name}"
    """
    raw_docs  = PyMuPDFLoader(file_path=pdf_path).load()
    full_text = "".join(f"\n## Page {i+1}\n\n{doc.page_content}\n" for i, doc in enumerate(raw_docs))
    md_chunks = MarkdownHeaderTextSplitter(
        headers_to_split_on=HEADERS_TO_SPLIT, strip_headers=False
    ).split_text(full_text)
    chunk_cfg = CONFIG.get("chunking", {})
    chunks = RecursiveCharacterTextSplitter(
        chunk_size=chunk_cfg.get("chunk_size", 800),
        chunk_overlap=chunk_cfg.get("chunk_overlap", 80),
    ).split_documents(md_chunks)
    for c in chunks:
        c.metadata["source"] = prefixed_source
    return filter_complex_metadata(chunks)

FOLLOWUP_PROMPT = """
You are a classifier.

Decide whether the user's latest question is a FOLLOW-UP to the previous conversation.

A question is a FOLLOW-UP if:

* It depends on previous context
* It uses vague references like "it", "that", "this"
* It is incomplete alone ("why", "how", "tell more")

A question is NOT a follow-up if:

* It is self-contained
* It introduces a new topic

Return ONLY one word:
YES or NO

Conversation:
{history}

Question:
{question}

Answer:
"""

# ── Single shared engine ──────────────────────────────────────
class DocCopilotEngine:
    """
    Singleton engine backed by ONE shared Chroma collection.
    session_id is NEVER passed into Chroma — it is a user-boundary concern only.
    All file isolation uses metadata.source = "{chat_id}::{file_name}".
    """

    def __init__(self):
        self.persist_dir = os.path.join(_BACKEND_DIR, "db", "shared")
        self._embeddings = FastEmbedEmbeddings()
        model_cfg = CONFIG.get("model", {})
        self._llm = ChatOllama(
            model=model_cfg.get("name", "phi3"),
            base_url=model_cfg.get("base_url", "http://localhost:11434"),
            temperature=model_cfg.get("temperature", 0),
        )
        self._vector_store: Optional[Chroma] = None
        if os.path.isdir(self.persist_dir):
            self._vector_store = Chroma(
                persist_directory=self.persist_dir,
                embedding_function=self._embeddings,
            )

    # ── Retriever ─────────────────────────────────────────────
    def _get_retriever(self, intent: str, allowed_files: list = None):
        """
        Build a retriever using Chroma-native metadata filtering.

        allowed_files: exact metadata.source values ("{chat_id}::{file_name}").
          - If provided and non-empty → apply {"source": {"$in": allowed_files}} filter.
          - If empty / None           → no filter (fallback to all docs).
        """
        if not self._vector_store:
            return None
        cfg = CONFIG["retrieval"].get(intent, CONFIG["retrieval"]["general"])
        search_kwargs: dict = {
            "k":               cfg["k"],
            "score_threshold": cfg["score_threshold"],
        }
        if allowed_files is not None and len(allowed_files) > 0:
            search_kwargs["filter"] = {"source": {"$in": list(allowed_files)}}
        return self._vector_store.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs=search_kwargs,
        )

    # ── Ingest ────────────────────────────────────────────────
    def ingest(self, pdf_path: str, file_name: str, chat_id: str) -> int:
        """
        Ingest a PDF into the shared Chroma collection.
        metadata.source is set to "{chat_id}::{file_name}" for collision-safe scoping.
        Chroma reference is refreshed after every ingest.
        """
        prefixed = f"{chat_id}::{file_name}"
        chunks   = _pdf_to_chunks(pdf_path, prefixed)
        if not chunks:
            return 0
        if self._vector_store is None:
            os.makedirs(self.persist_dir, exist_ok=True)
            self._vector_store = Chroma.from_documents(
                documents=chunks,
                embedding=self._embeddings,
                persist_directory=self.persist_dir,
            )
        else:
            self._vector_store.add_documents(chunks)
            # Rebuild: re-open the collection so retriever sees the new chunks
            self._vector_store = Chroma(
                persist_directory=self.persist_dir,
                embedding_function=self._embeddings,
            )
        logger.info("INGEST  chat=%s  source=%s  chunks=%d", chat_id[:8], prefixed, len(chunks))
        return len(chunks)

    # ── Delete ────────────────────────────────────────────────
    def delete_file(self, file_name: str, chat_id: str):
        """
        Delete all chunks for a file in the shared Chroma collection.
        Matches exactly: metadata.source == "{chat_id}::{file_name}".
        Rebuilds the Chroma reference so subsequent queries see the deletion.
        """
        if not self._vector_store:
            return
        prefixed = f"{chat_id}::{file_name}"
        self._vector_store.delete(where={"source": prefixed})
        # Rebuild: re-open so retriever reflects deletion
        self._vector_store = Chroma(
            persist_directory=self.persist_dir,
            embedding_function=self._embeddings,
        )
        logger.info("DELETE  chat=%s  source=%s", chat_id[:8], prefixed)

    # ── List files ────────────────────────────────────────────
    def get_ingested_files(self, chat_id: str) -> list[str]:
        """
        Return prefixed source keys for this chat only.
        e.g. ["abc123::report.pdf", "abc123::guide.pdf"]
        """
        if not self._vector_store:
            return []
        prefix  = f"{chat_id}::"
        results = self._vector_store.get(include=["metadatas"], limit=100_000)
        return sorted({
            m["source"]
            for m in results.get("metadatas", [])
            if m and m.get("source", "").startswith(prefix)
        })

    # ── Intent classifier ─────────────────────────────────────
    def classify(self, question: str) -> str:
        valid    = CONFIG["classifier"]["valid_intents"]
        fallback = CONFIG["classifier"]["fallback_intent"]
        raw      = (_CLASSIFIER_PROMPT | self._llm | StrOutputParser()).invoke({"question": question}).strip().lower()
        first    = re.split(r"[\s\n,.\-:]+", raw)[0]
        intent   = first if first in valid else next((v for v in valid if v in raw), fallback)
        logger.info("CLASSIFY  intent=%-10s  raw=%r  q=%r", intent, raw, question[:60])
        return intent

    # ── Query rewriter for follow-ups ───────────────────────────
    def _rewrite_query(self, question: str, history_messages: list) -> str:
        """
        Rewrite a short/vague follow-up into a self-contained query
        using the conversation history. Returns the original if
        history is empty or the query is already clear.
        """
        history_text = _format_history(history_messages)
        if history_text == "No previous conversation.":
            return question

        rewrite_prompt = PromptTemplate.from_template(
            "Given the conversation and the latest question, "
            "rewrite the question into a fully self-contained query "
            "that can be understood without any prior context. "
            "Output ONLY the rewritten question, nothing else.\n\n"
            "{history}\n\n"
            "Latest question: {question}\n\n"
            "Rewritten question:"
        )
        try:
            rewritten = (rewrite_prompt | self._llm | StrOutputParser()).invoke({
                "history": history_text,
                "question": question,
            }).strip().strip('"')
            if rewritten and len(rewritten) > 3:
                logger.info("REWRITE  q=%r  →  %r", question[:50], rewritten[:80])
                return rewritten
        except Exception:
            pass
        return question

    def _is_followup_llm(self, question: str, history_messages: list) -> bool:
        history_text = _format_history(history_messages)
    
        if history_text == "No previous conversation.":
            return False
    
        prompt = PromptTemplate.from_template(FOLLOWUP_PROMPT)
    
        try:
            result = (prompt | self._llm | StrOutputParser()).invoke({
                "history": history_text,
                "question": question,
            }).strip().upper()
    
            return result == "YES"
        except:
            return False

    # ── Answer ────────────────────────────────────────────────
    def ask(self, question: str, chat_id: str,
            history_messages: list, allowed_files: list = None) -> dict:
        """
        Generate an answer.

        Parameters
        ----------
        question        : user query
        chat_id         : current chat (for logging only)
        history_messages: list of {role, content, ...} dicts from chat_store
        allowed_files   : exact metadata.source values to filter retrieval.
                          Pass [] or None to query across all docs (fallback).
        """
        if not question or len(question.strip()) < 3:
            return {"answer": "Please ask a meaningful question.", "intent": "general", "sources": []}
        if not self._vector_store:
            return {"answer": "Please upload a document first.", "intent": "general", "sources": []}

        # ── STRICT ISOLATION: no files → no retrieval ─────────
        if not allowed_files:
            return {"answer": "Please upload a document first.", "intent": "general", "sources": []}

        allowed_set = set(allowed_files)
        logger.info("ISOLATION  chat=%s  allowed_files=%s", chat_id[:8], list(allowed_set))

        # Detect short / follow-up queries and rewrite for better retrieval
        q = question.lower().strip()
        
        cheap_signal = (
            len(q.split()) <= 4 or
            any(p in q for p in ["it", "that", "this", "those"])
        )
        
        if cheap_signal:
            is_followup = self._is_followup_llm(question, history_messages)
        else:
            is_followup = False
        retrieval_query = question
        if is_followup:
            retrieval_query = self._rewrite_query(question, history_messages)

        if is_followup:
            intent = "specific"
        else:
            intent = self.classify(question)
        retriever = self._get_retriever(intent, allowed_files)

        # Use the (possibly rewritten) query for retrieval
        docs = retriever.invoke(retrieval_query) if retriever else []

        # If rewritten query found nothing, fall back to the original query
        if not docs and retrieval_query != question and retriever:
            docs = retriever.invoke(question)

        # ── HARD POST-FILTER: Python-side safety net ──────────
        # Never trust Chroma filtering alone — enforce in Python
        pre_filter_count = len(docs)
        docs = [d for d in docs if d.metadata.get("source") in allowed_set]
        if pre_filter_count != len(docs):
            logger.info("POST-FILTER  chat=%s  before=%d  after=%d",
                        chat_id[:8], pre_filter_count, len(docs))

        # Enforce strict grounding — never pass empty context to the LLM
        if not docs:
            logger.info("ANSWER  chat=%s  intent=%s  no docs matched filter", chat_id[:8], intent)
            return {"answer": "I don't know based on the document.", "intent": intent, "sources": []}

        # Allow more chunks for follow-ups (they need broader context)
        max_chunks = 6 if is_followup else 4
        docs = docs[:max_chunks]

        context = "\n\n".join(d.page_content for d in docs)
        has_code = "```" in context or any(
            kw in context for kw in [
                "class ", "def ", "#include", "public:", "private:"
            ]
        )

        # Strip prefix for display ("abc::report.pdf" → "report.pdf"), then deduplicate
        sources = list(dict.fromkeys(
            d.metadata.get("source", "").split("::", 1)[-1]
            for d in docs if d.metadata.get("source")
        ))

        answer = (_ANSWER_PROMPTS[intent] | self._llm | StrOutputParser()).invoke({
            "context":  context,
            "question": question,
            "has_code": has_code,
        })
        logger.info("ANSWER  chat=%s  intent=%s  chunks=%d  sources=%s  followup=%s",
                    chat_id[:8], intent, len(docs), sources, is_followup)
        return {"answer": answer, "intent": intent, "sources": sources}


# ── Singleton ─────────────────────────────────────────────────
_engine: Optional[DocCopilotEngine] = None

def get_engine() -> DocCopilotEngine:
    global _engine
    if _engine is None:
        logger.info("ENGINE  initializing shared engine")
        _engine = DocCopilotEngine()
    return _engine