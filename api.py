import re
import os
import streamlit as st
from openai import OpenAI
import pandas as pd
from typing import List, Dict, Any, Optional
# from data_analyzer import DataAnalyzer, create_data_context
from data_analyzer import create_data_context
from utils import execute_code
import json

def get_api_key():
    api_key = st.secrets.get("OPENAI_API_KEY", None) if hasattr(st, "secrets") else None
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY")
    return api_key

system_prompt_generale = """
Sei un esperto specializzato nell'analisi di dati, soprattutto dati statistici ufficiali, ti chiami Storylaizer.
Sei specializzato nell'interpretare dataset e fornire insights significativi.
Quando l'utente fa domande di elaborazione dati, DEVI SEMPRE generare codice Python per fornire risposte precise basate sul dataset fornito.
L'utente può chiederti di eseguire analisi statistiche, calcoli, filtri e aggregazioni sui dati OPPURE di generare dei report o commenti basati su una tabella.

Regole generali:
1. Rispondi sempre in italiano, utilizzando un linguaggio chiaro, preciso
2. Non fornire opinioni personali, ma risposte basate sui dati
3. Fornire risposte SOLO basate sui dati, fai attenzione a riportare SEMPRE i valori corretti evitando allucinazioni.
4. Prima di iniziare l'analisi, se l'utente non l'ha già fornito, chiedi SEMPRE di fornirti un dataset da analizzare e dettagli sul contesto dei dati, significato delle colonne, periodo di riferimento, fonte, etc.

"""


system_prompt_analisi_df = """
Quando l'utente fa domande di elaborazione dati, DEVI SEMPRE generare codice Python per fornire risposte precise basate sul dataset fornito.
L'utente può chiederti di eseguire analisi dati, calcolo di statistiche, filtri e aggregazioni sui dati.

Regole se l'utente ti chiede di eseguire analisi statistiche:
1. Hai a disposizione df (pandas.DataFrame) e la funzione execute_code(code: str) -> any.
2. Genera SOLO un blocco di codice Python che definisca `result` sulla base della query dell'utente.
3. Usa sempre la variabile 'result' per il risultato finale
4. Usa SOLO funzioni di pandas (pd) e numpy (np) per l'elaborazione dei dati, evitando librerie esterne
5. Se la domanda è vaga, interpreta nel contesto dei dati disponibili e nel flusso di conversazione
6. Se non puoi rispondere con i dati, chiedi all'utente di essere più specifico
7. Fornisci risposte concise e chiare, evitando tecnicismi inutili e giri di parole.

"""

system_prompt_report = """
L'utente può chiederti di generare dei report o commenti basati su una tabella

Regole se l'utente ti chiede di generare report o commenti:
1. Fornisci un report dettagliato basato sui dati, includendo statistiche e insights
2. Non rispondere a domande che non riguardano i dati, come opinioni personali o argomenti generali
3. Se non hai informazioni a riguardo, chiedi all'utente la lunghezza del report desiderato (come numero di parole o caratteri)
4. Se l'utente non specifica, fornisci un report di 500 caratteri come default
5. Se l'utente chiede di generare un report per ciascuna riga del dataset (es. per ogni provincia/regione), formatta il report in modo che sia chiaro e leggibile, riportando sempre il riferimento alla riga specifica. L'ideale sarebbe generare una tabella con due colonne (colonna 1: nome della provincia/regione, colonna 2: report dettagliato).

"""

def ask_openai_analysis(history: List[Dict]
                        , model: str
                        , df: pd.DataFrame
                        , temperature: float
                        , top_p: float) -> str:
    """
    Risponde alle domande sull'analisi dati usando function-calling Python solo se df è presente.
    """
    # Contesto dati
    data_ctx = create_data_context(df)
    data_context = f"\n\n DATASET REPORT CONTEXT:\n{create_data_context(df)}"

    # Chiediamo al modello di produrre Python
    client = OpenAI(api_key=get_api_key())
    response = client.chat.completions.create(
        model=st.session_state.selected_model,
        messages=[{"role":"system"
                   ,"content":system_prompt_generale + system_prompt_analisi_df + data_context}]
                + st.session_state.chat_history,
        functions=[{"name":"execute_code", "description":"Esegue codice su df",
                    "parameters":{"type":"object","properties":{"code":{"type":"string"}},"required":["code"]}}],
        function_call="auto",
        temperature=temperature,
        top_p=top_p
    )
    msg = response.choices[0].message
    if msg.function_call:
        args = json.loads(msg.function_call.arguments)
        result = execute_code(args["code"], df)
        followup = client.chat.completions.create(
            model=model,
            messages=[
                *response.usage,  # oppure ricomporre i messaggi
                {"role":"assistant","function_call":msg.function_call},
                {"role":"function","name":"execute_code","content":json.dumps(result)}
            ]
        )
        return followup.choices[0].message.content
    else:
        return msg.content


def ask_openai_report(history: List[Dict]
                      , model: str
                      , df: pd.DataFrame
                      , temperature: float
                      , top_p: float) -> str:
    """
    Risponde alle domande di report includendo il contesto completo di df.
    """
    # Genero un prompt che include create_data_context(df_report)
    if df.empty or df is None:
        system_prompt_dati = f"""Chiedi all'utente di fornire un dataset da analizzare."""
    else:
        system_prompt_dati = f"""

Ecco i dati che hai a disposizione per generare il report:
<TABELLA>{df.to_markdown(index=False)}</TABELLA>
"""
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model=model,
        messages=[{"role":"system","content":system_prompt_generale + system_prompt_report + system_prompt_dati}] + history,
        temperature=temperature,
        top_p=top_p
    )
    return response.choices[0].message.content