import streamlit as st
import os
import shutil
import base64
from classes import Database, vectordb, RAGAssistant

# --- Set project root --- (assumes this file is in src/)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# --- Paths outside src ---
UPLOAD_DIR = os.path.join(PROJECT_ROOT, "uploads")
CHROMA_DIR = os.path.join(PROJECT_ROOT, "chroma_db")
DB_PATH = os.path.join(PROJECT_ROOT, "studymate.db")
icon_path = os.path.join(PROJECT_ROOT, "static", "favicon.ico")

# --- Ensure folders exist ---
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CHROMA_DIR, exist_ok=True)

st.set_page_config(page_title="Lambda", page_icon=icon_path, layout="wide")

# --- Initialize Backend ---
@st.cache_resource
def get_backend():
    vdb = vectordb()    
    assistant = RAGAssistant(vdb)
    return vdb, assistant

vdb, assistant = get_backend()
db = vdb.database

# --- Session State Management ---
if "active_session" not in st.session_state:
    st.session_state.active_session = None

if "messages" not in st.session_state:
    st.session_state.messages = []

if "view_mode" not in st.session_state:
    st.session_state.view_mode = "ingest"

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

def refresh_messages():
    if st.session_state.active_session:
        session_id = db.get_session_id(st.session_state.active_session)
        messages = db.get_messages(session_id)
        st.session_state.messages = [{"role": m[2], "content": m[3]} for m in messages]
    else:
        st.session_state.messages = []

