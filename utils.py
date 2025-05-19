import streamlit as st
import time
import pandas as pd
import io
from docx import Document
import markdown2
from html2docx import html2docx
import re


def reset_conversation():
    # Nuovo ID sessione per forzare ricaricamento
    st.session_state.session_id = str(time.time())
    
    # Salva la tab corrente prima del reset
    current_tab = st.session_state.get("active_tab", "file")
    
    # Reset variabili principali
    keys_to_reset = ["chat_history", "file_loaded", "uploaded_file", "dataframe", "data_metadata", "data_errors"]
    for key in keys_to_reset:
        if key in st.session_state:
            del st.session_state[key]
    
    # Ripristina la tab corrente
    st.session_state.active_tab = current_tab
    st.session_state.default_tab = current_tab
            
def init_session_state():
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "selected_mode" not in st.session_state:
        st.session_state.selected_mode = None
    if "file_loaded" not in st.session_state:
        st.session_state.file_loaded = False
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "file"  # Default alla tab dei file
    if "uploaded_file" not in st.session_state:
        st.session_state.uploaded_file = None
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(time.time())

# Esportazione chat in vari formati
def export_chat(format_type):
    if not st.session_state.chat_history:
        st.warning("Non ci sono messaggi da esportare.")
        return None

    if format_type == "xlsx":
        conv_rows = []
        tables = []
        tbl_idx = 0

        for msg in st.session_state.chat_history:
            role = "Utente" if msg["role"] == "user" else "Assistente"
            content = msg["content"] or ""
            lines = content.splitlines()

            # Riconoscimento di blocco tabella Markdown (header + separator)
            if (
                len(lines) >= 2
                and re.match(r"^\|(.+\|)+\s*$", lines[0])
                and re.match(r"^\|\s*[-:]+\s*(\|\s*[-:]+\s*)+\|\s*$", lines[1])
            ):
                # Parsiamo header e righe
                headers = [h.strip() for h in lines[0].strip("|").split("|")]
                data_rows = []
                for row in lines[2:]:
                    if not row.strip().startswith("|"):
                        break
                    data_rows.append([c.strip() for c in row.strip("|").split("|")])

                # Crea DataFrame della tabella
                df_tbl = pd.DataFrame(data_rows, columns=headers)
                tbl_idx += 1
                tables.append((f"Tabella {tbl_idx}", df_tbl))

                # Nella conversazione inseriamo un placeholder
                conv_rows.append({
                    "Ruolo": role,
                    "Messaggio": f"[Tabella {tbl_idx}]"
                })
            else:
                # Messaggio normale
                conv_rows.append({
                    "Ruolo": role,
                    "Messaggio": content
                })

        # Costruiamo DataFrame conversazione
        df_conv = pd.DataFrame(conv_rows)

        # Scriviamo su Excel con più sheet
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            # Foglio principale
            df_conv.to_excel(
                writer,
                index=False,
                sheet_name="Conversazione"
            )
            # Fogli delle tabelle
            for sheet_name, df_tbl in tables:
                df_tbl.to_excel(
                    writer,
                    index=False,
                    sheet_name=sheet_name
                )

        return (
            output.getvalue(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "conversazione.xlsx"
        )

    elif format_type == "txt":
        content = ""
        for msg in st.session_state.chat_history:
            prefix = "Utente: " if msg["role"] == "user" else "Assistente: "
            content += f"{prefix}{msg['content']}\n\n"
        return content.encode(), "text/plain", "conversazione.txt"

    elif format_type == "docx":
        try:
            final_doc = Document()

            for idx, msg in enumerate(st.session_state.chat_history, start=1):
                text = msg.get("content", "").strip()
                if not text:
                    continue

                role = "Utente" if msg["role"] == "user" else "Assistente"
                markdown_text = f"**{role}:**\n\n{text}"

                # 1) Prova a convertire TUTTO in HTML (inclusi i blocchi tabella)
                html = markdown2.markdown(
                    markdown_text,
                    extras=["tables", "fenced-code-blocks"]
                )

                try:
                    # 2) html2docx con parametro title
                    temp_stream = html2docx(html, title=f"msg_{idx}")
                    from docx import Document as _Doc
                    temp_doc = _Doc(io.BytesIO(temp_stream.getvalue()))

                    # 3) Unisci i nodi XML
                    for element in temp_doc.element.body:
                        final_doc.element.body.append(element)

                except Exception:
                    # --- Fallback manual per tabelle Markdown ---
                    lines = markdown_text.splitlines()
                    # riconosco un blocco tabella in stile Markdown
                    if (len(lines) >= 3
                        and re.match(r"^\|.+\|$", lines[0])
                        and re.match(r"^\|\s*[-:]+\s*(\|\s*[-:]+\s*)+\|$", lines[1])):
                        # intestazioni
                        headers = [h.strip() for h in lines[0].strip("|").split("|")]
                        # righe
                        data_rows = []
                        for row in lines[2:]:
                            if not row.strip().startswith("|"):
                                break
                            data_rows.append([c.strip() for c in row.strip("|").split("|")])

                        table = final_doc.add_table(rows=1+len(data_rows), cols=len(headers))
                        # header row
                        for i, hdr in enumerate(headers):
                            table.rows[0].cells[i].text = hdr
                        # body
                        for r, row in enumerate(data_rows, start=1):
                            for c, val in enumerate(row):
                                table.rows[r].cells[c].text = val

                        final_doc.add_paragraph("")  # spazio dopo la tabella
                    else:
                        # se non è tabella, aggiungo il blocco come paragrafo semplice
                        p = final_doc.add_paragraph()
                        p.add_run(markdown_text)

                # spazio tra i messaggi
                final_doc.add_paragraph("")

            output = io.BytesIO()
            final_doc.save(output)
            return (
                output.getvalue(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "conversazione.docx"
            )

        except ImportError:
            st.error(
                "Per esportare in DOCX con Markdown servono: "
                "python-docx, markdown2, html2docx"
            )
            return None