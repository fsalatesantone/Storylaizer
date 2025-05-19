import streamlit as st
import time
import pandas as pd
import io

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

# Esportazione chat in vari formati
def export_chat(format_type):
    if not st.session_state.chat_history:
        st.warning("Non ci sono messaggi da esportare.")
        return None

    if format_type == "xlsx":
        data = [{"Ruolo": "Utente" if msg["role"] == "user" else "Assistente", "Messaggio": msg["content"]} for msg in st.session_state.chat_history]
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Conversazione')
        return output.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "conversazione.xlsx"

    elif format_type == "txt":
        content = ""
        for msg in st.session_state.chat_history:
            prefix = "Utente: " if msg["role"] == "user" else "Assistente: "
            content += f"{prefix}{msg['content']}\n\n"
        return content.encode(), "text/plain", "conversazione.txt"

    elif format_type == "docx":
        try:
            from docx import Document
            doc = Document()
            for msg in st.session_state.chat_history:
                prefix = "Utente: " if msg["role"] == "user" else "Assistente: "
                p = doc.add_paragraph()
                runner = p.add_run(f"{prefix}{msg['content']}")
                runner.bold = msg["role"] == "user"
                doc.add_paragraph("")
            output = io.BytesIO()
            doc.save(output)
            return output.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "conversazione.docx"
        except ImportError:
            st.error("Per esportare in formato docx è necessario installare python-docx: pip install python-docx")
            return None