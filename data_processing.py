import pandas as pd
import numpy as np
import streamlit as st
from typing import Dict, List, Tuple, Optional, Any

def get_excel_sheets(file) -> List[str]:
    """Restituisce la lista di sheet presenti nel file Excel."""
    try:
        excel_file = pd.ExcelFile(file)
        return excel_file.sheet_names
    except Exception as e:
        st.error(f"Errore nella lettura del file Excel: {str(e)}")
        return []

def detect_header_row(df: pd.DataFrame) -> Tuple[int, bool]:
    """
    Individua la riga che contiene probabilmente le intestazioni.
    
    Returns:
        Tuple[int, bool]: (indice riga intestazione, flag di presenza problemi)
    """
    # Se tutti i valori della prima riga sono stringhe o hanno valori unici, 
    # probabilmente è un'intestazione valida
    if df.shape[0] == 0:
        return 0, True
        
    first_row = df.iloc[0]
    non_null_values = first_row.dropna()
    if len(non_null_values) == 0:
        return 1, True  # La prima riga è vuota
        
    str_count = sum(isinstance(val, str) for val in first_row)
    unique_ratio = len(first_row.unique()) / len(first_row)
    
    if str_count >= len(first_row) * 0.7 or unique_ratio > 0.9:
        return 0, False  # Prima riga sembra essere un'intestazione valida
    else:
        # Controlla se ci sono pattern tipici di intestazioni nelle righe successive
        for i in range(1, min(5, df.shape[0])):
            row = df.iloc[i]
            str_count = sum(isinstance(val, str) for val in row)
            unique_ratio = len(row.unique()) / len(row)
            
            if str_count >= len(row) * 0.7 or unique_ratio > 0.9:
                return i, True  # Possibile intestazione trovata in questa riga
                
    return 0, True  # Non trovata una riga specifica, usiamo la prima come default

