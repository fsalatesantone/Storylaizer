import re
import os
import openai

def ask_openai(messages_history, model, temperature=0.7, top_p=1.0):
    system_prompt = (
        "Sei un esperto di analisi di dati statistici ufficiali, ti chiami Storylaizer. "
        "Rispondi sempre in italiano. "
        "Quando analizzi i dati di una tabella, fai attenzione a riportare sempre i valori corretti evitando allucinazioni."
    )
    
    api_messages = [{"role": "system", "content": system_prompt}]
    for msg in messages_history:
        api_messages.append({"role": msg["role"], "content": msg["content"]})
    
    try:
        # Inizializza il client OpenAI - non è più necessario definire la chiave 
        # direttamente qui poiché ora viene impostata nelle variabili d'ambiente
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