import streamlit as st
import time
import os
import pandas as pd
from dotenv import load_dotenv
import io
import json
from openai import OpenAI
from api import get_api_key, ask_openai_analysis, ask_openai_report
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
                risposta = ask_openai_analysis(history = st.session_state.chat_history
                                               , model = st.session_state.get("selected_model", "gpt-4.1-nano") 
                                               , df = st.session_state.get("dataframe", None)
                                               , temperature = st.session_state.get("temperature", 0.7)
                                               , top_p = st.session_state.get("top_p", 1.0)
                )
            # Altrimenti, se siamo nella tab "report" o "chat", chiamiamo l'API per il report
            elif st.session_state.active_tab == "report" or st.session_stat.e.active_tab == "chat":
                risposta = ask_openai_report(history = st.session_state.chat_history
                                             , model = st.session_state.get("selected_model", "gpt-4.1-nano") 
                                             , df = st.session_state.get("dataframe_report", None)
                                             , temperature = st.session_state.get("temperature", 0.7)
                                             , top_p = st.session_state.get("top_p", 1.0)
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
            
            st.markdown("""<div class='mode-title'>Chiedi all'assistente</div>
                        <div class='mode-subtitle'>L'assistente è in grado di eseguire <strong>analisi dati</strong>, <strong>calcolo di statistiche</strong>
                        , <strong>filtri</strong> e <strong>aggregazioni</strong> sui dati.<br>
                        Riesce ad interpretare le richieste in <i>linguaggio naturale</i> convertendole in istruzioni di sistema.<br><br>
                        Prova a chiedere ad esempio di calcolare la <i>media</i> di una colonna o di <i>filtrare</i> le righe in base ad una condizione, facendo attenzione però 
                        a riferirti all'esatto nome della colonna (in caso di errori di battitura nel nome del campo, l'assistente potrebbe non riuscire a rispondere correttamente).
                        Se dovessi ricevere un errore, prova a riformulare la domanda o a fornire più dettagli sui dati caricati.
                        <br><br>
                        Se invece sei interessato a generare un <strong>report</strong> a partire da un <i>file Excel</i>, passa alla <i>tab</i> <strong>"📋 Genera un report"</strong> in alto.<br>
                        Poi anche decidere di generare un report utilizzando il tab <strong>"💬 Parla con l'assistente AI"</strong> in alto, in questo caso però dovrai incollare la tabella direttamente nella chat. <br>
                        </div><br>"""
                        , unsafe_allow_html=True)

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
            
            st.markdown(f"""<div class='mode-title'>Chiedi all'assistente</div>
                        <div class='mode-subtitle'>Fornisci una <i>descrizione</i> dei dati caricati fornendo dettagli sul significato delle colonne, 
                        il periodo di riferimento, la fonte, il contesto e altre informazioni che ritieni utili.<br>
                        Successivamente specifica le <strong>istruzioni</strong> che l'assistente AI deve eseguire (es. <i>"genera un report di 500 caratteri, uno per ciascuna regione, ..."</i>).<br>
                        Ricorda che è possibile generare report a partire da una tabella con un massimo di <strong>{max_righe_per_report} righe</strong>.
                        <br><br>
                        Poi anche decidere di generare un report utilizzando il tab <strong>"💬 Parla con l'assistente AI"</strong> in alto, in questo caso però dovrai incollare la tabella direttamente nella chat. <br>
                        Se invece sei interessato ad effettuare un'<strong>analisi statistica</strong> o effettuare dei <strong>calcoli</strong>, passa alla <i>tab</i> <strong>"📊 Analizza un file"</strong> in alto.
                        </div><br>"""
                        , unsafe_allow_html=True)

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
        st.markdown(f"""<div class='mode-title'>Chiedi all'assistente</div>
                    <div class='mode-subtitle'>Fornisci all'assistente dei dati sui quali generare un report, incollandoli direttamente nella chat.<br>
                    Riporta anche una <i>descrizione</i> dei dati caricati fornendo dettagli sul significato delle colonne, 
                    il periodo di riferimento, la fonte, il contesto e altre informazioni che ritieni utili.<br>
                    Successivamente specifica le <strong>istruzioni</strong> che l'assistente AI deve eseguire (es. <i>"genera un report di 500 caratteri, uno per ciascuna regione, ..."</i>).<br>
                    Ricorda che è possibile generare report a partire da una tabella con un massimo di <strong>{max_righe_per_report} righe</strong>.<br><br>
                    Puoi anche decidere di generare un <strong>report</strong> a partire da un <i>file Excel</i>: passa alla <i>tab</i> <strong>"📋 Genera un report"</strong> in alto.<br>
                    Se invece sei interessato ad effettuare un'<strong>analisi statistica</strong> o a calcolare <strong>metriche</strong> specifiche, vai alla <i>tab</i> <strong>"📊 Analizza un file"</strong> in alto.
                    </div><br>"""
                    , unsafe_allow_html=True)
        
        # CORREZIONE: Prima visualizza la cronologia, poi l'input in basso
        display_chat_history()
        handle_chat_input(key="chat_input_chat_tab")

if __name__ == "__main__":
    main()