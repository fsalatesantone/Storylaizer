import streamlit as st
import time

def reset_conversation():
    # Nuovo ID sessione per forzare ricaricamento
    st.session_state.session_id = str(time.time())
    
    # Salva la tab corrente prima del reset
    current_tab = st.session_state.get("active_tab", "file")
    
    # Reset variabili principali
    keys_to_reset = ["chat_history", "file_loaded", "uploaded_file", "dataframe", "data_metadata", "data_errors"]
    for key in keys_to_reset:
        if key in st.session_state:
            del st.session_state[key]
    
    # Ripristina la tab corrente
    st.session_state.active_tab = current_tab
    st.session_state.default_tab = current_tab
            
def init_session_state():
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "selected_mode" not in st.session_state:
        st.session_state.selected_mode = None
    if "file_loaded" not in st.session_state:
        st.session_state.file_loaded = False
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "file"  # Default alla tab dei file
    if "uploaded_file" not in st.session_state:
        st.session_state.uploaded_file = None
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(time.time())