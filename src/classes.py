# Updated Backend with Supabase database
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_experimental.text_splitter import SemanticChunker
from langchain_community.document_loaders import PyPDFLoader
from langchain_groq import ChatGroq
from langchain_core.prompts import (
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    ChatPromptTemplate
)
from langchain_core.documents import Document
from pypdf import PdfReader
from supabase import create_client, Client
from dotenv import load_dotenv
import psycopg2
import os
from datetime import datetime

load_dotenv()


class Database:
    @property
    def client(self):
        load_dotenv()
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        return create_client(url, key)

    def _create_tables(self):
        # Tables already created via Supabase SQL editor
        pass

    # ------------------- Session Methods -------------------

    def add_session(self, session_name, subject_category):
        if self.session_exists(session_name):
            return None
        created_at = datetime.now().isoformat()
        result = self.client.table("sessions").insert({
            "session_name": session_name,
            "subject_category": subject_category,
            "created_at": created_at
        }).execute()
        return result.data[0]["session_id"] if result.data else None

    def session_exists(self, session_name):
        result = self.client.table("sessions").select("session_id").eq("session_name", session_name).execute()
        return len(result.data) > 0

    def get_sessions(self):
        result = self.client.table("sessions").select("*").execute()
        return [(r["session_id"], r["session_name"], r["subject_category"], r["created_at"]) for r in result.data]

    def get_session_id(self, session_name):
        result = self.client.table("sessions").select("session_id").eq("session_name", session_name).execute()
        return result.data[0]["session_id"] if result.data else None

    def get_subject_category(self, session_name):
        result = self.client.table("sessions").select("subject_category").eq("session_name", session_name).execute()
        return result.data[0]["subject_category"] if result.data else None

    def delete_session(self, session_name):
        session_id = self.get_session_id(session_name)
        if not session_id:
            return False
        self.client.table("messages").delete().eq("session_id", session_id).execute()
        self.client.table("documents").delete().eq("session_id", session_id).execute()
        self.client.table("embeddings").delete().eq("session_name", session_name).execute()
        self.client.table("sessions").delete().eq("session_id", session_id).execute()
        return True

    # ------------------- Document Methods -------------------

    def add_document(self, session_id, doc_name, file_path):
        result = self.client.table("documents").insert({
            "session_id": session_id,
            "doc_name": doc_name,
            "file_path": file_path
        }).execute()
        return result.data[0]["doc_id"] if result.data else None

    def get_documents(self, session_id):
        result = self.client.table("documents").select("*").eq("session_id", session_id).execute()
        return [(r["doc_id"], r["session_id"], r["doc_name"], r["file_path"]) for r in result.data]

    def get_document_paths(self, session_id):
        result = self.client.table("documents").select("file_path").eq("session_id", session_id).execute()
        return [r["file_path"] for r in result.data]

    # ------------------- Message Methods -------------------

    def add_message(self, session_id, sender, content):
        timestamp = datetime.now().isoformat()
        result = self.client.table("messages").insert({
            "session_id": session_id,
            "sender": sender,
            "content": content,
            "timestamp": timestamp
        }).execute()
        return result.data[0]["message_id"] if result.data else None

    def get_messages(self, session_id):
        result = self.client.table("messages").select("*").eq("session_id", session_id).order("timestamp").execute()
        return [(r["message_id"], r["session_id"], r["sender"], r["content"], r["timestamp"]) for r in result.data]

    def get_last_k_messages_by_name(self, session_name: str, k: int):
        session_id = self.get_session_id(session_name)
        if not session_id:
            return []
        result = self.client.table("messages").select("message_id, session_id, sender, content").eq("session_id", session_id).order("message_id", desc=True).limit(k).execute()
        rows = [(r["message_id"], r["session_id"], r["sender"], r["content"]) for r in result.data]
        return rows[::-1]

    def close(self):
        pass  # Supabase client doesn't need explicit closing


