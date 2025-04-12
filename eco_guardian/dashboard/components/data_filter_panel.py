# eco_guardian/dashboard/components/data_filter_panel.py
import streamlit as st
import pandas as pd
from eco_guardian.utils.data_loader import load_processed_data

def data_filter_panel():
    """Painel lateral para filtros hierárquicos flexíveis"""
    
    default_filters = {
        "landuse_filters": {
            "biomas": [],
            "estados": [],
            "municipios": [],
            "ano_inicio": 2010,
            "ano_fim": 2023,
            "show_diff": True
        }
    }

    with st.sidebar:
        st.header("🌳 Filtros de Análise")
        
        try:
            # Carrega dados com cache
            @st.cache_data
            def load_filter_data():
                return {
                    'desmatamento': load_processed_data('desmatamento_bioma'),
                    'municipios': load_processed_data('br_municipios'),
                    'landuse': load_processed_data('landuse_processed')
                }
                
            data = load_filter_data()
            
            st.markdown("**Filtros de Cobertura Vegetal**")
            
            # Multiselect para Biomas
            biomas = sorted(data['landuse']['bioma'].unique())
            selected_biomas = st.multiselect(
                "Biomas",
                options=biomas,
                default=[],
                help="Selecione um ou mais biomas"
            )
            
            # Estados disponíveis baseados nos biomas selecionados
            estados_disponiveis = sorted(
                data['landuse'][data['landuse']['bioma'].isin(selected_biomas)]['Estado'].unique() 
                if selected_biomas 
                else data['landuse']['Estado'].unique()
            )
            selected_estados = st.multiselect(
                "Estados",
                options=estados_disponiveis,
                default=[],
                help="Selecione um ou mais estados"
            )
            
            # Municípios disponíveis baseados nos filtros anteriores
            municipios_query = []
            if selected_biomas:
                municipios_query.append(f"bioma in {selected_biomas}")
            if selected_estados:
                municipios_query.append(f"Estado in {selected_estados}")
            
            municipios_disponiveis = sorted(
                data['landuse'].query(" & ".join(municipios_query))['dc_municipio'].unique() 
                if municipios_query 
                else data['landuse']['dc_municipio'].unique()
            )
            selected_municipios = st.multiselect(
                "Municípios",
                options=municipios_disponiveis,
                default=[],
                help="Selecione um ou mais municípios"
            )
            
            # Período
            if pd.api.types.is_datetime64_any_dtype(data['landuse']['ano']):
                data['landuse']['ano'] = data['landuse']['ano'].dt.year
            
            min_year = int(data['landuse']['ano'].min())
            max_year = int(data['landuse']['ano'].max())
            landuse_years = st.slider(
                "Período de Análise",
                min_value=min_year,
                max_value=max_year,
                value=(2010, 2023)
            )
            
            show_diff = st.checkbox("Mostrar diferenças anuais", True)
            
            return {
                "landuse_filters": {
                    'biomas': selected_biomas,
                    'estados': selected_estados,
                    'municipios': selected_municipios,
                    'ano_inicio': landuse_years[0],
                    'ano_fim': landuse_years[1],
                    'show_diff': show_diff
                }
            }
            
        except Exception as e:
            st.error(f"Erro ao carregar filtros: {str(e)}")
            return default_filters