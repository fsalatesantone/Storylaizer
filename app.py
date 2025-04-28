import streamlit as st
import time
import os
from dotenv import load_dotenv

# Import dei moduli personalizzati
from api import ask_openai
from ui_components import render_user_message, render_response, load_css, render_header
from utils import reset_conversation, init_session_state

# Carica variabili d'ambiente da .env
load_dotenv()

# Prendi la chiave API direttamente
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    st.error("Errore: API Key mancante! Assicurati che il file .env sia configurato.")
    st.stop()


def main():
    st.set_page_config(page_title="Storylaizer", layout="centered")
    
    # Carica CSS
    load_css()
    
    # Inizializzazione delle variabili di stato
    init_session_state()

    # Gestione della chiave API
    if not os.environ.get("OPENAI_API_KEY"):
        try:
            from config import OPENAI_API_KEY
            os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
            st.success("✅ Chiave API caricata dal file di configurazione!")
        except ImportError:
            st.warning("⚠️ Chiave API OpenAI non trovata. Imposta la variabile d'ambiente OPENAI_API_KEY.")
            api_key = st.text_input("Inserisci la tua chiave API OpenAI:", type="password")
            if api_key:
                os.environ["OPENAI_API_KEY"] = api_key
                st.success("✅ Chiave API impostata!")
            else:
                return

    # Rendering dell'header
    render_header()

    # Bottone di reset 
    tab_col, reset_col = st.columns([8, 1])
    with reset_col:
        if st.button("🧹 Reset", help="Cancella la conversazione e riavvia"):
            reset_conversation()
            # Forza il ricaricamento della pagina per eliminare completamente il file dall'interfaccia
            st.rerun()

    # Gestione delle tab
    with tab_col:
        
        # Usiamo i radio button per simulare le tab
        tab_options = ["📁 Carica un file", "💬 Parla con l'assistente AI"]
        tab_selection = st.radio(
            "Modalità",
            tab_options,
            index=0 if st.session_state.get("active_tab", "file") == "file" else 1,
            horizontal=True,
            label_visibility="collapsed"
        )
        

        if tab_selection == "📁 Carica un file":
            st.session_state.active_tab = "file"  # Aggiorna active_tab
            uploader_key = f"uploader_{st.session_state.session_id}"

            uploaded_file = st.file_uploader(
                label="Carica il file con i dati da analizzare",
                type=["xlsx", "xls", "csv"],
                key=uploader_key
            )

            if uploaded_file:
                st.session_state.uploaded_file = uploaded_file
                st.session_state.file_loaded = True
                st.session_state.default_tab = "file"  # Ricorda dove eri
                st.success(f"✅ Hai caricato: {uploaded_file.name}")

                st.markdown("""<div class="mode-title">Inizia a parlare con l'assistente</div>
                            <div class="mode-subtitle">Fornisci una descrizione dei dati caricati e le istruzioni da eseguire.</div>
                            """, unsafe_allow_html=True)
        elif tab_selection == "💬 Parla con l'assistente AI":
            st.session_state.active_tab = "chat"  # Aggiorna active_tab

            st.markdown("""<div class="mode-title">Inizia a parlare con l'assistente</div>
                        <div class="mode-subtitle">Incolla la tabella direttamente nella chat e fornisci una descrizione dei dati caricati e le istruzioni da eseguire.</div>
                        """, unsafe_allow_html=True)

    # Mostra la cronologia della chat per entrambe le modalità
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            render_user_message(msg["content"])
        else:
            with st.chat_message("assistant"):
                render_response(msg["content"])

    # Mostra l'input di chat se necessario
    should_show_chat_input = (tab_selection == "💬 Parla con l'assistente AI") or (tab_selection == "📁 Carica un file" and st.session_state.file_loaded)
    
    if should_show_chat_input:
        user_input = st.chat_input("Scrivi qualcosa...")
        if user_input:
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            with st.chat_message("assistant"):
                loading_placeholder = st.empty()
                loading_placeholder.markdown("🧠 *Storylaizer sta scrivendo...*")
                risposta = ask_openai(st.session_state.chat_history)
                loading_placeholder.empty()
                render_response(risposta)
                st.session_state.chat_history.append({"role": "assistant", "content": risposta})

if __name__ == "__main__":
    main()