# --- Sidebar ---
with st.sidebar:
    st.markdown(
        """
        <style>
        /* Sidebar scientific clean headings */
        .gradient-text-sessions {
            font-weight: 500;
            font-size: 1.6rem;
            letter-spacing: 1px;
            border-bottom: 2px solid #3B82F6;
            padding-bottom: 4px;
            display: inline-block;
            margin-bottom: 10px;
        }
        .gradient-text-navigation, .gradient-text-create, .gradient-text-delete {
            font-weight: 500;
            font-size: 1.2rem;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            opacity: 0.7;
        }
        /* Hide "Press Enter to submit form" instruction */
        div[data-testid="InputInstructions"] {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown('<div><span class="gradient-text-sessions">⚡ Control Panel</span></div>', unsafe_allow_html=True)
    
    sessions = db.get_sessions()
    session_names = [s[1] for s in sessions]
    
    selected_session = st.selectbox(
        "Active Session",
        options=session_names,
        index=None if st.session_state.active_session not in session_names else session_names.index(st.session_state.active_session),
        placeholder="Choose a session..."
    )
    
    if selected_session and selected_session != st.session_state.active_session:
        st.session_state.active_session = selected_session
        st.session_state.view_mode = "ingest"
        session_id = db.get_session_id(selected_session)
        st.session_state.current_docs = db.get_documents(session_id)
        refresh_messages()
        st.rerun()

    if st.session_state.active_session:
        st.markdown('<div class="gradient-text-navigation" style="margin-top: 20px;">Navigation</div>', unsafe_allow_html=True)
        
        view_selection = st.radio(
            "Go to:", 
            options=["📂 Documents", "💬 Chat"],
            index=0 if st.session_state.view_mode == "ingest" else 1,
            label_visibility="collapsed"
        )
        
        new_mode = "ingest" if view_selection == "📂 Documents" else "chat"
        if new_mode != st.session_state.view_mode:
            st.session_state.view_mode = new_mode
            st.rerun()

    st.divider()
    
    with st.expander("✨ Create New Session", expanded=False):
        with st.form("create_session_form", clear_on_submit=True):
            new_session_name = st.text_input("New Session Name", placeholder="e.g. physics_101").strip()
        
            subject_category = st.selectbox(
                "Select Subject Category",
                options=[
                    "Physics",
                    "Chemistry",
                    "General Math",
                    "Biology",
                    "Computer Science",
                    "Software Development",
                    "Competitive Programming",
                    "Urdu",
                    "Islamic Studies",
                    "Pakistan Studies",
                    "General"
                ]
            )
        
            submit_create = st.form_submit_button("Create Session")
        
            if submit_create:
                if not new_session_name:
                    st.error("Session name cannot be empty.")
                elif " " in new_session_name:
                    st.error("Spaces are not allowed in session names.")
                else:
                    success = vdb.create_session(new_session_name, subject_category)
                    if success:
                        st.success(f"Session '{new_session_name}' created under '{subject_category}'!")
                        st.session_state.active_session = new_session_name
                        st.session_state.view_mode = "ingest"
                        session_id = db.get_session_id(new_session_name)
                        st.session_state.current_docs = db.get_documents(session_id)
                        refresh_messages()
                        st.rerun()
                    else:
                        st.error("Session already exists.")

    if st.session_state.active_session:
        with st.expander("⚙️ Manage Session", expanded=False):
            st.markdown(f"Current Session: **{st.session_state.active_session}**")
            if st.button(f"🗑️ Delete Session", use_container_width=True, type="primary"):
                vdb.delete_session(st.session_state.active_session)
                st.session_state.active_session = None
                st.session_state.messages = []
                st.rerun()

# --- Main Panel ---
if not st.session_state.active_session:
    st.markdown(f"""
    <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:20px; padding-bottom: 20px;">
        <div style="flex: 1;">
            <div style="
                font-size:4.5rem;
                font-weight:300;
                letter-spacing: 2px;
            ">
                λ <span style="font-weight: 600; color: #3B82F6;">Lambda</span>
            </div>
            <div style="font-size:1.1rem; opacity: 0.7; margin-top:5px; font-weight: 400; letter-spacing: 0.5px;">
                Advanced Research & Document Analysis Engine            
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    # --- Ingest View ---
    if st.session_state.view_mode == "ingest":
        # Clean scientific title
        st.markdown(f"""
        <h1 style="
            font-size:2.2rem;
            font-weight:400;
            border-bottom: 1px solid #3B82F6;
            padding-bottom: 10px;
            margin-bottom:20px;
        ">
        <span style="color: #3B82F6;">■</span> Research Space: <b>{st.session_state.active_session}</b>
        </h1>
        """, unsafe_allow_html=True)
        
        # Upload PDFs clean heading
        st.markdown(f"""
        <h2 style="
            font-size:1.4rem;
            font-weight:500;
            opacity: 0.9;
            margin-bottom:10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        ">
        Document Ingestion
        </h2>
        """, unsafe_allow_html=True)
    
        # --- File Uploader with Dynamic Key ---
        uploaded_files = st.file_uploader(
            "Select PDF files",
            type=["pdf"],
            accept_multiple_files=True,
            key=f"uploader_{st.session_state.uploader_key}"
        )

        # --- Add files to session ---
        if st.button("Add to Session"):
            if uploaded_files:
                with st.status("Processing PDFs..."):
                    saved_paths = []
                    for uploaded_file in uploaded_files:
                        file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        saved_paths.append(file_path)
                    vdb.add_file(saved_paths, st.session_state.active_session)
                    st.success(f"{len(saved_paths)} document(s) added successfully!")
                
                # --- Reset Uploader via Dynamic Key ---
                st.session_state.uploader_key += 1
                
                # --- Refresh current documents list ---
                session_id = db.get_session_id(st.session_state.active_session)
                st.session_state.current_docs = db.get_documents(session_id)
                
               # st.rerun()
            else:
                st.warning("No files selected.")
    
        st.divider()
        
        # --- Current Documents heading ---
        st.markdown(f"""
        <h2 style="
            font-size:1.4rem;
            font-weight:500;
            opacity: 0.9;
            margin-bottom:10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        ">
        Indexed Corpus
        </h2>
        """, unsafe_allow_html=True)
    
        # --- Display current documents using session_state ---
        if "current_docs" not in st.session_state:
            session_id = db.get_session_id(st.session_state.active_session)
            st.session_state.current_docs = db.get_documents(session_id)
    
        docs = st.session_state.current_docs
        if docs:
            for doc in docs:
                st.text(f"📄 {doc[2]}")
        else:
            st.write("No documents in this session yet.")

    # --- Chat View ---
    elif st.session_state.view_mode == "chat":
        # Clean Chat title
        st.markdown(f"""
        <h1 style="
            font-size:2.2rem;
            font-weight:400;
            border-bottom: 1px solid #3B82F6;
            padding-bottom: 10px;
            margin-bottom:20px;
        ">
        <span style="color: #3B82F6;">■</span> Analysis Console: <b>{st.session_state.active_session}</b>
        </h1>
        """, unsafe_allow_html=True)

        chat_container = st.container()
        
        with chat_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        if prompt := st.chat_input("Ask a question about your documents..."):
            with st.chat_message("user"):
                st.markdown(prompt)
            
            session_id = db.get_session_id(st.session_state.active_session)
            db.add_message(session_id, "user", prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})

            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""
                with st.spinner("Thinking..."):
                    for chunk in assistant.query(st.session_state.active_session, prompt):
                        full_response += chunk
                        message_placeholder.markdown(full_response + "▌")
                    message_placeholder.markdown(full_response)
            
            db.add_message(session_id, "assistant", full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
