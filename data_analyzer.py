import pandas as pd
import numpy as np
import json
from typing import Dict, Any, List, Tuple
import re

class DataAnalyzer:
    """Classe per analizzare DataFrame e fornire informazioni strutturate all'AI"""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.analysis_cache = {}
    
    def get_comprehensive_summary(self) -> Dict[str, Any]:
        """Genera un summary completo del dataset per l'AI"""
        if 'comprehensive_summary' in self.analysis_cache:
            return self.analysis_cache['comprehensive_summary']
            
        summary = {
            'basic_info': self._get_basic_info(),
            'column_analysis': self._analyze_columns(),
            'data_quality': self._assess_data_quality(),
            'relationships': self._find_relationships(),
            'insights': self._generate_insights()
        }
        
        self.analysis_cache['comprehensive_summary'] = summary
        return summary
    
    def _get_basic_info(self) -> Dict[str, Any]:
        """Informazioni base del dataset"""
        return {
            'shape': self.df.shape,
            'memory_usage': f"{self.df.memory_usage(deep=True).sum() / 1024**2:.2f} MB",
            'columns': list(self.df.columns),
            'dtypes': {col: str(dtype) for col, dtype in self.df.dtypes.items()}
        }
    
    def _analyze_columns(self) -> Dict[str, Dict[str, Any]]:
        """Analisi dettagliata per ogni colonna"""
        analysis = {}
        
        for col in self.df.columns:
            col_analysis = {
                'dtype': str(self.df[col].dtype),
                'missing_count': int(self.df[col].isna().sum()),
                'missing_percentage': round(self.df[col].isna().sum() / len(self.df) * 100, 2),
                'unique_count': int(self.df[col].nunique()),
                'unique_percentage': round(self.df[col].nunique() / len(self.df) * 100, 2)
            }
            
            # Analisi specifica per tipo di dato
            if pd.api.types.is_numeric_dtype(self.df[col]):
                col_analysis.update(self._analyze_numeric_column(col))
            elif pd.api.types.is_datetime64_any_dtype(self.df[col]):
                col_analysis.update(self._analyze_datetime_column(col))
            else:
                col_analysis.update(self._analyze_categorical_column(col))
            
            analysis[col] = col_analysis
        
        return analysis
    
    def _analyze_numeric_column(self, col: str) -> Dict[str, Any]:
        """Analisi specifica per colonne numeriche"""
        series = self.df[col].dropna()
        
        return {
            'statistics': {
                'mean': round(series.mean(), 4),
                'median': round(series.median(), 4),
                'std': round(series.std(), 4),
                'min': series.min(),
                'max': series.max(),
                'q25': round(series.quantile(0.25), 4),
                'q75': round(series.quantile(0.75), 4),
                'skewness': round(series.skew(), 4),
                'kurtosis': round(series.kurtosis(), 4)
            },
            'outliers_count': self._count_outliers(series),
            'distribution_type': self._identify_distribution(series)
        }
    
    def _analyze_datetime_column(self, col: str) -> Dict[str, Any]:
        """Analisi specifica per colonne datetime"""
        series = pd.to_datetime(self.df[col], errors='coerce').dropna()
        
        return {
            'date_range': {
                'min': str(series.min()),
                'max': str(series.max()),
                'span_days': (series.max() - series.min()).days
            },
            'frequency_analysis': self._analyze_date_frequency(series)
        }
    
    def _analyze_categorical_column(self, col: str) -> Dict[str, Any]:
        """Analisi specifica per colonne categoriche"""
        series = self.df[col].dropna()
        value_counts = series.value_counts()
        
        return {
            'top_values': value_counts.head(10).to_dict(),
            'cardinality_level': self._assess_cardinality(series),
            'text_characteristics': self._analyze_text_characteristics(series) if series.dtype == 'object' else None
        }
    
    def _count_outliers(self, series: pd.Series) -> int:
        """Conta gli outlier usando IQR method"""
        Q1 = series.quantile(0.25)
        Q3 = series.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        return int(((series < lower_bound) | (series > upper_bound)).sum())
    
    def _identify_distribution(self, series: pd.Series) -> str:
        """Identifica il tipo di distribuzione approssimativo"""
        skew = abs(series.skew())
        kurt = series.kurtosis()
        
        if skew < 0.5:
            if -0.5 <= kurt <= 0.5:
                return "normale"
            elif kurt > 0.5:
                return "leptocurtica"
            else:
                return "platicurtica"
        elif skew < 1:
            return "moderatamente_asimmetrica"
        else:
            return "fortemente_asimmetrica"
    
    def _analyze_date_frequency(self, series: pd.Series) -> Dict[str, Any]:
        """Analizza la frequenza delle date"""
        return {
            'daily_counts': len(series.dt.date.value_counts()),
            'monthly_counts': len(series.dt.to_period('M').value_counts()),
            'yearly_counts': len(series.dt.year.value_counts()),
            'weekday_pattern': series.dt.day_name().value_counts().to_dict()
        }
    
    def _assess_cardinality(self, series: pd.Series) -> str:
        """Valuta il livello di cardinalità"""
        unique_ratio = series.nunique() / len(series)
        
        if unique_ratio > 0.95:
            return "alta_cardinalita"
        elif unique_ratio > 0.5:
            return "media_cardinalita"
        elif unique_ratio > 0.1:
            return "bassa_cardinalita"
        else:
            return "categorica"
    
    def _analyze_text_characteristics(self, series: pd.Series) -> Dict[str, Any]:
        """Analizza caratteristiche del testo"""
        text_lengths = series.astype(str).str.len()
        
        return {
            'avg_length': round(text_lengths.mean(), 2),
            'max_length': int(text_lengths.max()),
            'contains_numbers': int(series.astype(str).str.contains(r'\d').sum()),
            'contains_special_chars': int(series.astype(str).str.contains(r'[^\w\s]').sum())
        }
    
    def _assess_data_quality(self) -> Dict[str, Any]:
        """Valuta la qualità generale dei dati"""
        total_cells = self.df.size
        missing_cells = self.df.isna().sum().sum()
        
        return {
            'completeness_score': round((1 - missing_cells / total_cells) * 100, 2),
            'duplicate_rows': int(self.df.duplicated().sum()),
            'columns_with_missing': int((self.df.isna().sum() > 0).sum()),
            'data_quality_issues': self._identify_quality_issues()
        }
    
    def _identify_quality_issues(self) -> List[str]:
        """Identifica problemi di qualità dei dati"""
        issues = []
        
        # Check for completely empty columns
        empty_cols = self.df.columns[self.df.isna().all()].tolist()
        if empty_cols:
            issues.append(f"Colonne completamente vuote: {empty_cols}")
        
        # Check for columns with very high missing rate
        high_missing = self.df.columns[self.df.isna().sum() / len(self.df) > 0.8].tolist()
        if high_missing:
            issues.append(f"Colonne con >80% valori mancanti: {high_missing}")
        
        # Check for potential constant columns
        constant_cols = []
        for col in self.df.columns:
            if self.df[col].nunique() == 1:
                constant_cols.append(col)
        if constant_cols:
            issues.append(f"Colonne con valore costante: {constant_cols}")
        
        return issues
    
    def _find_relationships(self) -> Dict[str, Any]:
        """Trova potenziali relazioni tra colonne"""
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        
        relationships = {
            'high_correlations': [],
            'potential_hierarchies': [],
            'date_relationships': []
        }
        
        # Correlazioni numeriche
        if len(numeric_cols) > 1:
            corr_matrix = self.df[numeric_cols].corr()
            
            for i in range(len(numeric_cols)):
                for j in range(i+1, len(numeric_cols)):
                    corr_val = corr_matrix.iloc[i, j]
                    if abs(corr_val) > 0.7:
                        relationships['high_correlations'].append({
                            'col1': numeric_cols[i],
                            'col2': numeric_cols[j],
                            'correlation': round(corr_val, 3)
                        })
        
        # Potenziali gerarchie (es: città-provincia-regione)
        text_cols = self.df.select_dtypes(include=['object']).columns
        for i, col1 in enumerate(text_cols):
            for col2 in text_cols[i+1:]:
                if self._check_hierarchy(col1, col2):
                    relationships['potential_hierarchies'].append({
                        'parent': col2,
                        'child': col1
                    })
        
        return relationships
    
    def _check_hierarchy(self, col1: str, col2: str) -> bool:
        """Verifica se esiste una relazione gerarchica tra due colonne"""
        # Semplice euristica: se ogni valore di col1 corrisponde a un solo valore di col2
        try:
            grouped = self.df.groupby(col1)[col2].nunique()
            return (grouped == 1).all() and self.df[col1].nunique() > self.df[col2].nunique()
        except:
            return False
    
    def _generate_insights(self) -> List[str]:
        """Genera insights automatici sui dati"""
        insights = []
        
        # Insight sulla dimensione
        rows, cols = self.df.shape
        if rows > 100000:
            insights.append(f"Dataset di grandi dimensioni con {rows:,} righe")
        elif rows < 100:
            insights.append(f"Dataset piccolo con solo {rows} righe")
        
        # Insight sui valori mancanti
        missing_pct = (self.df.isna().sum().sum() / self.df.size) * 100
        if missing_pct > 20:
            insights.append(f"Attenzione: {missing_pct:.1f}% di valori mancanti nel dataset")
        elif missing_pct == 0:
            insights.append("Dataset completo senza valori mancanti")
        
        # Insight sui tipi di dato
        numeric_cols = len(self.df.select_dtypes(include=[np.number]).columns)
        if numeric_cols == 0:
            insights.append("Dataset prevalentemente categorico senza colonne numeriche")
        elif numeric_cols / cols > 0.8:
            insights.append("Dataset prevalentemente numerico")
        
        return insights
    
    def query_data(self, query_type: str, **kwargs) -> Any:
        """Esegue query specifiche sui dati"""
        query_methods = {
            'filter': self._filter_data,
            'aggregate': self._aggregate_data,
            'group_by': self._group_by_data,
            'sort': self._sort_data,
            'top_values': self._get_top_values,
            'correlation': self._get_correlation,
            'distribution': self._get_distribution
        }
        
        if query_type in query_methods:
            return query_methods[query_type](**kwargs)
        else:
            raise ValueError(f"Query type '{query_type}' not supported")
    
    def _filter_data(self, column: str, operator: str, value: Any) -> pd.DataFrame:
        """Filtra i dati"""
        if operator == 'equals':
            return self.df[self.df[column] == value]
        elif operator == 'greater_than':
            return self.df[self.df[column] > value]
        elif operator == 'less_than':
            return self.df[self.df[column] < value]
        elif operator == 'contains':
            return self.df[self.df[column].astype(str).str.contains(str(value), na=False)]
        else:
            raise ValueError(f"Operator '{operator}' not supported")
    
    def _aggregate_data(self, column: str, operation: str) -> float:
        """Calcola aggregazioni"""
        if not pd.api.types.is_numeric_dtype(self.df[column]):
            raise ValueError(f"Column '{column}' is not numeric")
        
        operations = {
            'sum': self.df[column].sum(),
            'mean': self.df[column].mean(),
            'median': self.df[column].median(),
            'std': self.df[column].std(),
            'min': self.df[column].min(),
            'max': self.df[column].max(),
            'count': self.df[column].count()
        }
        
        return operations.get(operation, None)
    
    def _group_by_data(self, group_by: str, agg_column: str, operation: str) -> pd.DataFrame:
        """Raggruppa e aggrega i dati"""
        return self.df.groupby(group_by)[agg_column].agg(operation).reset_index()
    
    def _sort_data(self, column: str, ascending: bool = True) -> pd.DataFrame:
        """Ordina i dati"""
        return self.df.sort_values(by=column, ascending=ascending)
    
    def _get_top_values(self, column: str, n: int = 10) -> pd.Series:
        """Ottiene i valori più frequenti"""
        return self.df[column].value_counts().head(n)
    
    def _get_correlation(self, col1: str, col2: str) -> float:
        """Calcola correlazione tra due colonne"""
        if not (pd.api.types.is_numeric_dtype(self.df[col1]) and 
                pd.api.types.is_numeric_dtype(self.df[col2])):
            raise ValueError("Both columns must be numeric for correlation")
        
        return self.df[col1].corr(self.df[col2])
    
    def _get_distribution(self, column: str, bins: int = 10) -> Dict[str, Any]:
        """Ottiene informazioni sulla distribuzione"""
        if pd.api.types.is_numeric_dtype(self.df[column]):
            hist, bin_edges = np.histogram(self.df[column].dropna(), bins=bins)
            return {
                'type': 'numeric',
                'histogram': {
                    'counts': hist.tolist(),
                    'bin_edges': bin_edges.tolist()
                }
            }
        else:
            value_counts = self.df[column].value_counts()
            return {
                'type': 'categorical',
                'value_counts': value_counts.to_dict()
            }

