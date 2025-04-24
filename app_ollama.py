import streamlit as st
import requests
import json
import re
import time
import threading

def ask_ollama(message, model="deepseek-r1:7b"):
    system_prompt = (
        "Sei un assistente esperto in calcoli matematici. "
        "Rispondi in italiano in modo diretto e chiaro, e non includere riflessioni interne o testo tra <think>...</think>. "
        "Per espressioni matematiche, usa LaTeX ben formattato ed evita spiegazioni verbose. "
        "Mostra solo il calcolo e il risultato finale in modo ordinato."
    )

    response = requests.post(
        "http://localhost:11434/api/chat",
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            "stream": True
        },
        stream=True
    )

    full_response = ""
    for line in response.iter_lines():
        if line:
            part = line.decode("utf-8")
            try:
                data = json.loads(part)
                full_response += data.get("message", {}).get("content", "")
            except Exception as e:
                print(f"Errore nel parsing di una riga: {e}")
    cleaned_response = re.sub(r"<think>.*?</think>", "", full_response, flags=re.DOTALL).strip()
    return cleaned_response


def render_user_message(message):
    st.markdown(
        f"""
        <div style='display: flex; justify-content: flex-end; margin-top: 1rem;'>
            <div style='background-color: #e6f0fa; padding: 10px 15px; border-radius: 15px; max-width: 80%; text-align: right;'>
                <div style='color: #1f77b4; font-size: 1.2rem; margin-bottom: 5px;'>🙋‍♂️</div>
                <div style='color: #000;'>{message}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# Separa testo normale e LaTeX
def render_response(content):
    """
    Visualizza la risposta dell'LLM con supporto per:
    - Markdown (grassetto, corsivo, ecc.)
    - Blocchi LaTeX come \boxed{...}
    """
    # Trova blocchi \boxed{...} o altre espressioni LaTeX inline
    # Puoi aggiungere qui altri pattern se il modello usa \(...\) o $$...$$
    latex_blocks = re.findall(r"\\boxed\{.*?\}", content)

    if latex_blocks:
        # Spezza la risposta in parti miste: testo normale e blocchi LaTeX
        parts = re.split(r"(\\boxed\{.*?\})", content)
        for part in parts:
            if part.startswith("\\boxed"):
                st.latex(part)
            else:
                # Usa markdown per formattazione testuale (grassetto, corsivo, link)
                st.markdown(part, unsafe_allow_html=False)
    else:
        # Solo markdown
        st.markdown(content, unsafe_allow_html=False)


def typing_animation(placeholder, stop_event):
    """Anima i puntini fino a quando stop_event è attivo."""
    i = 0
    while not stop_event.is_set():
        placeholder.markdown(f"🧠 Storylaizer sta scrivendo{'.' * (i % 4)}")
        time.sleep(0.4)
        i += 1

def main():

    model_ollama = "deepseek-r1:7b"

    # Colonne per logo + titolo
    col1, col2 = st.columns([2, 6])
    with col1:
        st.image("./img/logo.png", width=200)
    with col2:
        st.markdown(
            """
            <h1 style="margin-bottom: 0;">
                <span style="color:#0F3D6E;">Storyl</span><span style="color:#26B6DA;">ai</span><span style="color:#0F3D6E;">zer</span>
            </h1>
            <h5 style="font-style: italic; margin-top: 0; color:#0F3D6E">Trasforma i tuoi dati in narrazioni AI-driven</h5>
            """,
            unsafe_allow_html=True
        )


    # Campo di upload file (per ora uno solo; se vuoi più file, usa accept_multiple_files=True)
    uploaded_file = st.file_uploader("Carica un file", type=["xlsx", "csv", "txt", "pdf", "jpg", "png"])

    # # Pulsante di submit
    # submitted = st.form_submit_button("Elabora")
    if uploaded_file:
        st.success(f"✅ Hai caricato: {uploaded_file.name}")
        st.session_state.file_loaded = True
    else:
        st.session_state.file_loaded = False

    # Chat dopo caricamento
    if st.session_state.get("file_loaded", False):
        st.markdown("---")
        st.markdown(f"##### 💬 Fornisci le istruzioni all'assistente AI")
        st.markdown(f"*{model_ollama}*")

        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        # Visualizza cronologia con render personalizzati
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                render_user_message(msg["content"])
            else:
                with st.chat_message("assistant"):
                    render_response(msg["content"])

        # Input utente
        user_input = st.chat_input("Scrivi qualcosa...")
        if user_input:
            render_user_message(user_input)
            st.session_state.chat_history.append({"role": "user", "content": user_input})

            # Placeholder per l'effetto "sta scrivendo..."
            with st.chat_message("assistant"):
                loading_placeholder = st.empty()
                dots = ""
                risposta = ""

                # Avvia la richiesta in un thread separato
                def get_response():
                    nonlocal risposta
                    risposta = ask_ollama(user_input, model=model_ollama)

                thread = threading.Thread(target=get_response)
                thread.start()

                # Mostra l'animazione fino a quando la risposta non arriva
                while thread.is_alive():
                    dots += "."
                    if len(dots) > 3:
                        dots = ""
                    loading_placeholder.markdown(f"🧠 *Storylaizer sta scrivendo*{dots}")
                    time.sleep(0.4)

                # Sostituisci animazione con risposta formattata
                loading_placeholder.empty()
                render_response(risposta)
                st.session_state.chat_history.append({"role": "assistant", "content": risposta})

if __name__ == "__main__":
    main()