def validate_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Controlla se il DataFrame ha problemi strutturali.
    
    Returns:
        Dict con informazioni sugli errori trovati.
    """
    errors = {
        "has_errors": False,
        "messages": [],
        "suggestions": []
    }
    
    # Controllo dimensioni
    if df.shape[0] == 0:
        errors["has_errors"] = True
        errors["messages"].append("Il file non contiene dati.")
        errors["suggestions"].append("Carica un file con almeno una riga di dati.")
        return errors
        
    if df.shape[1] == 0:
        errors["has_errors"] = True
        errors["messages"].append("Il file non contiene colonne.")
        errors["suggestions"].append("Carica un file con almeno una colonna di dati.")
        return errors
    
    # Controllo intestazioni colonne
    if df.columns.str.contains("Unnamed").any():
        unnamed_cols = df.columns[df.columns.str.contains("Unnamed")].tolist()
        errors["has_errors"] = True
        errors["messages"].append(f"Trovate {len(unnamed_cols)} colonne senza intestazione.")
        errors["suggestions"].append("Assicurati che tutte le colonne abbiano un'intestazione nella riga corretta.")
    
    # Controllo duplicati nelle intestazioni
    if len(df.columns) != len(df.columns.unique()):
        duplicates = df.columns[df.columns.duplicated()].unique().tolist()
        errors["has_errors"] = True
        errors["messages"].append(f"Trovate intestazioni duplicate: {', '.join(map(str, duplicates))}")
        errors["suggestions"].append("Le intestazioni delle colonne devono essere univoche.")
    
    # Controllo formati incoerenti nelle colonne
    for col in df.columns:
        if df[col].notna().sum() == 0:
            continue  # Salta colonne completamente vuote
            
        inferred_type = None
        mixed_types = False
        
        for val in df[col].dropna():
            current_type = type(val)
            if inferred_type is None:
                inferred_type = current_type
            elif inferred_type != current_type:
                if (inferred_type in [int, float] and current_type in [int, float]) or \
                   (str(inferred_type) == "<class 'pandas._libs.tslibs.timestamps.Timestamp'>" and current_type == str) or \
                   (inferred_type == str and str(current_type) == "<class 'pandas._libs.tslibs.timestamps.Timestamp'>"):
                    # Tipi compatibili (numeri o date/stringhe)
                    continue
                else:
                    mixed_types = True
                    break
                
        if mixed_types:
            errors["has_errors"] = True
            errors["messages"].append(f"La colonna '{col}' contiene tipi di dati misti.")
            errors["suggestions"].append(f"Verifica i formati nella colonna '{col}' e assicurati che siano coerenti.")
    
    return errors

def get_column_info(df: pd.DataFrame) -> List[Dict[str, str]]:
    """
    Restituisce informazioni sui tipi di dati delle colonne.
    
    Returns:
        List di Dict con nome colonna e tipo di dato in formato leggibile.
    """
    column_info = []
    
    for col in df.columns:
        # Ottieni i valori non nulli
        values = df[col].dropna()
        
        if len(values) == 0:
            data_type = "Vuoto"
        else:
            # Rileva il tipo di dato
            dtype = df[col].dtype
            
            if pd.api.types.is_integer_dtype(dtype):
                data_type = "Numero intero"
            elif pd.api.types.is_float_dtype(dtype):
                # Verifica se sono in realtà interi memorizzati come float
                if all(pd.notna(val) and val.is_integer() for val in values):
                    data_type = "Numero intero"
                else:
                    data_type = "Numero decimale"
            elif pd.api.types.is_datetime64_dtype(dtype):
                data_type = "Data/Ora"
            elif pd.api.types.is_bool_dtype(dtype):
                data_type = "Booleano (Vero/Falso)"
            elif pd.api.types.is_categorical_dtype(dtype):
                data_type = f"Categorico ({len(values.unique())} categorie)"
            elif pd.api.types.is_string_dtype(dtype) or pd.api.types.is_object_dtype(dtype):
                # Controlla se potrebbe essere una data
                try:
                    if all(pd.to_datetime(val, errors='raise') for val in values.iloc[:min(10, len(values))]):
                        data_type = "Data/Ora (come testo)"
                    else:
                        # Se è testo, controlla se è categorico o testo libero
                        unique_ratio = len(values.unique()) / len(values)
                        if unique_ratio < 0.2 and len(values) > 10:
                            data_type = f"Categorico ({len(values.unique())} categorie)"
                        else:
                            data_type = "Testo"
                except:
                    # Se ci sono errori nella conversione a data, è testo
                    unique_ratio = len(values.unique()) / len(values)
                    if unique_ratio < 0.2 and len(values) > 10:
                        data_type = f"Categorico ({len(values.unique())} categorie)"
                    else:
                        data_type = "Testo"
            else:
                data_type = str(dtype)
                
        column_info.append({
            "nome": col,
            "tipo": data_type
        })
    
    return column_info

def get_dataframe_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcola le statistiche principali per ciascuna colonna del DataFrame.
    
    Returns:
        DataFrame con statistiche per colonna.
    """
    stats = []
    
    for col in df.columns:
        col_stats = {"Variabile": col}
        
        # Calcola valori mancanti
        missing = df[col].isna().sum()
        col_stats["Valori mancanti"] = missing
        col_stats["% mancanti"] = f"{(missing / len(df) * 100):.1f}%"
        
        # Statistiche diverse per tipi diversi
        if pd.api.types.is_numeric_dtype(df[col].dtype):
            # Statistiche numeriche
            col_stats["Media"] = f"{df[col].mean():.2f}" if not pd.isna(df[col].mean()) else "N/A"
            col_stats["Mediana"] = f"{df[col].median():.2f}" if not pd.isna(df[col].median()) else "N/A"
            col_stats["Deviazione std"] = f"{df[col].std():.2f}" if not pd.isna(df[col].std()) else "N/A"
            col_stats["Min"] = f"{df[col].min():.2f}" if not pd.isna(df[col].min()) else "N/A"
            col_stats["Max"] = f"{df[col].max():.2f}" if not pd.isna(df[col].max()) else "N/A"
            col_stats["25%"] = f"{df[col].quantile(0.25):.2f}" if not pd.isna(df[col].quantile(0.25)) else "N/A"
            col_stats["75%"] = f"{df[col].quantile(0.75):.2f}" if not pd.isna(df[col].quantile(0.75)) else "N/A"
            
        elif pd.api.types.is_datetime64_dtype(df[col].dtype):
            # Statistiche temporali
            col_stats["Min"] = str(df[col].min()) if not pd.isna(df[col].min()) else "N/A"
            col_stats["Max"] = str(df[col].max()) if not pd.isna(df[col].max()) else "N/A"
            col_stats["Range"] = f"{(df[col].max() - df[col].min()).days} giorni" if not pd.isna(df[col].min()) and not pd.isna(df[col].max()) else "N/A"
            
        else:
            # Statistiche per testo/categorie
            unique_values = df[col].nunique()
            col_stats["Valori unici"] = unique_values
            col_stats["% unicità"] = f"{(unique_values / len(df) * 100):.1f}%"
            
            if unique_values <= 10:
                # Se pochi valori, mostra le frequenze principali
                value_counts = df[col].value_counts().head(5)
                for i, (val, count) in enumerate(value_counts.items(), 1):
                    val_str = str(val)
                    if len(val_str) > 20:
                        val_str = val_str[:17] + "..."
                    col_stats[f"Top {i}"] = f"{val_str} ({count})"
            else:
                # Altrimenti mostra solo il valore più comune
                most_common = df[col].value_counts().head(1)
                if not most_common.empty:
                    val = most_common.index[0]
                    val_str = str(val)
                    if len(val_str) > 20:
                        val_str = val_str[:17] + "..."
                    col_stats["Più frequente"] = f"{val_str} ({most_common.values[0]})"
        
        stats.append(col_stats)
    
    # Crea un DataFrame dalle statistiche
    stats_df = pd.DataFrame(stats)
    return stats_df

