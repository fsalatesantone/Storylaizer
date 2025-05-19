import streamlit as st
import time
import os
import pandas as pd
from dotenv import load_dotenv
import io

from api import ask_openai
from ui_components import render_user_message, render_response, load_css, render_header, display_chat_history
from utils import reset_conversation, init_session_state, export_chat

if not os.environ.get("STREAMLIT_SHARING"):
    load_dotenv()

def get_api_key():
    api_key = st.secrets.get("OPENAI_API_KEY", None) if hasattr(st, "secrets") else None
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY")
    return api_key

def render_conversation_options(tab_key):
    """Renderizza le opzioni di conversazione nell'expander"""
    with st.expander("⚙️ Opzioni conversazione", expanded=False):
        disabilita = not st.session_state.get("conversation_started", False)
        
        # Aggiungi un prefisso alla chiave in base alla tab
        reset_btn_key = f"reset_button_{tab_key}"
        format_key = f"export_format_{tab_key}"
        download_key = f"download_button_{tab_key}"
        model_key = f"model_selection_{tab_key}" 
        temp_key = f"temperature_slider_{tab_key}"
        top_p_key = f"top_p_slider_{tab_key}"
        
        st.button("🧹 Reset conversazione", on_click=reset_conversation, disabled=disabilita, key=reset_btn_key)
        
        formati = {"📊 XLSX": "XLSX", "📝 DOCX": "DOCX", "📄 TXT": "TXT"}
        formato_label = st.selectbox(
            "📂 Seleziona formato di esportazione:",
            list(formati.keys()),
            key=format_key,
            disabled=disabilita
        )
        formato = formati[formato_label]
        
        export_result = export_chat(formato.lower()) if not disabilita else None
        
        st.download_button(
            label=f"📥 Download conversazione [{formato}]",
            data=export_result[0] if export_result else b"",
            file_name=export_result[2] if export_result else "",
            mime=export_result[1] if export_result else "",
            disabled=disabilita,
            key=download_key
        )
        
        # Scelta modello
        modelli = {
            "🪶 GPT-4.1 Nano (in: $0.10/1M - out: $0.40/1M)": "gpt-4.1-nano",
            "⚡ GPT-4.1 Mini (in: $0.40/1M - out: $1.60/1M)": "gpt-4.1-mini",
            "🧠 GPT-4.1 (in: $2.00/1M - out: $8.00/1M)": "gpt-4.1"
        }
        modello_label = st.selectbox(
            "🧩 Seleziona modello OpenAI:",
            list(modelli.keys()),
            index=0,  # Default su GPT-4.1 Nano
            key=model_key,
            disabled=False
        )
        st.session_state["selected_model"] = modelli[modello_label]
        
        # Controlli creatività e distribuzione
        st.session_state["temperature"] = st.slider(
            "🌡️ Temperature (default: 0.7):",
            min_value=0.0,
            max_value=2.0,
            value=0.7,
            step=0.1,
            disabled=False,
            key=temp_key
        )
        
        st.session_state["top_p"] = st.slider(
            "🎯 Top-p (default: 1.0):",
            min_value=0.0,
            max_value=1.0,
            value=1.0,
            step=0.05,
            disabled=False,
            key=top_p_key
        )

def handle_chat_input(key):
    """Gestisce l'input della chat con una chiave univoca"""
    # Se c'è un messaggio pendente (dopo un rerun), gestiscilo
    if "pending_user_message" not in st.session_state:
        st.session_state.pending_user_message = None
    
    if st.session_state.pending_user_message:
        user_input = st.session_state.pending_user_message
        st.session_state.pending_user_message = None
        
        render_user_message(user_input)
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        st.session_state.conversation_started = True
        
        with st.chat_message("assistant"):
            loading_placeholder = st.empty()
            loading_placeholder.markdown("🧠 *Storylaizer sta scrivendo...*")
            risposta = ask_openai(st.session_state.chat_history
                                  , model=st.session_state.get("selected_model", "gpt-4.1-nano")
                                  , temperature=st.session_state.get("temperature", 0.7)
                                  , top_p=st.session_state.get("top_p", 1.0)
                                  )
            loading_placeholder.empty()
            render_response(risposta)
            st.session_state.chat_history.append({"role": "assistant", "content": risposta})
        
        st.rerun()
    
    # Altrimenti mostra il campo input con chiave univoca
    user_input = st.chat_input("Scrivi qualcosa...", key=key)
    if user_input:
        st.session_state.pending_user_message = user_input
        st.rerun()

