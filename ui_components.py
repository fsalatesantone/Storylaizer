import streamlit as st
import re
import pandas as pd
from utils import reset_conversation, export_chat
from api import get_api_key, ask_openai_analysis, ask_openai_report

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

def render_user_message(message):
    st.markdown(
        f"""
        <div style='display: flex; justify-content: flex-end; margin-top: 1rem;'>
            <div style='background-color: #e6f0fa; padding: 10px 15px; border-radius: 15px; max-width: 80%; text-align: right;'>
                <div style='color: #000;'>{message}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_response(content):
    """
    Renderizza il contenuto gestendo formule LaTeX e testo normale.
    Mantiene il flusso del testo senza andare a capo inappropriatamente.
    """
    # Pattern per le formule LaTeX
    # Cattura: $$...$$, $...$ (ma non singoli $ isolati), \[...\]
    latex_pattern = r'(\$\$[^$]+\$\$|\$[^$\s][^$]*[^$\s]\$|\\\[[^\]]*\\\])'
    
    # Dividi il contenuto in parti: testo normale e formule LaTeX
    parts = re.split(latex_pattern, content, flags=re.DOTALL)
    
    # Ricostruisci il contenuto processando le formule LaTeX
    processed_content = ""
    
    for i, part in enumerate(parts):
        if not part:  # Salta parti vuote
            continue
            
        # Controlla se è una formula LaTeX
        if re.match(latex_pattern, part):
            # Gestisci le diverse tipologie di formule LaTeX
            if part.startswith("$$") and part.endswith("$$"):
                # Formula display (block) - la rendiamo separatamente
                if processed_content.strip():
                    # Renderizza il testo accumulato finora
                    st.markdown(processed_content, unsafe_allow_html=True)
                    processed_content = ""
                
                # Renderizza la formula display
                formula = part[2:-2].strip()  # Rimuovi $$ ... $$
                formula = formula.replace("%", r"\%")
                st.latex(formula)
                
            elif part.startswith("\\[") and part.endswith("\\]"):
                # Formula display con \[ ... \]
                if processed_content.strip():
                    st.markdown(processed_content, unsafe_allow_html=True)
                    processed_content = ""
                
                formula = part[2:-2].strip()  # Rimuovi \[ ... \]
                formula = formula.replace("%", r"\%")
                st.latex(formula)
                
            elif part.startswith("$") and part.endswith("$"):
                # Formula inline - la includiamo nel testo
                formula = part[1:-1]  # Rimuovi $ ... $
                formula = formula.replace("%", r"\%")
                # Mantieni la formula inline nel flusso del testo
                processed_content += f"${formula}$"
        else:
            # È testo normale - lo aggiungiamo al contenuto processato
            processed_content += part
    
    # Renderizza l'eventuale contenuto rimanente
    if processed_content.strip():
        st.markdown(processed_content, unsafe_allow_html=True)


def load_css():
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

def render_header():
    st.image("./img/storylaizer_logo.png")


def display_chat_history(chat_history):
    """Visualizza la cronologia delle chat"""
    for msg in chat_history:
        if msg["role"] == "user":
            render_user_message(msg["content"])
        else:
            with st.chat_message("assistant"):
                render_response(msg["content"])


def render_data_preview(df):
    # Anteprima
    st.markdown("<div class='mode-title'>Tabella Dati</div>", unsafe_allow_html=True)
    st.markdown(f"""**{df.shape[0]}** righe, **{df.shape[1]}** colonne""", unsafe_allow_html=True)
    st.dataframe(df)

    # Statistiche principali
    st.markdown("<div class='mode-title'>Statistiche descrittive</div>", unsafe_allow_html=True)

    # Costruisco il DataFrame di summary
    stats = pd.DataFrame(index=df.columns)
    stats["dtype"]   = df.dtypes.astype(str)
    stats["missing"] = df.isna().sum()
    stats["distinct"] = df.nunique()
    # Applico solo alle colonne numeriche
    numeric = df.select_dtypes(include="number")
    stats["min"]    = numeric.min()
    stats["q1"]     = numeric.quantile(0.25).round(2)
    stats["median"] = numeric.median().round(2)
    stats["mean"]   = numeric.mean().round(2)
    stats["q3"]     = numeric.quantile(0.75).round(2)
    stats["max"]    = numeric.max()
    stats["std"]    = numeric.std().round(2)
    stats["cv"]     = (numeric.std() / numeric.mean()).round(2)
    # Mostro statistiche
    st.dataframe(stats)

def render_download_conversation(tab_key, chat_history, conversation_started):
    with st.expander("💾 Download conversazione", expanded=False):
        disabilita = not conversation_started
        
        # Aggiungi un prefisso alla chiave in base alla tab
        format_key = f"export_format_{tab_key}"
        download_key = f"download_button_{tab_key}"

        formati = {"📝 DOCX": "DOCX", "📄 TXT": "TXT", "📊 XLSX": "XLSX"}
        formato_label = st.selectbox(
            "📂 Seleziona formato di esportazione:",
            list(formati.keys()),
            key=format_key,
            disabled=disabilita
        )
        formato = formati[formato_label]
        
        export_result = export_chat(formato.lower(), chat_history) if not disabilita else None
        
        st.download_button(
            label=f"📥 Download conversazione [{formato}]",
            data=export_result[0] if export_result else b"",
            file_name=export_result[2] if export_result else "",
            mime=export_result[1] if export_result else "",
            disabled=disabilita,
            key=download_key
        )


def render_conversation_options(tab_key, conversation_started):
    """Renderizza le opzioni di conversazione nell'expander"""
    with st.expander("⚙️ Opzioni conversazione", expanded=False):
        disabilita = not conversation_started
        
        # Aggiungi un prefisso alla chiave in base alla tab
        reset_btn_key = f"reset_button_{tab_key}"
        model_key = f"model_selection_{tab_key}" 
        temp_key = f"temperature_slider_{tab_key}"
        top_p_key = f"top_p_slider_{tab_key}"
        st.button("🧹 Reset conversazione", on_click=reset_conversation, disabled=disabilita, key=reset_btn_key)
        
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
            disabled=False,
            help=(
        r"""
        **Modelli disponibili**
        
        - **GPT-4.1 Nano**: modello leggero ed economico (∼\$0.10/1M token in e \$0.40/1M token out), ideale per prompt non complessi e risposte veloci. E' il modello predefinito, generalmente consigliato per la maggior parte delle analisi.
        - **GPT-4.1 Mini**: compromesso tra costo e qualità (∼\$0.40/1M token in e \$1.60/1M token out)
        consigliato per analisi di media complessità
        - **GPT-4.1**: modello completo più “potente” e costoso (∼\$2.00/1M token in e \$8.00/1M token out)
        adatto per prompt lunghi o che richiedono ragionamenti più elaborati. Utilizzare solo in caso di reale necessità.
        """
    )
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
            key=temp_key,
            help=("""
                    **Temperature**: controlla la casualità delle risposte del modello.

                    - **Valori bassi** (es. 0.0–0.3) rendono il modello più deterministico e focalizzato.
                    - **Valori alti** (es. 1.0–2.0) ne aumentano la casualità e la varietà.
                    """
            )
        )
        
        st.session_state["top_p"] = st.slider(
            "🎯 Top-p (default: 1.0):",
            min_value=0.0,
            max_value=1.0,
            value=1.0,
            step=0.05,
            disabled=False,
            key=top_p_key,
            help=("""
                    **Top-p**: controlla la distribuzione delle risposte del modello (*nucleus sampling*), considerando *solo* le parole con probabilità cumulativa *≤ top-p*.

                    - **Valori bassi** (es. 0.0–0.3): il modello si concentra sulle parole più probabili, offrendo risultati più coerenti e sicuri
                    - **Valori alti** (es. 0.8–1.0): il modello include parole meno probabili, aumentando la varietà delle risposte e introducendo maggiore creatività.
                    """)
        )