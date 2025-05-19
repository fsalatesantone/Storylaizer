import streamlit as st
import time
import os
import pandas as pd
from dotenv import load_dotenv
import io

from api import ask_openai
from ui_components import render_user_message, render_response, load_css, render_header
from utils import reset_conversation, init_session_state, export_chat

if not os.environ.get("STREAMLIT_SHARING"):
    load_dotenv()

def get_api_key():
    api_key = st.secrets.get("OPENAI_API_KEY", None) if hasattr(st, "secrets") else None
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY")
    return api_key

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

    if "tab_index" not in st.session_state:
        st.session_state.tab_index = 0 if st.session_state.active_tab == "file" else 1

    tab_options = ["📁 Carica un file", "💬 Parla con l'assistente AI"]
    selected_tab = st.radio("Modalità", tab_options, index=st.session_state.tab_index, horizontal=True, label_visibility="collapsed")

    if selected_tab == "📁 Carica un file":
        st.session_state.tab_index = 0
        st.session_state.active_tab = "file"
    else:
        st.session_state.tab_index = 1
        st.session_state.active_tab = "chat"

    if st.session_state.active_tab == "file":
        uploader_key = f"uploader_{st.session_state.session_id}"
        uploaded_file = st.file_uploader("Carica il file con i dati da analizzare", type=["xlsx", "xls", "csv"], key=uploader_key)
        if uploaded_file:
            st.session_state.uploaded_file = uploaded_file
            st.session_state.file_loaded = True
            st.success(f"✅ Hai caricato: {uploaded_file.name}")
            st.markdown("<div class='mode-title'>Inizia a parlare con l'assistente</div><div class='mode-subtitle'>Fornisci una descrizione dei dati caricati e le istruzioni da eseguire.</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='mode-title'>Inizia a parlare con l'assistente</div><div class='mode-subtitle'>Incolla la tabella direttamente nella chat e fornisci una descrizione dei dati caricati e le istruzioni da eseguire.</div><br>", unsafe_allow_html=True)
        # EXPANDER - Pulsanti alti e disabilitati se nessuna chat è iniziata
        with st.expander("⚙️ Opzioni conversazione", expanded=False):

            disabilita = not st.session_state.get("conversation_started", False)

            st.button("🧹 Reset conversazione", on_click=reset_conversation, disabled=disabilita)

            formati = {"📊 XLSX": "XLSX", "📝 DOCX": "DOCX", "📄 TXT": "TXT"}
            formato_label = st.selectbox(
                "📂 Seleziona formato di esportazione:",
                list(formati.keys()),
                key="export_format_simple",
                disabled=disabilita
            )
            formato = formati[formato_label]

            export_result = export_chat(formato.lower()) if not disabilita else None

            st.download_button(
                label=f"📥 Download conversazione [{formato}]",
                data=export_result[0] if export_result else b"",
                file_name=export_result[2] if export_result else "",
                mime=export_result[1] if export_result else "",
                disabled=disabilita
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
                key="openai_model_selection",
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
                disabled=False
            )

            st.session_state["top_p"] = st.slider(
                "🎯 Top-p (default: 1.0):",
                min_value=0.0,
                max_value=1.0,
                value=1.0,
                step=0.05,
                disabled=False
            )


    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            render_user_message(msg["content"])
        else:
            with st.chat_message("assistant"):
                render_response(msg["content"])

    should_show_chat_input = (st.session_state.active_tab == "chat") or (st.session_state.active_tab == "file" and st.session_state.file_loaded)

    # --- Gestione input utente e risposta assistant con pending_user_message ---
    if "pending_user_message" not in st.session_state:
        st.session_state.pending_user_message = None
    if "conversation_started" not in st.session_state:
        st.session_state.conversation_started = False

    should_show_chat_input = (st.session_state.active_tab == "chat") or (st.session_state.active_tab == "file" and st.session_state.file_loaded)

    if should_show_chat_input:
        # Se c'è un messaggio pendente (dopo un rerun), gestiscilo
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
                                      , model=st.session_state["selected_model"]
                                      , temperature=st.session_state["temperature"]
                                      , top_p=st.session_state["top_p"]
                                      )
                loading_placeholder.empty()
                render_response(risposta)
                st.session_state.chat_history.append({"role": "assistant", "content": risposta})

            st.rerun()

        # Altrimenti mostra il campo input
        user_input = st.chat_input("Scrivi qualcosa...")
        if user_input:
            st.session_state.pending_user_message = user_input
            st.rerun()

if __name__ == "__main__":
    main()