# Funzione helper per creare il prompt context
def create_data_context(df: pd.DataFrame) -> str:
    """Crea il contesto sui dati per l'AI"""
    analyzer = DataAnalyzer(df)
    summary = analyzer.get_comprehensive_summary()
    
    context = f"""
CONTESTO DATASET:
- Dimensioni: {summary['basic_info']['shape'][0]} righe × {summary['basic_info']['shape'][1]} colonne
- Memoria: {summary['basic_info']['memory_usage']}
- Completezza: {summary['data_quality']['completeness_score']}%
- Righe duplicate: {summary['data_quality']['duplicate_rows']}

COLONNE DISPONIBILI:
"""
    
    for col, info in summary['column_analysis'].items():
        context += f"\n• {col} ({info['dtype']}): "
        context += f"{info['unique_count']} valori unici, "
        context += f"{info['missing_percentage']}% mancanti"
        
        if 'statistics' in info:
            stats = info['statistics']
            context += f" [min: {stats['min']}, max: {stats['max']}, media: {stats['mean']}]"
        elif 'top_values' in info:
            top_vals = list(info['top_values'].keys())[:3]
            context += f" [top valori: {', '.join(map(str, top_vals))}]"
    
    if summary['relationships']['high_correlations']:
        context += f"\n\nCORRELAZIONI SIGNIFICATIVE:"
        for rel in summary['relationships']['high_correlations']:
            context += f"\n• {rel['col1']} ↔ {rel['col2']}: {rel['correlation']}"
    
    if summary['insights']:
        context += f"\n\nINSIGHT AUTOMATICI:"
        for insight in summary['insights']:
            context += f"\n• {insight}"
    
    return context