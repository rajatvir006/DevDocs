from langchain_community.vectorstores import Chroma
from langchain_ollama import ChatOllama
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import PromptTemplate
from langchain_community.vectorstores.utils import filter_complex_metadata


class DevDocsCopilot:
    vector_store = None
    retriever = None
    chain = None

    def __init__(self):
        self.model = ChatOllama(
            model="phi3",
            base_url='http://localhost:11434',
            temperature=0
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=400,
            chunk_overlap=50
        )
        self.prompt = PromptTemplate.from_template("""
You are DevDocs Copilot, a strict document-based assistant.

RULES (must follow):

1. Answer ONLY using the provided CONTEXT.
2. Do NOT use any outside knowledge.
3. If the answer is NOT clearly found in the context, reply EXACTLY:
   "I don't know based on the document."
4. Do NOT guess.
5. Do NOT partially answer.
6. Keep the answer concise and directly based on the context.
7. If possible, use phrases directly from the context.

---------------------
CONTEXT:
{context}
---------------------

QUESTION:
{question}

---------------------

ANSWER:
""")

    def ingest(self, pdf_file_path: str):
        docs = PyMuPDFLoader(file_path=pdf_file_path).load()
        chunks = self.text_splitter.split_documents(docs)
        chunks = filter_complex_metadata(chunks)

        if self.vector_store is None:
            self.vector_store = Chroma.from_documents(
                documents=chunks,
                embedding=FastEmbedEmbeddings()
            )
        else:
            self.vector_store.add_documents(chunks)

        self.retriever = self.vector_store.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={
                "k": 2,
                "score_threshold": 0.5,
            },
        )

        self.chain = (
            {
                "context": self.retriever | (
                    lambda docs: "\n\n".join(doc.page_content for doc in docs)
                ),
                "question": RunnablePassthrough()
            }
            | self.prompt
            | self.model
            | StrOutputParser()
        )

    def ask(self, query: str):
        if not self.chain:
         return "Please upload a document first."

        if len(query.strip()) < 3:
         return "Please ask a meaningful question."

        return self.chain.invoke(query)

    def clear(self):
        self.vector_store = None
        self.retriever = None
        self.chain = None