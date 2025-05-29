import re
import os
import openai
import pandas as pd
from typing import List, Dict, Any, Optional
# from data_analyzer import DataAnalyzer, create_data_context
from data_analyzer import create_data_context
from utils import execute_code
import json

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
- Analisi di frequenza per variabili categoriche
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
        response = openai.ChatCompletion.create(
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
        if msg.get("function_call"):
            args = json.loads(msg["function_call"]["arguments"])
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
            return msg.get("content", "")
        
    except Exception as e:
        return f"Errore nella chiamata a OpenAI: {str(e)}"

def _contains_data_query(text: str) -> bool:
    """Verifica se il testo contiene richieste di analisi dati"""
    data_keywords = [
        'correlazione', 'media', 'mediana', 'deviazione', 'distribuzione',
        'frequenza', 'somma', 'massimo', 'minimo', 'raggruppa', 'filtra',
        'ordina', 'top', 'bottom', 'conta', 'percentuale', 'statistic', 'analisi', 'trend',
        'outlier', 'varianza', 'quantile', 'istogramma', 'calcola', 'aggiungi'
    ]
    
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in data_keywords)

def _execute_data_analysis(query: str, df: pd.DataFrame) -> Optional[str]:
    """Esegue analisi automatiche basate sulla query dell'utente"""
    try:
        analyzer = DataAnalyzer(df)
        query_lower = query.lower()
        results = []
        
        # Analisi di correlazione
        if 'correlazione' in query_lower or 'correlazioni' in query_lower:
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) >= 2:
                corr_matrix = df[numeric_cols].corr()
                # Trova le correlazioni più significative
                high_corr = []
                for i in range(len(numeric_cols)):
                    for j in range(i+1, len(numeric_cols)):
                        corr_val = corr_matrix.iloc[i, j]
                        if abs(corr_val) > 0.5:
                            high_corr.append(f"{numeric_cols[i]} ↔ {numeric_cols[j]}: {corr_val:.3f}")
                
                if high_corr:
                    results.append("CORRELAZIONI SIGNIFICATIVE:\n" + "\n".join(high_corr))
        
        # Statistiche descrittive per colonne menzionate
        mentioned_cols = [col for col in df.columns if col.lower() in query_lower]
        for col in mentioned_cols:
            if df[col].dtype in ['int64', 'float64']:
                stats = df[col].describe()
                results.append(f"STATISTICHE PER {col}:\n{stats.to_string()}")
            else:
                value_counts = df[col].value_counts().head(10)
                results.append(f"FREQUENZE PER {col}:\n{value_counts.to_string()}")
        
        # Analisi generale se non vengono trovate colonne specifiche
        if not mentioned_cols and not results:
            # Fornisci un summary generale
            summary = analyzer.get_comprehensive_summary()
            insights = summary.get('insights', [])
            if insights:
                results.append("INSIGHTS GENERALI:\n" + "\n".join(f"• {insight}" for insight in insights))
        
        return "\n\n".join(results) if results else None
        
    except Exception as e:
        return f"Errore nell'analisi automatica: {str(e)}"

# Manteniamo la funzione originale per backward compatibility
def ask_openai(messages_history, model, temperature=0.7, top_p=1.0):
    """Funzione originale mantenuta per compatibilità"""
    return ask_openai_with_data(messages_history, model, None, temperature, top_p)

# Nuove funzioni utility per query specifiche sui dati
def execute_specific_query(df: pd.DataFrame, query_type: str, **params) -> str:
    """Esegue query specifiche e restituisce risultati formattati"""
    try:
        analyzer = DataAnalyzer(df)
        result = analyzer.query_data(query_type, **params)
        
        if isinstance(result, pd.DataFrame):
            return f"RISULTATI QUERY ({query_type}):\n{result.to_string()}"
        elif isinstance(result, pd.Series):
            return f"RISULTATI QUERY ({query_type}):\n{result.to_string()}"
        else:
            return f"RISULTATO QUERY ({query_type}): {result}"
            
    except Exception as e:
        return f"Errore nell'esecuzione della query: {str(e)}"

def get_data_suggestions(df: pd.DataFrame) -> List[str]:
    """Genera suggerimenti per possibili analisi sui dati"""
    analyzer = DataAnalyzer(df)
    summary = analyzer.get_comprehensive_summary()
    
    suggestions = []
    
    # Suggerimenti basati sui tipi di colonne
    numeric_cols = [col for col, info in summary['column_analysis'].items() 
                   if 'statistics' in info]
    categorical_cols = [col for col, info in summary['column_analysis'].items() 
                       if 'top_values' in info]
    
    if len(numeric_cols) >= 2:
        suggestions.append("🔗 Analizza le correlazioni tra variabili numeriche")
        suggestions.append("📊 Confronta le distribuzioni delle variabili numeriche")
    
    if categorical_cols:
        suggestions.append("📈 Esamina la frequenza delle categorie principali")
        if numeric_cols:
            suggestions.append("🎯 Analizza le medie per categoria")
    
    # Suggerimenti basati sulla qualità dei dati
    if summary['data_quality']['missing_cells'] > 0:
        suggestions.append("🔍 Investiga i pattern dei valori mancanti")
    
    if summary['data_quality']['duplicate_rows'] > 0:
        suggestions.append("🔄 Esamina le righe duplicate")
    
    # Suggerimenti basati sulle relazioni
    if summary['relationships']['high_correlations']:
        suggestions.append("⚡ Approfondisci le correlazioni significative trovate")
    
    return suggestions[:5]  # Limitiamo a 5 suggerimenti