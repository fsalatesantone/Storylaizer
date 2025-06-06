import streamlit as st
import time
import os
import pandas as pd
from dotenv import load_dotenv
import io
import json
from openai import OpenAI
from ui_components import handle_chat_input, render_user_message, render_response, load_css, render_header, display_chat_history, render_conversation_options, render_data_preview, render_download_conversation
from utils import reset_conversation, init_session_state, export_chat, execute_code

max_righe_per_report = 250 # Numero massimo di righe per generare un report
if not os.environ.get("STREAMLIT_SHARING"):
    load_dotenv()

def main():
    st.set_page_config(page_title="Storylaizer",page_icon="img/logo.png", layout="centered")
    load_css()
    init_session_state()
    render_header()

    # Utilizzo st.tabs invece di st.radio
    tab1, tab2, tab3 = st.tabs(["🔍 Data Analyzer", "📝 Report Builder", "🤖 AI Chat"])
    
    # Contenuto della prima tab (Analizza file)
    with tab1:
        st.markdown("""<div class='mode-title'>Analisi esplorativa di un file Excel</div>
                    <div class='mode-subtitle'>L'assistente è in grado di eseguire <strong>analisi dati</strong>, <strong>calcolo di statistiche</strong>
                    , <strong>filtri</strong> e <strong>aggregazioni</strong> sui dati caricati all'interno di un file <strong>Excel</strong>: riesce  
                    ad interpretare le richieste in <i>linguaggio naturale</i> convertendole in istruzioni per l'elaborazione a sistema.<br><br>
                    Prova a chiedere ad esempio di calcolare la <i>media</i> di una colonna o di <i>filtrare</i> le righe in base ad una condizione, facendo attenzione però 
                    a riferirti all'esatto nome della colonna (in caso di errori di battitura nel nome del campo, l'assistente potrebbe non riuscire a rispondere correttamente).
                    Ecco alcuni <strong>esempi</strong> di comandi che puoi provare (ma ce ne sono molti altri!):<br>
                    <ul>
                        <li><em>“Escludendo l'ultima riga che contiene il totale, calcola la media del campo [INSERISCI VARIABILE]”</em></li>
                        <li><em>“Stampa una tabella in cui, per ogni colonna del dataset, venga riportata la deviazione standard corrispondente”</em></li>
                        <li><em>“Filtra tutte le righe in cui il valore di [COLONNA_X] è maggiore di 1000 e mostra solo le prime 10”</em></li>
                        <li><em>“Raggruppa i dati per [COLONNA_Y] e somma il campo [COLONNA_Z] per ciascun gruppo”</em></li>
                    </ul>
                    Se dovessi <strong>ricevere un errore</strong>, prova a riformulare la domanda o a fornire più dettagli sui dati caricati.<br><br>
                    Se invece sei interessato a generare un <strong>report</strong> a partire da un <i>file Excel</i>, passa alla <i>tab</i> <strong>"📝 Report Builder"</strong> in alto.<br>
                    Poi anche decidere di generare un report utilizzando il tab <strong>"🤖 AI Chat"</strong> in alto, in questo caso però dovrai incollare la tabella direttamente nella chat. <br>
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
            st.markdown("""<div class='mode-title'>Scrivi a Storylaizer</div>""", unsafe_allow_html=True)
            display_chat_history(chat_history=st.session_state.chat_history1)
            handle_chat_input(key="1", chat_history=st.session_state.chat_history1)

    with tab2:
        st.markdown(f"""<div class='mode-title'>Generazione automatica di report</div>
                        <div class='mode-subtitle'>L'assistente è in grado di generare uno o più <strong>report</strong> basati sui dati caricati a partire da un file <i>Excel</i>.<br><br>
                    <strong>Linee guida per il prompt:</strong><br>
                    <ol type="1">
                        <li>Fornisci una <strong>descrizione</strong> dettagliata dei dati: specifica il significato delle colonne, il periodo di riferimento, la fonte e il contesto.</li>
                        <li>Poi, specifica le istruzioni di output: ad esempio <i>“Per ciascuna regione presente nel dataset, crea un testo di 500 caratteri e organizza risultati e numeri in una tabella.”</i></li>
                        <li>Ricorda che l’assistente funziona meglio quante <em>più informazioni</em> ha a disposizione: descrivi chiaramente chi sono i destinatari del report, stile linguistico, e lo scopo finale.</li>
                        <li>Se invece hai già un report “esempio” che ti piace (magari per una certa regione), incollalo nel prompt come modello. Ad esempio: 
                            <i>"Ecco il report per la Regione X: [INCOLLA QUI TESTO REPORT]. Genera lo stesso tipo di report per le altre regioni."</i></li>
                    </ol>
                    <strong>Ricorda:</strong> puoi generare report a partire da una <strong>tabella</strong> con un massimo di <strong>{max_righe_per_report} righe</strong>.<br><br>
                    Poi anche decidere di generare un report utilizzando il tab <strong>"🤖 AI Chat"</strong> in alto, in questo caso però dovrai incollare la tabella direttamente nella chat. <br>
                    Se invece sei interessato ad effettuare un'<strong>analisi statistica</strong> o effettuare dei <strong>calcoli</strong>, passa alla <i>tab</i> <strong>"🔍 Data Analyzer"</strong> in alto.
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
            st.markdown("""<div class='mode-title'>Scrivi a Storylaizer</div>""", unsafe_allow_html=True)
            display_chat_history(chat_history=st.session_state.chat_history2)
            handle_chat_input(key="2", chat_history=st.session_state.chat_history2)
            

    
    # Contenuto della terza tab (Chat)
    with tab3: 
        st.markdown(f"""<div class='mode-title'>Dialoga con l'assistente AI</div>
                        <div class='mode-subtitle'>
                        L'assistente AI è a tua disposizione per rispondere a <i>qualsiasi domanda</i> di <strong>statistica</strong>, 
                        <strong>formule matematiche</strong>, <strong>metodologie di analisi</strong> e molto altro.<br><br>
                        Puoi anche utilizzare l'assistente per creare uno o più <strong>report</strong> a partire da dati incollati direttamente nella chat: 
                        ricorda di fornire una breve <i>descrizione</i> dei dati (colonne, periodo di riferimento, fonte, contesto, etc.) e di specificare le <i>istruzioni</i> per l’AI (ad esempio: 
                        <i>"Per ciascuna regione della tabella qui sotto <TABELLA>[INCOLLA QUI I DATI]</TABELLA>, genera un report di 500 caratteri e organizzalo in una tabella."</i>). In questo caso, sappi che è possibile generare report a partire da una <strong>tabella</strong> con un massimo di <strong>{max_righe_per_report} righe</strong>.<br><br>
                        Se invece vuoi interrogare direttamente un file Excel per calcoli avanzati o aggregazioni,
                        torna al tab <strong>"🔍 Data Analyzer"</strong>; per report più strutturati a partire da Excel, 
                        utilizza invece il tab <istrong>"📝 Report Builder"</strong> in alto.
                        </div><br>"""
                    , unsafe_allow_html=True)
        render_conversation_options(tab_key="chat_tab", conversation_started=st.session_state.conversation_started3)
        render_download_conversation(tab_key="chat_tab", chat_history=st.session_state.chat_history3, conversation_started=st.session_state.conversation_started3)
        
        # CORREZIONE: Prima visualizza la cronologia, poi l'input in basso
        st.markdown("""<div class='mode-title'>Scrivi a Storylaizer</div>""", unsafe_allow_html=True)
        display_chat_history(chat_history=st.session_state.chat_history3)
        handle_chat_input(key="3", chat_history=st.session_state.chat_history3)

if __name__ == "__main__":
    main()