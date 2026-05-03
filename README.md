<div align="center">
  <img src="static/images.png" alt="StudyMate Logo" width="400"/>
  <h1>StudyMate 📚</h1>
  <p><b>Your AI-powered academic co-pilot for focused learning.</b></p>
  <p>🎯 Session-Based Learning · 🧠 Smart Document Q&A · ⚡ Context-Aware RAG</p>

  <a href="YOUR_STREAMLIT_URL_HERE">🔴 Live Demo</a>
</div>

---

## 📌 What is StudyMate?

StudyMate is a **session-based Retrieval-Augmented Generation (RAG) system** that lets you upload study materials (PDFs) and interact with them using natural language.

Each session is isolated, meaning:
- One session = one subject/context  
- Physics notes don’t interfere with DBMS notes  
- Clean separation of knowledge domains  

The system prioritizes:
1. Your uploaded documents  
2. General knowledge fallback (only if relevant)  
3. Clear refusal if unrelated  


---

## ✨ Features

- 🧠 Session-based document isolation per subject
- 📄 Semantic chunking for meaning-aware document splitting
- 🔍 Context-first Q&A using uploaded PDFs
- 💬 Short-term conversation memory (last 6 exchanges)
- ⚡ Streaming responses (token-by-token output)
- 🗄️ Persistent sessions & chat history via Supabase

---

## 🧰 Tech Stack

| Layer            | Technology |
|------------------|------------|
| Frontend         | Streamlit |
| LLM              | Groq (Qwen3-32B) |
| Embeddings       | HuggingFace (all-MiniLM-L6-v2) |
| Vector Database   | Supabase (pgvector) |
| Database         | Supabase PostgreSQL |
| RAG Framework    | LangChain |
| Chunking         | SemanticChunker |

---

## 🚀 Local Setup

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/studymate.git
cd studymate
```
### 2. Create virtual environment
```bash
python -m venv venv

# Windows
.\venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```
### 3. Install dependencies
```bash
pip install -r requirements.txt
```
### 4. Configure environment variables

Create a .env file in the root directory:
```bash
GROQ_API_KEY="your_groq_api_key"
EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"

SUPABASE_URL="your_supabase_project_url"
SUPABASE_KEY="your_supabase_anon_key"
SUPABASE_DB_URL="your_supabase_DB_URL"

```
### 5. Run the application
```bash
streamlit run src/app.py
```
## 📁 Project Structure
```bash
StudyMate/
├── src/
│   ├── app.py
│   └── classes.py
├── static/
│   └── images.png
├── requirements.txt
├── README.md
└── LICENSE
```
## How to Use StudyMate
### 1. Create a Study Session
Start by creating a session for a course, topic, or exam. Each session keeps its documents and AI context separate.

### 2. Upload Documents
Add PDFs or study material to the session. StudyMate automatically chunks them for AI to read and understand.

### 3. Ask Questions in Chat
Use the chat feature to ask anything about your uploaded documents. The AI answers with session-specific context, so you get precise and relevant responses.

### 4. Manage & Review
Track session activity, review uploaded documents, or delete outdated sessions to keep everything tidy.

## 🧰 Tech Stack

### 🖥️ Frontend
- Streamlit — UI, file uploads, chat interface, session handling

### 🧠 LLM / Reasoning Engine
- Groq (Qwen3-32B) — fast LLM inference

### 🔎 Embeddings
- Hugging Face (sentence-transformers/all-MiniLM-L6-v2)

### 🗄️ Vector Database
- Supabase (pgvector) — vector similarity search

### 🗃️ Database
- PostgreSQL (via Supabase) — session data, chat history, metadata

### 🧱 RAG Framework
- LangChain — retrieval + generation orchestration

### ✂️ Chunking Strategy
- SemanticChunker (LangChain experimental) — semantic document splitting

### ⚙️ Supporting Libraries
- Pydantic — data validation
- python-dotenv — environment variable management
- sentence-transformers — embedding backend


## Live URL: 
### https://s-t-u-d-y-m-a-t-e.streamlit.app/


## 👤 Author

Built by a Nouman Fazil. Student at NED Univeristy and  exploring real-world AI systems and RAG pipelines.