class vectordb:
    def __init__(self, **kwargs):
        self.embedding_model_name = os.environ.get("EMBEDDING_MODEL")
        self.embedding_engine = HuggingFaceEmbeddings(
            model_name=self.embedding_model_name
        )
        self.database = Database()
        self.db_url = os.environ.get("SUPABASE_DB_URL")
        self.textsplitter = SemanticChunker(
            self.embedding_engine,
            breakpoint_threshold_type="percentile",
            breakpoint_threshold_amount=85
        )
        print("Vector database initialized successfully.")

    def _embed_text(self, text):
        return self.embedding_engine.embed_query(text)

    def _insert_embedding(self, session_name, content, metadata, embedding):
        conn = psycopg2.connect(self.db_url)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO embeddings (session_name, content, metadata, embedding) VALUES (%s, %s, %s, %s)",
            (session_name, content, psycopg2.extras.Json(metadata), embedding)
        )
        conn.commit()
        cur.close()
        conn.close()

    def _similarity_search(self, session_name, query_embedding, k=3):
        import psycopg2.extras
        conn = psycopg2.connect(self.db_url)
        cur = conn.cursor()
        cur.execute("""
            SELECT content, metadata, 1 - (embedding <=> %s::vector) AS similarity
            FROM embeddings
            WHERE session_name = %s
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (query_embedding, session_name, query_embedding, k))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows  # (content, metadata, similarity_score)

    def create_session(self, session_name, subject_category):
        if self.database.session_exists(session_name):
            return False
        self.database.add_session(session_name, subject_category)
        return True

    def get_session(self, session_name):
        if not self.database.session_exists(session_name):
            print(f"Session {session_name} does not exist.")
            return None
        return session_name  # just return name, used as filter key

    def chunk_document(self, document):
        return self.textsplitter.split_documents(document)

    def add_file(self, documents_list, session_name):
        import psycopg2.extras
        session_id = self.database.get_session_id(session_name)

        for i, item in enumerate(documents_list, start=1):
            try:
                if isinstance(item, str):
                    if not os.path.exists(item):
                        print(f"[WARN] File '{item}' not found, skipping.")
                        continue
                    loader = PyPDFLoader(item)
                    document = loader.load()
                    doc_name = os.path.basename(item)
                    doc_path = item
                else:
                    reader = PdfReader(item)
                    document = []
                    for page_idx, page in enumerate(reader.pages):
                        text = page.extract_text()
                        document.append(Document(
                            page_content=text,
                            metadata={"source": item.name, "page": page_idx}
                        ))
                    doc_name = item.name
                    doc_path = f"in-memory://{item.name}"

                chunks = self.chunk_document(document)

                # Insert each chunk embedding into Supabase
                conn = psycopg2.connect(self.db_url)
                cur = conn.cursor()
                for chunk in chunks:
                    embedding = self._embed_text(chunk.page_content)
                    cur.execute(
                        "INSERT INTO embeddings (session_name, content, metadata, embedding) VALUES (%s, %s, %s, %s)",
                        (session_name, chunk.page_content, psycopg2.extras.Json(chunk.metadata), embedding)
                    )
                conn.commit()
                cur.close()
                conn.close()

                self.database.add_document(session_id, doc_name, doc_path)
                print(f"[INFO] Document {i}: '{doc_name}' added successfully.")

            except Exception as e:
                print(f"[ERROR] Failed to add document {i}: {e}")

    def delete_session(self, session_name):
        deleted = self.database.delete_session(session_name)
        if deleted:
            print(f"Session {session_name} deleted successfully.")
        else:
            print(f"Session does not exist.")

    def list_sessions(self):
        sessions = self.database.get_sessions()
        for idx, sess in enumerate(sessions, start=1):
            print(f"{idx}. {sess[1]}")


class RAGAssistant:
    def __init__(self, vector_database):
        self.llm = self._initialize_llm()
        self.vector_db = vector_database
        self.similarity_threshold = 0.20
        print("[INFO] RAGAssistant initialized successfully.")

    def _initialize_llm(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("Groq API key not found!")
        return ChatGroq(
            model="qwen/qwen3-32b",
            temperature=0,
            reasoning_format="hidden",
            max_retries=2
        )

    def _build_strict_prompt(self, session_name, question, past_conversation, context_text, subject_category):
        system_msg = SystemMessagePromptTemplate.from_template("""
        You are Lambda, an AI educational assistant.
        TASK:
        1. If context documents contain the answer, use ONLY context to answer.
        2. If not in context but related to {subject_category}, use general knowledge.
        3. If totally unrelated, respond: "I don't know. No relevant information found."
        INPUTS:
        - Session: {session_name}
        - Past Conversation: {past_conversation}
        - Context: {context_text}
        - Subject Category: {subject_category}
        RULES: Never invent answers. Keep responses concise and clear.
        """)
        human_msg = HumanMessagePromptTemplate.from_template(
            "Question: {question}\nContext: {context_text}\nPast Conversation: {past_conversation}"
        )
        return ChatPromptTemplate.from_messages([system_msg, human_msg])

    def _build_general_prompt(self, session_name, question, past_conversation, subject_category):
        system_msg = SystemMessagePromptTemplate.from_template("""
        You are Lambda, an AI educational assistant.
        ROLE:
        - Answer if related to {subject_category}.
        - If unrelated respond: "I don't know. No relevant information found."
        - If {subject_category} is "General", answer normally.
        - Use past conversation for context only.
        """)
        human_msg = HumanMessagePromptTemplate.from_template(
            "Question: {question}\nSession Subject: {subject_category}\nPast Conversation: {past_conversation}"
        )
        return ChatPromptTemplate.from_messages([system_msg, human_msg])

    def query(self, session_name: str, question: str, n_results: int = 3):
        last_messages = self.vector_db.database.get_last_k_messages_by_name(session_name, 6)
        memory_text = ""
        for m in last_messages:
            role = "User" if m[2] == "user" else "Assistant"
            memory_text += f"{role}: {m[3]}\n"

        subject_category = self.vector_db.database.get_subject_category(session_name)

        query_embedding = self.vector_db._embed_text(question)
        rows = self.vector_db._similarity_search(session_name, query_embedding, k=n_results)

        filtered_docs = [row for row in rows if row[2] >= self.similarity_threshold]
        context_text = "\n\n".join(row[0] for row in filtered_docs)

        prompt = self._build_strict_prompt(session_name, question, memory_text, context_text, subject_category)
        chain = prompt | self.llm

        rows = self.vector_db._similarity_search(session_name, query_embedding, k=n_results)
        print("DEBUG SCORES:", [(row[0][:50], row[2]) for row in rows])

        for chunk in chain.stream({
            "question": question,
            "past_conversation": memory_text,
            "context_text": context_text,
            "session_name": session_name,
            "subject_category": subject_category
        }):
            yield chunk.content