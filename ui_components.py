import streamlit as st
import re
import pandas as pd
from utils import reset_conversation, export_chat

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
    latex_blocks = re.findall(r"\\boxed\{.*?\}", content)

    if latex_blocks:
        parts = re.split(r"(\\boxed\{.*?\})", content)
        for part in parts:
            if part.startswith("\\boxed"):
                st.latex(part)
            else:
                # Usa unsafe_allow_html=True per permettere la formattazione markdown
                st.markdown(part, unsafe_allow_html=True)
    else:
        st.markdown(content, unsafe_allow_html=True)

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


def display_chat_history():
    """Visualizza la cronologia delle chat"""
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            render_user_message(msg["content"])
        else:
            with st.chat_message("assistant"):
                render_response(msg["content"])





def render_data_preview(df):
    #with st.expander("📈 Esplora i dati", expanded=True):
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
    # ——— FINE ANTEPRIMA E STATISTICHE ———

def render_download_conversation(tab_key):
    with st.expander("💾 Download conversazione", expanded=False):
        disabilita = not st.session_state.get("conversation_started", False)
        
        # Aggiungi un prefisso alla chiave in base alla tab
        #reset_btn_key = f"reset_button_{tab_key}"
        format_key = f"export_format_{tab_key}"
        download_key = f"download_button_{tab_key}"

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


def render_conversation_options(tab_key):
    """Renderizza le opzioni di conversazione nell'expander"""
    with st.expander("⚙️ Opzioni conversazione", expanded=False):
        disabilita = not st.session_state.get("conversation_started", False)
        
        # # Aggiungi un prefisso alla chiave in base alla tab
        reset_btn_key = f"reset_button_{tab_key}"
        # format_key = f"export_format_{tab_key}"
        # download_key = f"download_button_{tab_key}"
        model_key = f"model_selection_{tab_key}" 
        temp_key = f"temperature_slider_{tab_key}"
        top_p_key = f"top_p_slider_{tab_key}"
        
        st.button("🧹 Reset conversazione", on_click=reset_conversation, disabled=disabilita, key=reset_btn_key)
        
        # formati = {"📊 XLSX": "XLSX", "📝 DOCX": "DOCX", "📄 TXT": "TXT"}
        # formato_label = st.selectbox(
        #     "📂 Seleziona formato di esportazione:",
        #     list(formati.keys()),
        #     key=format_key,
        #     disabled=disabilita
        # )
        # formato = formati[formato_label]
        
        # export_result = export_chat(formato.lower()) if not disabilita else None
        
        # st.download_button(
        #     label=f"📥 Download conversazione [{formato}]",
        #     data=export_result[0] if export_result else b"",
        #     file_name=export_result[2] if export_result else "",
        #     mime=export_result[1] if export_result else "",
        #     disabled=disabilita,
        #     key=download_key
        # )
        
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