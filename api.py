import re
import os
import openai

def ask_openai(messages_history):

    system_prompt = (
        "Sei un esperto di analisi di dati statistici ufficiali. "
        "Rispondi sempre in italiano. "
        "Quando analizzi i dati di una tabella, fai attenzione a riportare sempre i valori corretti evitando allucinazioni."
    )

    api_messages = [{"role": "system", "content": system_prompt}]
    for msg in messages_history:
        api_messages.append({"role": msg["role"], "content": msg["content"]})

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4.1-nano",
            messages=api_messages,
            stream=False
        )

        full_response = response.choices[0].message.content
        cleaned_response = re.sub(r"<think>.*?</think>", "", full_response, flags=re.DOTALL).strip()
        return cleaned_response

    except openai.error.OpenAIError as e:
        return f"Errore nella chiamata a OpenAI: {str(e)}"