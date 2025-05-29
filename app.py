import streamlit as st
import time
import os
import pandas as pd
from dotenv import load_dotenv
import io
import json
from openai import OpenAI

from api import ask_openai, ask_openai_with_data, build_system_prompt_code_executor
from ui_components import render_user_message, render_response, load_css, render_header, display_chat_history, render_conversation_options, render_data_preview, render_download_conversation
from utils import reset_conversation, init_session_state, export_chat

if not os.environ.get("STREAMLIT_SHARING"):
    load_dotenv()

def get_api_key():
    api_key = st.secrets.get("OPENAI_API_KEY", None) if hasattr(st, "secrets") else None
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY")
    return api_key


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
            # Se la domanda contiene analisi dati, facciamo function-calling
            if st.session_state.dataframe is not None:
                from utils import execute_code
			
				# Chiediamo al modello di produrre Python
                client = OpenAI(api_key=get_api_key())
                fc = client.chat.completions.create(
					model=st.session_state.selected_model,
					messages=[{"role":"system","content":build_system_prompt_code_executor()}]
							+ st.session_state.chat_history
							+ [{"role":"user","content":user_input}],
					functions=[{"name":"execute_code", "description":"Esegue codice su df",
								"parameters":{"type":"object","properties":{"code":{"type":"string"}},"required":["code"]}}],
					function_call="auto"
				)
                function_call = fc.choices[0].message.function_call

                if function_call and hasattr(function_call, "arguments"):
                    code_data = json.loads(function_call.arguments)
                    code = code_data.get("code", "")
                else:
                    code = None 
                result = execute_code(code, st.session_state.dataframe)
                risposta = str(result)
            else:
                risposta = ask_openai_with_data(st.session_state.chat_history
                                                , model=st.session_state.get("selected_model", "gpt-4.1-nano")
                                                , dataframe=st.session_state.get("dataframe", None)
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
        with st.expander("📂 Carica il file", expanded=True):
            uploaded_file = st.file_uploader(label="Seleziona un file Excel con i dati da analizzare", type=["xlsx"], key=uploader_key)
            if uploaded_file:
                # Scelta dello Sheet
                xls = pd.ExcelFile(uploaded_file)
                sheet_names = xls.sheet_names
                selected_sheet = st.selectbox("📑 Seleziona il foglio", options=sheet_names, index=0)
                df = pd.read_excel(uploaded_file, sheet_name=selected_sheet)
                st.session_state.dataframe = df

                #st.session_state.uploaded_file = uploaded_file
                st.session_state.file_loaded = True
                st.success(f"✅ Hai caricato: {uploaded_file.name} (sheet: {selected_sheet})")
                
                # Anteprima dei dati caricati
                render_data_preview(df)
                        
        # Area di chat dopo il caricamento del file
        if st.session_state.file_loaded:
            
            # Opzioni di conversazione e download
            render_conversation_options(tab_key="file_tab")
            render_download_conversation(tab_key="file_tab")
            
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