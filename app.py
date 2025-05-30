import streamlit as st
import time
import os
import pandas as pd
from dotenv import load_dotenv
import io
import json
from openai import OpenAI

from api import get_api_key, ask_openai_with_data, build_system_prompt_code_executor, ask_openai_analysis, ask_openai_report
from ui_components import render_user_message, render_response, load_css, render_header, display_chat_history, render_conversation_options, render_data_preview, render_download_conversation
from utils import reset_conversation, init_session_state, export_chat, execute_code

max_righe_per_report = 250 # Numero massimo di righe per generare un report

if not os.environ.get("STREAMLIT_SHARING"):
    load_dotenv()


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
            # Se siamo nel tabl "file" e la domanda contiene analisi dati, facciamo function-calling 
            if st.session_state.get("dataframe") is not None and st.session_state.active_tab == "file":
			
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

# def process_user_message(user_input: str) -> str:
#     """
#     Dispatcha la richiesta utente alla funzione corretta in base alla tab attiva.
#     """
#     tab = st.session_state.active_tab
#     history = st.session_state.chat_history + [{"role":"user","content":user_input}]
#     model = st.session_state.selected_model
#     temp  = st.session_state.temperature
#     top_p = st.session_state.top_p

#     if tab == "file" and st.session_state.get("dataframe") is not None:
#         return ask_openai_analysis(history, model, st.session_state.dataframe, temp, top_p)
#     elif tab == "report" and st.session_state.get("dataframe_report") is not None:
#         return ask_openai_report(history, model, st.session_state.dataframe_report, temp, top_p)
#     else:
#         # fallback generico senza dataframe
#         return ask_openai_with_data(history, model, None, temp, top_p)

# def handle_chat_input(key):
#     """Gestione semplificata dell'input chat."""
#     user_input = st.chat_input("Scrivi qualcosa...", key=key)
#     if not user_input:
#         return
#     # render e storico
#     render_user_message(user_input)
#     st.session_state.chat_history.append({"role":"user","content":user_input})
#     st.session_state.conversation_started = True

#     # genera risposta
#     with st.chat_message("assistant"):
#         placeholder = st.empty()
#         placeholder.markdown("🧠 *Storylaizer sta scrivendo...*")
#         risposta = process_user_message(user_input)
#         placeholder.empty()
#         render_response(risposta)

#     st.session_state.chat_history.append({"role":"assistant","content":risposta})
    

