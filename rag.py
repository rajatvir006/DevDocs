from langchain_community.vectorstores import Chroma
from langchain_ollama import ChatOllama
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import PromptTemplate
from langchain_community.vectorstores.utils import filter_complex_metadata
import uuid


class DevDocsCopilot:
    def __init__(self):
        self.vector_store = None
        self.retriever = None
        self.chain = None

        # 🔥 mapping file → chunk IDs
        self.file_chunk_map = {}

        self.model = ChatOllama(
            model="phi3",
            base_url="http://localhost:11434",
            temperature=0,
        )

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=400,
            chunk_overlap=50,
        )

        self.prompt = PromptTemplate.from_template("""
You are DevDocs Copilot, a strict document-based assistant.

RULES:
1. Answer ONLY using the provided CONTEXT.
2. Do NOT use outside knowledge.
3. If answer not found, reply EXACTLY:
   "I don't know based on the document."

---------------------
CONTEXT:
{context}
---------------------

QUESTION:
{question}

ANSWER:
""")

    def ingest(self, pdf_file_path: str, file_name: str):
        docs = PyMuPDFLoader(file_path=pdf_file_path).load()
        chunks = self.text_splitter.split_documents(docs)
        chunks = filter_complex_metadata(chunks)

        ids = []

        for chunk in chunks:
            chunk_id = str(uuid.uuid4())
            ids.append(chunk_id)

        # store mapping
        self.file_chunk_map[file_name] = ids

        if self.vector_store is None:
            self.vector_store = Chroma.from_documents(
                documents=chunks,
                embedding=FastEmbedEmbeddings(),
                ids=ids,
            )
        else:
            self.vector_store.add_documents(chunks, ids=ids)

        # retriever
        self.retriever = self.vector_store.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"k": 2, "score_threshold": 0.5},
        )

        # chain
        self.chain = (
            {
                "context": self.retriever
                | (lambda docs: "\n\n".join(d.page_content for d in docs)),
                "question": RunnablePassthrough(),
            }
            | self.prompt
            | self.model
            | StrOutputParser()
        )

    def ask(self, query: str):
        if not self.chain:
            return "Please upload a document first."

        return self.chain.invoke(query)

    def clear(self):
        self.vector_store = None
        self.retriever = None
        self.chain = None
        self.file_chunk_map = {}