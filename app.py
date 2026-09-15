import streamlit as st
from streamlit_pdf_viewer import pdf_viewer
from main import MBAR_LM
import os 
import time

@st.cache_resource
def load_model():
    return MBAR_LM()

model = load_model()

st.set_page_config(page_title="MBAR AI Consultant", layout="wide")

# --- CALLBACK FUNCTIONS ---
def update_slider(name):
    if st.session_state[f"{name}_num"] != st.session_state[f"{name}_slider"]:
        st.session_state[f"{name}_slider"] = st.session_state[f"{name}_num"]

def update_num(name):
    if st.session_state[f"{name}_slider"] != st.session_state[f"{name}_num"]:
        st.session_state[f"{name}_num"] = st.session_state[f"{name}_slider"]

# 1. THE POPUP DIALOG
@st.dialog("Policy Document Review", width="large")
def show_pdf_modal(file_path, page):
    st.write(f"Reviewing: **{file_path}**")
    pdf_viewer(file_path, height=800, pages_to_render=[page], key=f"modal_{int(time.time())}")
    if st.button("Close"):
        st.rerun()

# 2. PURE CSS OVERLAY
st.markdown("""
    <style>
    .st-key-pdf_overlay_btn {
        margin-top: -425px !important;
        z-index: 10 !important;
        display: flex;
        justify-content: center;
        margin-left: -16px !important; 
        width: calc(100% + 32px) !important;
    }

    .st-key-pdf_overlay_btn button {
        height: 382px !important;
        width: 100% !important;
        background-color: transparent !important;
        border: none !important;
        color: transparent !important;
        transition: all 0.3s ease !important;
        border-radius: 0px !important;
        margin-left: 17.30px !important;
    }

    .st-key-pdf_overlay_btn button:hover {
        background-color: rgba(0, 0, 0, 0.6) !important;
        background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" fill="white"><path d="M416 208c0 45.9-14.9 88.3-40 122.7L502.6 457.4c12.5 12.5 12.5 32.8 0 45.3s-32.8 12.5-45.3 0L330.7 376c-34.4 25.2-76.8 40-122.7 40C93.1 416 0 322.9 0 208S93.1 0 208 0S416 93.1 416 208zM208 352a144 144 0 1 0 0-288 144 144 0 1 0 0 288zM240 256v48c0 8.8-7.2 16-16 16s-16-7.2-16-16V256H160c-8.8 0-16-7.2-16-16s7.2-16 16-16h48V176c0-8.8 7.2-16 16-16s16 7.2 16 16v48h48c8.8 0 16 7.2 16 16s-7.2 16-16 16H240z"/></svg>') !important;
        background-repeat: no-repeat !important;
        background-position: center !important;
        background-size: 30px 30px !important;
    }
    
    iframe[title="streamlit_pdf_viewer.pdf_viewer"] {
        border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# 3. SIDEBAR
with st.sidebar:
    
    st.header("NLP Inputs")

    # Chunk Size Sync
    if 'chunk_num' not in st.session_state: st.session_state['chunk_num'] = 500
    if 'chunk_slider' not in st.session_state: st.session_state['chunk_slider'] = 500

    col1, col2 = st.columns([3, 1])
    with col1:
        st.slider("Chunk Size", 100, 2000, key="chunk_slider", on_change=update_num, args=("chunk",))
    with col2:
        st.number_input("Size", 100, 2000, key="chunk_num", on_change=update_slider, args=("chunk",), label_visibility="collapsed")

    # Overlap Sync
    if 'overlap_num' not in st.session_state: st.session_state['overlap_num'] = 100
    if 'overlap_slider' not in st.session_state: st.session_state['overlap_slider'] = 100

    col3, col4 = st.columns([3, 1])
    with col3:
        st.slider("Overlap", 0, 200, key="overlap_slider", on_change=update_num, args=("overlap",))
    with col4:
        st.number_input("Overlap", 0, 200, key="overlap_num", on_change=update_slider, args=("overlap",), label_visibility="collapsed")

    chunk = st.session_state['chunk_num']
    overlap = st.session_state['overlap_num']

    if st.button("Re-Index PDF"):
        with st.spinner("Re-indexing..."):
            # FIX 1: Use the safe reset method from main.py to prevent memory locks
            model.reset_database()
            model.parse_pdf("Policies.pdf")
            st.success("Database Rebuilt!")

    st.divider()
    st.header("Source Document")
    
    if "last_metadata" in st.session_state:
        display_file = st.session_state.last_metadata.get('highlighted_path')
        
        # --- THE FIX IS HERE ---
        # Get the page, default to 1 if missing, ensure it's an integer, and force it to be at least 1
        raw_page = st.session_state.last_metadata.get('page', 1)
        page_num = max(1, int(raw_page)) 

        if display_file and os.path.exists(display_file):
            # The timestamp key FORCES the viewer to re-render the new highlight
            pdf_viewer(display_file, width=300, height=400, pages_to_render=[page_num], key=f"viewer_{display_file}")
        
        if st.button("Enlarge Document", key="pdf_overlay_btn"):
            show_pdf_modal(display_file, page_num)
        
        st.caption(f"Showing page {page_num} of Policies.pdf")
    else:
        st.caption("Ask Query to display source document")

# 4. MAIN CHAT
st.title("🏛️ <Placeholder> AI Consultant")

with st.expander("🔍 View Latest Grounding Source"):
    if "last_context" in st.session_state:
        st.markdown(f'''
            <div style="
                border-left: 4px solid #4A90E2; 
                padding: 15px; 
                background-color: #1E1E1E; 
                color: #E0E0E0; 
                font-family: monospace;
                white-space: pre-wrap; /* FIX: Forces HTML to show the real chunk shape */
            ">
{st.session_state.last_context}
            </div>
        ''', unsafe_allow_html=True)
    else:
        st.markdown("Raise query for context")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []      

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if prompt := st.chat_input("Ask a question"):
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Reviewing Documents..."):
            response, context, metadata = model.query_rag(prompt)
            st.session_state.last_context = context
            st.session_state.last_metadata = metadata
            st.write(response)

    st.session_state.chat_history.append({"role": "assistant", "content": response})
    st.rerun()