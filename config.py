import os
from dotenv import load_dotenv

# Carica le variabili dall'.env
load_dotenv()

# Prendi la chiave API in modo sicuro
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# (Facoltativo) Controllo se la chiave è caricata
if OPENAI_API_KEY is None:
    raise ValueError("API Key OpenAI mancante! Controlla il file .env")