import streamlit as st
import re

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