def main():
    st.set_page_config(page_title="Storylaizer", layout="centered")
    load_css()
    init_session_state()
    render_header()

    # Tieni traccia della tab precedente per gestire il reset quando si cambia tab
    if "previous_tab" not in st.session_state:
        st.session_state.previous_tab = "file"  # Valore iniziale

    # Inizializza lo stato della tab attiva se non esiste
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "file"  # Default alla tab dei file

    # Utilizzo st.tabs invece di st.radio
    tab1, tab2, tab3 = st.tabs(["📊 Analizza un file", "📋 Genera un report", "💬 Parla con l'assistente AI"])
    
    # Contenuto della prima tab (Analizza file)
    with tab1:
        # Se abbiamo cambiato tab dalla chat alla tab file, resettiamo la chat
        if ((st.session_state.previous_tab == "chat" and st.session_state.active_tab == "file")
            or (st.session_state.previous_tab == "report" and st.session_state.active_tab == "file")):
            if "conversation_started" in st.session_state and st.session_state.conversation_started:
                reset_conversation()
                st.session_state.conversation_started = False
        
        # Aggiorna lo stato della tab
        st.session_state.active_tab = "file"
        st.session_state.previous_tab = "file"
        
        uploader_key1 = f"uploader1_{st.session_state.session_id}"
        with st.expander("📂 Carica il file da analizzare", expanded=True):
            uploaded_file1 = st.file_uploader(label="Seleziona un file Excel con i dati da analizzare", type=["xlsx"], key=uploader_key1)
            if uploaded_file1:
                # Scelta dello Sheet
                xls = pd.ExcelFile(uploaded_file1)
                sheet_names = xls.sheet_names
                selected_sheet = st.selectbox("📑 Seleziona il foglio", options=sheet_names, index=0, key=f"sheet_sel1_{st.session_state.session_id}")
                df = pd.read_excel(uploaded_file1, sheet_name=selected_sheet)
                st.session_state.dataframe = df

                st.session_state.file_loaded1 = True
                st.success(f"✅ Hai caricato: {uploaded_file1.name} (sheet: {selected_sheet})")
                
                # Anteprima dei dati caricati
                render_data_preview(df)
                        
        # Area di chat dopo il caricamento del file
        if st.session_state.file_loaded1:
            
            # Opzioni di conversazione e download
            render_conversation_options(tab_key="file_tab")
            render_download_conversation(tab_key="file_tab")
            
            st.markdown("<div class='mode-title'>Inizia a parlare con l'assistente</div><div class='mode-subtitle'>Fornisci una descrizione dei dati caricati e le istruzioni da eseguire.</div>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            # CORREZIONE: Prima visualizza la cronologia, poi l'input in basso
            display_chat_history()
            handle_chat_input(key="chat_input_file_tab")


    with tab2:
        # Se abbiamo cambiato tab dalla chat alla tab file, resettiamo la chat
        if ((st.session_state.previous_tab == "chat" and st.session_state.active_tab == "file")
            or (st.session_state.previous_tab == "report" and st.session_state.active_tab == "file")):
            if "conversation_started" in st.session_state and st.session_state.conversation_started:
                reset_conversation()
                st.session_state.conversation_started = False
        
        # Aggiorna lo stato della tab
        st.session_state.active_tab = "report"
        st.session_state.previous_tab = "report"
        n_righe_file = 0
        
        uploader_key2 = f"uploader2_{st.session_state.session_id}"
        with st.expander("📂 Carica il file per il report", expanded=True):
            uploaded_file2 = st.file_uploader(label="Seleziona un file Excel per generare un report", type=["xlsx"], key=uploader_key2)
            if uploaded_file2:
                # Scelta dello Sheet
                xls = pd.ExcelFile(uploaded_file2)
                sheet_names = xls.sheet_names
                selected_sheet = st.selectbox("📑 Seleziona il foglio", options=sheet_names, index=0, key=f"sheet_sel2_{st.session_state.session_id}")
                df = pd.read_excel(uploaded_file2, sheet_name=selected_sheet)
                st.session_state.dataframe_report = df

                st.session_state.file_loaded2 = True
                st.success(f"✅ Hai caricato: {uploaded_file2.name} (sheet: {selected_sheet})")
                
                # Anteprima dei dati caricati
                render_data_preview(df)
                n_righe_file = df.shape[0]

                if n_righe_file > max_righe_per_report:
                    st.markdown(f"<div class='mode-title' style='color: red;'>ATTENZIONE: Il file è troppo grande per la generazione di report</div><div class='mode-subtitle' style='color: red;'>Il file contiene {n_righe_file} righe, il sistema può generare report a partire da un massimo di 250. Carica un file più piccolo.</div><br>", unsafe_allow_html=True)

                        
        # Area di chat dopo il caricamento del file
        if st.session_state.file_loaded2 and n_righe_file <= max_righe_per_report:
            
            # Opzioni di conversazione e download
            render_conversation_options(tab_key="report_tab")
            render_download_conversation(tab_key="report_tab")
            
            st.markdown("<div class='mode-title'>Inizia a parlare con l'assistente</div><div class='mode-subtitle'>Fornisci una descrizione dei dati caricati e le istruzioni da eseguire.</div>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            # CORREZIONE: Prima visualizza la cronologia, poi l'input in basso
            display_chat_history()
            handle_chat_input(key="chat_report_tab")
            

    
    # Contenuto della terza tab (Chat)
    with tab3:
        # Se abbiamo cambiato tab dalla tab file alla chat, aggiorniamo lo stato
        if ((st.session_state.previous_tab == "chat" and st.session_state.active_tab == "file")
            or (st.session_state.previous_tab == "report" and st.session_state.active_tab == "file")):
            if "conversation_started" in st.session_state and st.session_state.conversation_started:
                reset_conversation()
                st.session_state.conversation_started = False
        
        # Aggiorna lo stato della tab
        st.session_state.active_tab = "chat"
        st.session_state.previous_tab = "chat"
        
        # EXPANDER - Opzioni con chiave specifica per la tab
        render_conversation_options(tab_key="chat_tab")
        st.markdown("<div class='mode-title'>Inizia a parlare con l'assistente</div><div class='mode-subtitle'>Incolla la tabella direttamente nella chat e fornisci una descrizione dei dati caricati e le istruzioni da eseguire.</div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        # CORREZIONE: Prima visualizza la cronologia, poi l'input in basso
        display_chat_history()
        handle_chat_input(key="chat_input_chat_tab")

if __name__ == "__main__":
    main()