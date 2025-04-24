import streamlit as st
import json
import re
import time
import os
from openai import OpenAI

# Prova a importare la chiave API dal file di configurazione
try:
    from config import OPENAI_API_KEY
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
except ImportError:
    pass  # Se il file non esiste, procedi senza importarlo

def ask_openai(messages_history):
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    system_prompt = (
        "Sei un esperto di analisi di dati statistici ufficiali. "
        "Rispondi sempre in italiano. "
        "Quando analizzi i dati di una tabella, fai attenzione a riportare sempre i valori corretti evitando allucinazioni."
    )

    api_messages = [{"role": "system", "content": system_prompt}]
    for msg in messages_history:
        api_messages.append({"role": msg["role"], "content": msg["content"]})

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=api_messages,
            stream=False
        )

        full_response = response.choices[0].message.content
        cleaned_response = re.sub(r"<think>.*?</think>", "", full_response, flags=re.DOTALL).strip()
        return cleaned_response

    except Exception as e:
        return f"Errore nella chiamata a OpenAI: {str(e)}"

def render_user_message(message):
    st.markdown(
        f"""
        <div style='display: flex; justify-content: flex-end; margin-top: 1rem;'>
            <div style='background-color: #e6f0fa; padding: 10px 15px; border-radius: 15px; max-width: 80%; text-align: right;'>
                <div style='color: #1f77b4; font-size: 1.2rem; margin-bottom: 5px;'>👋</div>
                <div style='color: #000;'>{message}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_response(content):
    latex_blocks = re.findall(r"\\boxed\{.*?\}", content)

    if latex_blocks:
        parts = re.split(r"(\\boxed\{.*?\})", content)
        for part in parts:
            if part.startswith("\\boxed"):
                st.latex(part)
            else:
                st.markdown(part, unsafe_allow_html=False)
    else:
        st.markdown(content, unsafe_allow_html=False)

def reset_conversation():
    # Salva la tab corrente prima di resettare
    current_tab = st.session_state.active_tab
    
    # Genera un nuovo ID di sessione per forzare il ricaricamento dell'uploader
    st.session_state.session_id = str(time.time())
    
    # Reset completo delle variabili di sessione
    for key in list(st.session_state.keys()):
        if key not in ["active_tab", "session_id"]:
            del st.session_state[key]
    
    # Reinizializza le variabili necessarie
    st.session_state.chat_history = []
    st.session_state.file_loaded = False
    st.session_state.selected_mode = None
    st.session_state.uploaded_file = None
    
    # Mantieni la tab corrente
    st.session_state.active_tab = current_tab

def main():
    st.set_page_config(page_title="Storylaizer", layout="centered")

    # Inizializzazione delle variabili di stato
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

    # CSS
    st.markdown("""
        <style>
        .box-container {
            display: flex;
            gap: 20px;
            margin: 30px 0;
        }
        .box-option {
            flex: 1;
            border: 2px solid #ccc;
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            transition: all 0.3s ease;
            background-color: #f9f9f9;
        }
        .box-option:hover {
            border-color: #26B6DA;
            box-shadow: 0 0 12px rgba(38, 182, 218, 0.3);
        }
        .box-option.selected {
            border-color: #0F3D6E;
            background-color: #e6f0fa;
            box-shadow: 0 0 15px rgba(15, 61, 110, 0.3);
        }
        .mode-title {
            font-size: 20px;
            font-weight: bold;
            color: #0F3D6E;
            margin-top: 10px;
        }
        .mode-subtitle {
            font-size: 14px;
            color: #444;
            margin-top: 5px;
        }
        .file-uploader-container {
            margin-top: 10px;
        }
        /* Nuovi stili per l'header */
        .header-container {
            display: flex;
            align-items: center;
            margin-bottom: 20px;
        }
        .logo-container {
            flex: 2;
            display: flex;
            justify-content: center;
        }
        .title-container {
            flex: 6;
            padding-left: 0px;
        }
        .app-title {
            margin-bottom: 0;
            line-height: 1.2;
        }
        .app-subtitle {
            font-style: italic;
            margin-top: 0;
            line-height: 1.1;
        }
        </style>
    """, unsafe_allow_html=True)

    # Header
    col1, col2 = st.columns([2, 6])
    with col1:
        st.image("./img/logo.png", width=150)
    with col2:
        st.markdown("""
                    <div class="title-container">
                        <h1 class="app-title">
                            <span style="color:#0F3D6E;">Storyl</span><span style="color:#26B6DA;">ai</span><span style="color:#0F3D6E;">zer</span>
                        </h1>
                        <h6 class="app-subtitle" style="color:#0F3D6E;">Trasforma i tuoi dati in analisi AI-driven</h6>
                    </div>
        """, unsafe_allow_html=True)

    # Bottone di reset 
    tab_col, reset_col = st.columns([8, 1])
    with reset_col:
        if st.button("🧹 Reset", help="Cancella la conversazione e riavvia"):
            reset_conversation()
            # Forza il ricaricamento della pagina per eliminare completamente il file dall'interfaccia
            st.rerun()

    # Gestione delle tab
    with tab_col:
        # Determina il valore predefinito per il radio button in base alla tab attiva
        default_index = 0 if st.session_state.active_tab == "file" else 1
        
        # Usiamo i radio button per simulare le tab (più facili da controllare)
        tab_options = ["📁 Carica un file", "💬 Parla con l'assistente AI"]
        tab_selection = st.radio(
            "Modalità",
            tab_options,
            index=default_index,
            horizontal=True,
            label_visibility="collapsed"
        )
        
        if tab_selection == "📁 Carica un file":
            st.session_state.active_tab = "file"
            
            # Utilizziamo una chiave univoca basata sulla sessione per l'uploader
            uploader_key = f"uploader_{st.session_state.session_id}"
            uploaded_file = st.file_uploader(
                label="Carica il file con i dati da analizzare", 
                type=["xlsx", "xls", "csv"],
                key=uploader_key
            )

            if uploaded_file:
                st.session_state.uploaded_file = uploaded_file
                st.success(f"✅ Hai caricato: {uploaded_file.name}")
                st.session_state.file_loaded = True
                st.session_state.selected_mode = "file"

                st.markdown("""<div class="mode-title">Inizia a parlare con l'assistente</div>
                            <div class="mode-subtitle">Fornisci una descrizione dei dati caricati e le istruzioni da eseguire.</div>
                            """, unsafe_allow_html=True)
        else:  # "💬 Parla con l'assistente AI"
            st.session_state.active_tab = "chat"
            st.session_state.selected_mode = "chat"
            
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

    # Mostra l'input di chat SOLO se:
    # 1. L'utente è nella tab "Parla con l'assistente AI" OPPURE
    # 2. Un file è stato caricato nella tab "Carica un file"
    should_show_chat_input = (st.session_state.active_tab == "chat") or (st.session_state.active_tab == "file" and st.session_state.file_loaded)
    
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