def main():
    st.set_page_config(page_title="Storylaizer", layout="centered")
    load_css()
    init_session_state()
    render_header()

    api_key = get_api_key()
    if not api_key:
        api_key_input = st.text_input("Inserisci la tua chiave API OpenAI:", type="password")
        if api_key_input:
            st.session_state.temp_api_key = api_key_input
            st.success("✅ Chiave API impostata per questa sessione!")
            st.rerun()
        else:
            st.warning("⚠️ È necessaria una chiave API OpenAI per utilizzare l'applicazione.")
            return
    else:
        if not os.environ.get("OPENAI_API_KEY"):
            os.environ["OPENAI_API_KEY"] = api_key

    if hasattr(st.session_state, 'temp_api_key') and st.session_state.temp_api_key:
        os.environ["OPENAI_API_KEY"] = st.session_state.temp_api_key

    # Tieni traccia della tab precedente per gestire il reset quando si cambia tab
    if "previous_tab" not in st.session_state:
        st.session_state.previous_tab = "file"  # Valore iniziale

    # Inizializza lo stato della tab attiva se non esiste
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "file"  # Default alla tab dei file

    # Utilizzo st.tabs invece di st.radio
    tab1, tab2 = st.tabs(["📁 Carica un file", "💬 Parla con l'assistente AI"])
    
    # Contenuto della prima tab (Carica file)
    with tab1:
        # Se abbiamo cambiato tab dalla chat alla tab file, resettiamo la chat
        if st.session_state.previous_tab == "chat" and st.session_state.active_tab == "file":
            if "conversation_started" in st.session_state and st.session_state.conversation_started:
                reset_conversation()
                st.session_state.conversation_started = False
        
        # Aggiorna lo stato della tab
        st.session_state.active_tab = "file"
        st.session_state.previous_tab = "file"
        
        uploader_key = f"uploader_{st.session_state.session_id}"
        uploaded_file = st.file_uploader("Carica il file con i dati da analizzare", type=["xlsx"], key=uploader_key)
        if uploaded_file:
            st.session_state.uploaded_file = uploaded_file
            st.session_state.file_loaded = True
            st.success(f"✅ Hai caricato: {uploaded_file.name}")
            
            # Area di chat dopo il caricamento del file
            if st.session_state.file_loaded:
                
                # Opzioni di conversazione dopo il caricamento del file con chiave specifica per la tab
                render_conversation_options(tab_key="file_tab")
                
                st.markdown("<div class='mode-title'>Inizia a parlare con l'assistente</div><div class='mode-subtitle'>Fornisci una descrizione dei dati caricati e le istruzioni da eseguire.</div>", unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)

                # Visualizzazione della cronologia chat
                display_chat_history()
                
                # Input utente con chiave univoca
                handle_chat_input(key="chat_input_file_tab")

    
    # Contenuto della seconda tab (Chat)
    with tab2:
        # Se abbiamo cambiato tab dalla tab file alla chat, aggiorniamo lo stato
        if st.session_state.previous_tab == "file" and st.session_state.active_tab == "chat":
            if "conversation_started" in st.session_state and st.session_state.conversation_started:
                # Non resettiamo la conversazione quando passiamo alla tab chat
                pass
        
        # Aggiorna lo stato della tab
        st.session_state.active_tab = "chat"
        st.session_state.previous_tab = "chat"
        
        # EXPANDER - Opzioni con chiave specifica per la tab
        render_conversation_options(tab_key="chat_tab")
        st.markdown("<div class='mode-title'>Inizia a parlare con l'assistente</div><div class='mode-subtitle'>Incolla la tabella direttamente nella chat e fornisci una descrizione dei dati caricati e le istruzioni da eseguire.</div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Visualizzazione della cronologia chat
        display_chat_history()
        
        # Input utente con chiave univoca
        handle_chat_input(key="chat_input_chat_tab")

if __name__ == "__main__":
    main()