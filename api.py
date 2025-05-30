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

def build_system_prompt_code_executor():
    return (
      "Hai a disposizione df (pandas.DataFrame) e la funzione execute_code(code: str) -> any. "
      "Genera SOLO un blocco di codice Python che definisca `result` sulla base della query dell'utente."
    )

def ask_openai_with_data(messages_history: List[Dict], 
                        model: str, 
                        dataframe: Optional[pd.DataFrame] = None,
                        temperature: float = 0.7, 
                        top_p: float = 1.0) -> str:
    """
    Versione migliorata che include analisi automatica dei dati
    """
    
    # System prompt base
    system_prompt = ("""
Sei un esperto specializzato nell'analisi di dati, soprattutto dati statistici ufficiali, ti chiami Storylaizer.
Sei specializzato nell'interpretare dataset e fornire insights significativi.
Quando l'utente fa domande di elavoborazione dati, DEVI SEMPRE generare codice Python per fornire risposte precise basate sul dataset fornito.
L'utente può chiederti di eseguire analisi statistiche, calcoli, filtri e aggregazioni sui dati OPPURE di generare dei report o commenti basati su una tabella.

Regole generali:
1. Rispondi sempre in italiano, utilizzando un linguaggio chiaro, preciso
2. Non fornire opinioni personali, ma risposte basate sui dati
3. Non fornire risposte che non siano basate sui dati, fai attenzione a riportare sempre i valori corretti evitando allucinazioni.
4. Prima di iniziare l'analisi chiedi SEMPRE all'utente di fornire più dettagli sul contesto dei dati, significato delle colonne, periodo di riferimento, fonte, etc. (es. "Puoi spiegare meglio il contesto dei dati? A cosa fanno riferimento i dati?")
                     
Regole se l'utente ti chiede di eseguire analisi statistiche:
1. Per QUALSIASI domanda che presuppone un'elaborazione dati (es. calcoli, filtri, selezioni), genera sempre una function call con codice Python
2. Usa SOLO funzioni di pandas (pd) e numpy (np) per l'elaborazione dei dati, evitando librerie esterne
3. Se la domanda è vaga, interpreta nel contesto dei dati disponibili e nel flusso di conversazione
4. Usa sempre la variabile 'result' per il risultato finale
5. Se non puoi rispondere con i dati, chiedi all'utente di essere più specifico
6. Fornisci risposte concise e chiare, evitando tecnicismi inutili e giri di parole.
                     
Regole se l'utente ti chiede di generare report o commenti:
1. Fornisci un report dettagliato basato sui dati, includendo statistiche e insights
2. Non rispondere a domande che non riguardano i dati, come opinioni personali o argomenti generali
3. Se non hai informazioni a riguardo, chiedi all'utente la lunghezza del report desiderato (come numero di parole o caratteri)
4. Se l'utente non specifica, fornisci un report di 500 caratteri come default
5. Se l'utente chiede di generare un report per ciascuna riga del dataset (es. per ogni provincia/regione), formatta il report in modo che sia chiaro e leggibile, riportando sempre il riferimento alla riga specifica. L'ideale sarebbe generare una tabella con due colonne (colonna 1: nome della provincia/regione, colonna 2: report dettagliato).                     
    """
    )
    
    # Se abbiamo un dataframe, aggiungiamo il contesto
    if dataframe is not None and not dataframe.empty:
        data_context = create_data_context(dataframe)
        system_prompt += f"\n\nDATA CONTEXT:\n{data_context}"
        
        # Aggiungiamo anche le capacità di analisi
        system_prompt += """

CAPACITÀ DI ANALISI DISPONIBILI:
Puoi eseguire queste analisi sui dati:
- Statistiche descrittive per colonne numeriche
- Analisi di frequenza per handle_chat_input  categoriche
- Identificazione di valori mancanti e outlier
- Correlazioni tra variabili
- Raggruppamenti e aggregazioni
- Filtri e ordinamenti
- Analisi della distribuzione dei dati

IMPORTANTE: Quando l'utente chiede analisi specifiche, puoi fornire risultati precisi basati sui dati reali caricati.
"""
    
    # Costruiamo i messaggi per l'API
    api_messages = [{"role": "system", "content": system_prompt}]
    
    # Includiamo tutta la cronologia senza filtri:
    for msg in messages_history:
        api_messages.append({"role": msg["role"], "content": msg["content"]})
    
    try:
        client = OpenAI(api_key=get_api_key())
        response = client.chat.completions.create(
			model=model,
			messages=api_messages,
			functions=[{
				"name": "execute_code",
				"description": "Esegue un blocco di codice Python su df",
				"parameters": {
					"type": "object",
					"properties": {
						"code": {"type": "string"}
					},
					"required": ["code"]
				}
			}],
			function_call="auto",
			temperature=temperature,
			top_p=top_p
		)

        msg = response.choices[0].message
		# se l'LLM ha invocato la funzione:
        if msg.function_call:
            args = json.loads(msg.function_call.arguments)
            code = args.get("code", "")
            result = execute_code(code, dataframe)
			# poi formattiamo una seconda chiamata per la risposta umana
            followup = client.chat.completions.create(
				model=model,
				messages=api_messages + [
					{"role":"assistant","function_call":msg["function_call"]},
					{"role":"function","name":"execute_code","content":json.dumps(result)}
				]
			)
            return followup.choices[0].message.content
        else:
            return msg.content
        
    except Exception as e:
        return f"Errore nella chiamata a OpenAI: {str(e)}"
    



def ask_openai_analysis(history: List[Dict], model: str, df: pd.DataFrame, temperature: float, top_p: float) -> str:
    """
    Risponde alle domande sull’analisi dati usando function-calling Python
    solo se df è presente.
    """
    system = build_system_prompt_code_executor()
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model=model,
        messages=[{"role":"system","content":system}] + history,
        functions=[{
            "name":"execute_code",
            "description":"Esegue codice su df",
            "parameters":{"type":"object","properties":{"code":{"type":"string"}},"required":["code"]}
        }],
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

def ask_openai_report(history: List[Dict], model: str, df_report: pd.DataFrame, temperature: float, top_p: float) -> str:
    """
    Risponde alle domande di report includendo il contesto completo di df_report.
    """
    # Genero un prompt che include create_data_context(df_report)
    data_ctx = create_data_context(df_report)
    system = (
      "Sei Storylaizer, esperto nella generazione di report statistici dettagliati.\n"
      f"DATASET REPORT CONTEXT:\n{data_ctx}\n\n"
      "Ora l’utente può chiedere di creare report o commenti sul dataset intero."
    )
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model=model,
        messages=[{"role":"system","content":system}] + history,
        temperature=temperature,
        top_p=top_p
    )
    return response.choices[0].message.content