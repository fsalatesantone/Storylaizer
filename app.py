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

def handle_chat_input(key, chat_history):
    """Gestisce l'input della chat con una chiave univoca"""
    pending_key = f"pending_user_message{key}"
    if pending_key not in st.session_state:
        st.session_state[pending_key] = None
    
    if st.session_state[pending_key]:
        user_input = st.session_state[pending_key]
        st.session_state[pending_key] = None
        
        render_user_message(user_input)
        chat_history.append({"role": "user", "content": user_input})
        st.session_state[f"conversation_started{key}"] = True
        
        with st.chat_message("assistant"):
            loading_placeholder = st.empty()
            loading_placeholder.markdown("🧠 *Storylaizer sta scrivendo...*")

            # Scelgo il DataFrame e la funzione di OpenAI in base alla tab (key)
            if key == "1": # Se siamo nel tab 1 e la domanda contiene analisi dati, facciamo function-calling 
                risposta = ask_openai_analysis(history = chat_history
                                            , model = st.session_state.get("selected_model", "gpt-4.1-nano")
                                            , df = st.session_state.get("dataframe", None)
                                            , temperature = st.session_state.get("temperature", 0.7)
                                            , top_p = st.session_state.get("top_p", 1.0)
                                            )
            elif key == "2": # Nel tab 2 non deve fare function-calling, ma solo report
                risposta = ask_openai_report(history = chat_history
                                             , model = st.session_state.get("selected_model", "gpt-4.1-nano") 
                                             , df = st.session_state.get("dataframe_report", None)
                                             , temperature = st.session_state.get("temperature", 0.7)
                                             , top_p = st.session_state.get("top_p", 1.0)
                                            )
            else:  # key == "3" # Nel tab 3 non deve fare function-calling, ma solo report (ma senza dati importati da excel)
                risposta = ask_openai_report(history = chat_history
                                             , model = st.session_state.get("selected_model", "gpt-4.1-nano") 
                                             , df = None
                                             , temperature = st.session_state.get("temperature", 0.7)
                                             , top_p = st.session_state.get("top_p", 1.0)
                                            )
            loading_placeholder.empty()
            render_response(risposta)
            chat_history.append({"role": "assistant", "content": risposta})
        
        st.rerun()
    
    # Altrimenti mostra il campo input con chiave univoca
    user_input = st.chat_input("Scrivi qualcosa...", key=key)
    if user_input:
        #st.session_state.pending_user_message = user_input
        st.session_state[pending_key] = user_input
        st.rerun()
    

