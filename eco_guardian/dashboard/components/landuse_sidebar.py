# dashboard/components/landuse_sidebar.py
import streamlit as st
import pandas as pd
from eco_guardian.utils.data_loader import load_processed_data

def landuse_sidebar():
    """Componente de filtros para análise de cobertura vegetal"""
    with st.sidebar:
        st.header("Filtros de Análise")
        
        # Carrega dados processados
        df = load_processed_data("landuse_processed")
        
        # Verifica estrutura dos dados
        if 'bioma' not in df.columns:
            st.error("Dados não contêm coluna 'bioma'")
            return {
                'bioma': None,
                'estado': None,
                'municipio': None,
                'ano_inicio': 2010,
                'ano_fim': 2023,
                'show_diff': True
            }
        
        # Converte a coluna 'ano' para inteiro se for Timestamp
        if 'ano' in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df['ano']):
                df['ano'] = df['ano'].dt.year
            df['ano'] = df['ano'].astype(int)
        
        # Seleção hierárquica Bioma > Estado > Município
        biomas = df['bioma'].unique()
        selected_bioma = st.selectbox(
            "Bioma",
            options=biomas,
            index=0
        )
        
        estados = df[df['bioma'] == selected_bioma]['Estado'].unique()
        selected_estado = st.selectbox(
            "Estado",
            options=estados,
            index=0 if len(estados) > 0 else None
        )
        
        municipios = df[(df['bioma'] == selected_bioma) & 
                       (df['Estado'] == selected_estado)]['dc_municipio'].unique()
        selected_municipio = st.selectbox(
            "Município",
            options=municipios,
            index=0 if len(municipios) > 0 else None
        )
        
        # Seleção de período de análise
        year_range = st.slider(
            "Período de Análise",
            min_value=int(df['ano'].min()),
            max_value=int(df['ano'].max()),
            value=(2010, 2023)
        )
        
        # Configurações de exibição
        show_diff = st.checkbox(
            "Mostrar diferenças anuais",
            value=True,
            help="Exibe a variação ano a ano entre floresta e área agrícola"
        )
        
        return {
            'bioma': selected_bioma,
            'estado': selected_estado,
            'municipio': selected_municipio,
            'ano_inicio': year_range[0],
            'ano_fim': year_range[1],
            'show_diff': show_diff
        }