# 📊 Storylaizer

**Storylaizer** è un'applicazione Streamlit progettata per trasformare generare analisi AI-driven, report dettagliati e risposte intelligenti su argomenti di statistica e data analysis.

## 🚀 Funzionalità principali

L'applicazione si articola in **tre tab** principali, ciascuna dedicata a un tipo diverso di interazione con l’assistente AI:

---

### 🔍 Data Analyzer

Questa sezione consente di **caricare un file Excel** e interrogare l’assistente in linguaggio naturale per ottenere:

- Analisi statistiche descrittive
- Calcoli su colonne numeriche (media, deviazione standard, CV, ecc.)
- Filtri condizionali su righe (es. “valori maggiori di 1000”)
- Aggregazioni e raggruppamenti (es. “somma per regione”)
- Individuazione automatica di correlazioni e outlier

⚙️ L’assistente utilizza un modello OpenAI con function-calling per convertire le richieste in codice Python (sfruttando le librerie Pandas e Numpy) eseguibile sul dataframe caricato.

---

### 📝 Report Builder

Questa sezione è pensata per la **generazione automatica di report testuali** a partire da un file Excel.

- Supporta dataset fino a **250 righe**
- Richiede una **descrizione del contesto** e delle colonne nel prompt
- Consente di specificare la **lunghezza**, il **tono** e il **formato** del report desiderato
- È possibile fornire un esempio di report come modello da replicare

Il sistema genera testi coerenti e formattati, ideali per la pubblicazione o la documentazione statistica.

---

### 🤖 AI Chat

Uno spazio di **chat libera con l’assistente AI**:

- Risponde a domande di **statistica**, **analisi dati**, **formule matematiche**, ecc.
- Può generare report anche senza file Excel, partendo da **tabelle incollate nel prompt**
- Supporta input in linguaggio naturale e domande esplorative

💡 È la soluzione ideale quando si desidera interagire con l’AI senza caricare file, oppure per generare commenti e insight partendo da una tabella testuale.

---

## 💾 Esportazione

Ogni conversazione può essere esportata in tre formati:

- **.TXT** (testo semplice in cui possono essere presenti formattazioni markdown)
- **.DOCX** (Word)
- **.XLSX** (tabella Excel con messaggi e tabelle estratte)

---

## ⚙️ Tecnologie utilizzate

- **Python 3**, **Streamlit**
- **OpenAI API** con function calling
- **Pandas / NumPy** per l’analisi dati
- **Markdown2 / html2docx / OpenPyXL** per la generazione dei file esportabili

---

## 🧠 Modelli AI disponibili

È possibile scegliere tra tre modelli GPT-4.1:

- 🪶 **Nano**: economico, veloce, adatto a prompt semplici
- ⚡ **Mini**: buon bilanciamento tra costo e qualità
- 🧠 **Full GPT-4.1**: più potente e preciso, ma costoso

---

## 📎 Requisiti

- Python 3.10+
- OpenAI API Key
- File `.env` con variabili d'ambiente configurate (se locale)

---

## 📁 Avvio

Per eseguire l'app:

```bash
streamlit run app.py
