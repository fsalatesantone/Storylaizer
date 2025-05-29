import re
import os
import openai
import pandas as pd
from typing import List, Dict, Any, Optional
from data_analyzer import DataAnalyzer, create_data_context
import json

def ask_openai_with_data(messages_history: List[Dict], 
                        model: str, 
                        dataframe: Optional[pd.DataFrame] = None,
                        temperature: float = 0.7, 
                        top_p: float = 1.0) -> str:
    """
    Versione migliorata che include analisi automatica dei dati
    """
    
    # System prompt base
    system_prompt = (
        "Sei un esperto di analisi di dati statistici ufficiali, ti chiami Storylaizer. "
        "Rispondi sempre in italiano. "
        "Quando analizzi i dati di una tabella, fai attenzione a riportare sempre i valori corretti evitando allucinazioni. "
        "Sei specializzato nell'interpretare dataset e fornire insights significativi. "
        "Quando l'utente fa domande sui dati, puoi eseguire analisi specifiche e fornire risposte precise basate sui dati reali. "
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
    
    # Aggiungiamo la cronologia
    for msg in messages_history:
        content = msg["content"]
        
        # Se il messaggio contiene richieste di analisi specifiche e abbiamo i dati
        if dataframe is not None and _contains_data_query(content):
            # Proviamo a interpretare ed eseguire l'analisi
            analysis_result = _execute_data_analysis(content, dataframe)
            if analysis_result:
                content += f"\n\n[RISULTATI ANALISI AUTOMATICA]:\n{analysis_result}"
        
        api_messages.append({"role": msg["role"], "content": content})
    
    try:
        response = openai.chat.completions.create(
            model=model,
            messages=api_messages,
            stream=False,
            temperature=temperature,
            top_p=top_p
        )
        
        full_response = response.choices[0].message.content
        cleaned_response = re.sub(r"<think>.*?</think>", "", full_response, flags=re.DOTALL).strip()
        return cleaned_response
    
    except Exception as e:
        return f"Errore nella chiamata a OpenAI: {str(e)}"

def _contains_data_query(text: str) -> bool:
    """Verifica se il testo contiene richieste di analisi dati"""
    data_keywords = [
        'correlazione', 'media', 'mediana', 'deviazione', 'distribuzione',
        'frequenza', 'somma', 'massimo', 'minimo', 'raggruppa', 'filtra',
        'ordina', 'conta', 'percentuale', 'statistic', 'analisi', 'trend',
        'outlier', 'varianza', 'quantile', 'istogramma'
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