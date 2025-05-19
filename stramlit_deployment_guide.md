# Guida al Deployment su Streamlit Cloud

## Preparazione dell'app

1. Assicurati che il file `requirements.txt` contenga tutte le dipendenze necessarie:

```
streamlit
openai
python-dotenv
pandas
```

2. Assicurati che il tuo repository Github contenga tutti i file necessari:
   - app.py
   - api.py
   - ui_components.py
   - utils.py
   - /img/logo.png

3. Aggiungi al `.gitignore`:
   - .env
   - .streamlit/secrets.toml

## Deployment su Streamlit Cloud

1. Accedi a [Streamlit Cloud](https://streamlit.io/cloud)

2. Collega il tuo repository GitHub

3. Configura l'app:
   - Seleziona il repository
   - Specifica il file principale: `app.py`
   - Imposta la versione di Python (3.9+ raccomandata)

4. Configura le variabili segrete:
   - Vai in "Advanced settings" > "Secrets"
   - Aggiungi la tua chiave API in formato TOML:
   ```toml
   OPENAI_API_KEY = "sk-your-api-key-here"
   ```

5. Clicca su "Deploy" e attendi il completamento del processo

## Test dopo il deployment

1. Verifica che l'app si carichi correttamente
2. Controlla che l'autenticazione con l'API OpenAI funzioni
3. Testa tutte le funzionalità principali

## Risoluzione problemi comuni

- **Errore API OpenAI**: Verifica che la chiave segreta sia impostata correttamente
- **Errori di importazione**: Assicurati che tutte le dipendenze siano nel requirements.txt
- **Errori relativi ai file**: Controlla che tutti i percorsi file siano relativi e corretti