def safe_import_excel(file, sheet_name=0, header_row=0) -> Tuple[Optional[pd.DataFrame], Dict]:
    """
    Importa un file Excel in modo sicuro con gestione degli errori.
    
    Args:
        file: File Excel caricato
        sheet_name: Nome o indice dello sheet da importare
        header_row: Riga da usare come intestazione
    
    Returns:
        Tuple[DataFrame, Dict]: (DataFrame importato o None se ci sono errori, dizionario con info/errori)
    """
    result = {
        "success": False,
        "errors": [],
        "warnings": []
    }
    
    try:
        # Prova a leggere con pandas
        df = pd.read_excel(file, sheet_name=sheet_name, header=header_row)
        
        # Controlla se il DataFrame è vuoto
        if df.empty:
            result["errors"].append("Il file Excel non contiene dati.")
            return None, result
            
        # Verifica se ci sono problemi di formattazione
        header_row_detected, has_header_issues = detect_header_row(df)
        
        if has_header_issues and header_row == 0:
            result["warnings"].append(f"Le intestazioni potrebbero non essere nella prima riga. " 
                                     f"Trovate possibili intestazioni nella riga {header_row_detected + 1}.")
        
        # Valida il dataframe
        validation = validate_dataframe(df)
        if validation["has_errors"]:
            result["errors"].extend(validation["messages"])
            result["warnings"].extend(validation["suggestions"])
        
        # Se ci sono errori gravi, restituisce None
        if result["errors"]:
            return None, result
            
        # Normalizza i nomi delle colonne
        df.columns = [str(col).strip() for col in df.columns]
        
        result["success"] = True
        return df, result
        
    except Exception as e:
        result["errors"].append(f"Errore durante l'importazione del file: {str(e)}")
        return None, result