def main():
    st.set_page_config(page_title="Storylaizer", layout="centered")
    load_css()
    init_session_state()
    render_header()

    # Utilizzo st.tabs invece di st.radio
    tab1, tab2, tab3 = st.tabs(["📊 Analizza un file", "📋 Genera un report", "💬 Parla con l'assistente AI"])
    
    # Contenuto della prima tab (Analizza file)
    with tab1:
        st.markdown("""<div class='mode-title'>Analizza un file</div>
                    <div class='mode-subtitle'>L'assistente è in grado di eseguire <strong>analisi dati</strong>, <strong>calcolo di statistiche</strong>
                    , <strong>filtri</strong> e <strong>aggregazioni</strong> sui dati caricati all'interno di un file <strong>Excel</strong>: riesce  
                    ad interpretare le richieste in <i>linguaggio naturale</i> convertendole in istruzioni per l'elaborazione a sistema.<br><br>
                    Prova a chiedere ad esempio di calcolare la <i>media</i> di una colonna o di <i>filtrare</i> le righe in base ad una condizione, facendo attenzione però 
                    a riferirti all'esatto nome della colonna (in caso di errori di battitura nel nome del campo, l'assistente potrebbe non riuscire a rispondere correttamente).
                    Se dovessi ricevere un errore, prova a riformulare la domanda o a fornire più dettagli sui dati caricati.
                    <br><br>
                    Se invece sei interessato a generare un <strong>report</strong> a partire da un <i>file Excel</i>, passa alla <i>tab</i> <strong>"📋 Genera un report"</strong> in alto.<br>
                    Poi anche decidere di generare un report utilizzando il tab <strong>"💬 Parla con l'assistente AI"</strong> in alto, in questo caso però dovrai incollare la tabella direttamente nella chat. <br>
                    </div><br>"""
                    , unsafe_allow_html=True)
        
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
            render_conversation_options(tab_key="file_tab", conversation_started=st.session_state.conversation_started1)
            render_download_conversation(tab_key="file_tab", chat_history=st.session_state.chat_history1, conversation_started=st.session_state.conversation_started1)

            # Visualizza la cronologia, poi l'input in basso
            display_chat_history(chat_history=st.session_state.chat_history1)
            handle_chat_input(key="1", chat_history=st.session_state.chat_history1)

    with tab2:
        st.markdown(f"""<div class='mode-title'>Genera un report</div>
                        <div class='mode-subtitle'>L'assistente è in grado di generare uno o più <strong>report</strong> basati sui dati caricati a partire da un file <i>Excel</i>.<br><br>
                    Fornisci una <i>descrizione</i> dei dati caricati specificando dettagli sul significato delle colonne, 
                        il periodo di riferimento, la fonte, il contesto e altre informazioni che ritieni utili.<br>
                        Successivamente specifica le <strong>istruzioni</strong> che l'assistente AI deve eseguire (es. <i>"Per ciascuna regione presente nel dataset, genera un report di 500 caratteri e organizzalo in una tabella..."</i>).<br>
                        Ricorda che è possibile generare report a partire da una tabella con un massimo di <strong>{max_righe_per_report} righe</strong>.
                        <br><br>
                        Poi anche decidere di generare un report utilizzando il tab <strong>"💬 Parla con l'assistente AI"</strong> in alto, in questo caso però dovrai incollare la tabella direttamente nella chat. <br>
                        Se invece sei interessato ad effettuare un'<strong>analisi statistica</strong> o effettuare dei <strong>calcoli</strong>, passa alla <i>tab</i> <strong>"📊 Analizza un file"</strong> in alto.
                        </div><br>"""
                        , unsafe_allow_html=True)

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
            render_conversation_options(tab_key="report_tab", conversation_started=st.session_state.conversation_started2)
            render_download_conversation(tab_key="report_tab", chat_history=st.session_state.chat_history2, conversation_started=st.session_state.conversation_started2)

            # CORREZIONE: Prima visualizza la cronologia, poi l'input in basso
            display_chat_history(chat_history=st.session_state.chat_history2)
            handle_chat_input(key="2", chat_history=st.session_state.chat_history2)
            

    
    # Contenuto della terza tab (Chat)
    with tab3: 
        st.markdown(f"""<div class='mode-title'>Parla con l'assistente AI</div>
                    <div class='mode-subtitle'>L'assistente è in grado di generare uno o più <strong>report</strong> a partire da dati incollati direttamente nella chat.<br><br>
                    E' consigliato riportare anche una <i>descrizione</i> dei dati caricati, fornendo dettagli sul significato delle colonne, 
                    il periodo di riferimento, la fonte, il contesto e altre informazioni che ritieni utili.<br>
                    Successivamente specifica le <strong>istruzioni</strong> che l'assistente AI deve eseguire (es. <i>"Per ciascuna regione della seguente tabella <TABELLA>[COPIA QUI I DATI]</TABELLA>, genera un report di 500 caratteri e organizzalo in una tabella..."</i>).<br>
                    Ricorda che è possibile generare report a partire da una tabella con un massimo di <strong>{max_righe_per_report} righe</strong>.<br><br>
                    Puoi anche decidere di generare un <strong>report</strong> a partire da un <i>file Excel</i>: passa alla <i>tab</i> <strong>"📋 Genera un report"</strong> in alto.<br>
                    Se invece sei interessato ad effettuare un'<strong>analisi statistica</strong> o a calcolare <strong>metriche</strong> specifiche, vai alla <i>tab</i> <strong>"📊 Analizza un file"</strong> in alto.
                    </div><br>"""
                    , unsafe_allow_html=True)
        render_conversation_options(tab_key="chat_tab", conversation_started=st.session_state.conversation_started3)
        render_download_conversation(tab_key="chat_tab", chat_history=st.session_state.chat_history3, conversation_started=st.session_state.conversation_started3)
        
        # CORREZIONE: Prima visualizza la cronologia, poi l'input in basso
        display_chat_history(chat_history=st.session_state.chat_history3)
        handle_chat_input(key="3", chat_history=st.session_state.chat_history3)

if __name__ == "__main__":
    main()