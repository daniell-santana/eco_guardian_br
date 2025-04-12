import sys
from pathlib import Path

# Adicione esta linha ANTES de qualquer import
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # Ajuste crucial!


# 2. Bibliotecas externas
import streamlit as st
from streamlit_folium import folium_static 
import pandas as pd
import numpy as np
import geopandas as gpd
import plotly.express as px 
import plotly.graph_objects as go
from sklearn.preprocessing import LabelEncoder

# 3. Módulos internos
from eco_guardian.dashboard.components.data_filter_panel import data_filter_panel
from eco_guardian.models import llm_policy, time_series_model
from eco_guardian.utils import data_loader
from eco_guardian.dashboard.components import maps, charts, landuse_viz
from eco_guardian.dashboard.components import landuse_sidebar
from eco_guardian.dashboard.components.geo import geo_filters
from eco_guardian.dashboard.components import policy_dashboard
from eco_guardian.models.time_series_model import UnifiedForecaster

# Atalhos para classes/funções usadas frequentemente
PolicyAnalyzer = llm_policy.PolicyAnalyzer
load_processed_data = data_loader.load_processed_data
GeoFilter = geo_filters.GeoFilter

# ===================================
# CONFIGURAÇÕES FORMATAÇÃO NUMEROS
# ===================================
def formatar_br(valor):
    """Formata números no padrão brasileiro com separadores de milhar"""
    return f"{valor:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")

def formatar_campos_futebol(valor):
    """Formata o número de campos de futebol de forma inteligente"""
    valor = abs(valor)  # Garante que seja positivo para a formatação
    
    if valor >= 1_000_000:
        return f"{valor/1_000_000:,.1f} milhões".replace(",", "X").replace(".", ",").replace("X", ".")
    elif valor >= 1_000:
        return f"{valor/1_000:,.1f} mil".replace(",", "X").replace(".", ",").replace("X", ".")
    return formatar_br(valor)

# ======================
# CONFIGURAÇÕES DA PÁGINA
# ======================
def configure_page():
    """Configurações iniciais da página"""
    st.set_page_config(
        page_title="EcoGuardian - Monitoramento Ambiental",
        layout="wide",
        page_icon="🌳"
    )
    st.markdown("""
        <style>
            .main {padding: 2rem 3rem;}
            .stAlert {padding: 20px;}
            .stTabs [data-baseweb="tab-list"] {
                gap: 10px;
            }
            .metric-box {border: 1px solid #e6e6e6; border-radius: 8px; padding: 1rem;}
        </style>
    """, unsafe_allow_html=True)

# ======================
# COMPONENTES PRINCIPAIS
# ======================
def policy_analysis_section():
    """Seção de análise de políticas com IA"""
    analyzer = PolicyAnalyzer()
    with st.expander("🔍 Análise de Políticas Ambientais com IA", expanded=True):
        uploaded_file = st.file_uploader(
            "Carregue documento de política ambiental (PDF)",
            type="pdf",
            key="policy_upload"
        )
        
        if uploaded_file:
            with st.spinner("Analisando documento..."):
                try:
                    analysis = analyzer.analyze_policy(uploaded_file.read())
                    st.success("Análise concluída!")
                    st.markdown(f"**Insights do documento:**\n\n{analysis}")
                except Exception as e:
                    st.error(f"Erro na análise: {str(e)}")

def data_filter_panel():
    """Painel lateral para filtros hierárquicos flexíveis"""
    
    default_filters = {
        "mapa_nacional": {
            "year": 2023,
            "biomas": [],
            "estados": [],
            "municipios": [],
            "prodes_data": None,
            "map_data": None
        },
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
                prodes = load_processed_data('prodes')
                municipios = load_processed_data('br_municipios')
                landuse = load_processed_data('landuse_processed')

                # Garantir que não há None em colunas críticas
                prodes['bioma'] = prodes['bioma'].fillna('Não informado')
                municipios['NM_UF'] = municipios['NM_UF'].fillna('Estado não identificado')
                municipios['NM_MUN'] = municipios['NM_MUN'].fillna('Município não identificado')
                
                # Criar relação estável município-bioma para o mapa
                relacao_biomas = prodes.groupby('cd_municipio').agg(
                    bioma=('bioma', lambda x: x.mode()[0] if not x.mode().empty else 'Não informado')
                ).reset_index()

                # Converter explicitamente None para 'Não informado'
                relacao_biomas['bioma'] = relacao_biomas['bioma'].apply(
                    lambda x: 'Não informado' if x is None else x
                )

                # Após o merge, garantir substituição de NaN e None
                merged_mapa = municipios.merge(
                    relacao_biomas,
                    on='cd_municipio',
                    how='left'
                ).fillna({
                    'bioma': 'Não informado',
                    'NM_UF': 'Estado não identificado',
                    'NM_MUN': 'Município não identificado'
                })
                
                # Garantir substituição de NaN e None na coluna final
                merged_mapa['bioma'] = merged_mapa['bioma'].apply(
                    lambda x: 'Não informado' if x is None else x
                )
                return {
                    'prodes': prodes,
                    'landuse': landuse,
                    'map_data': merged_mapa
                }
                
            data = load_filter_data()
            
            # Tabs principais com keys únicas
            tab_mapa, tab_landuse = st.tabs(["Mapa Nacional", "Cobertura Vegetal"])
            
            with tab_mapa:
                st.markdown("**Filtros para o Mapa**")
                
                # Filtro de ano para o mapa
                min_year = int(data['prodes']['ano'].min())
                max_year = int(data['prodes']['ano'].max())
                selected_year = st.selectbox(
                    "Ano de referência",
                    options=sorted(data['prodes']['ano'].unique(), reverse=True),
                    index=0,
                    key='map_year_unique'
                )
                
                # Filtros hierárquicos para o mapa
                biomas_mapa = sorted([
                    str(b) for b in data['map_data']['bioma'].unique() 
                    if b not in [None, 'Não informado']
                ], key=str.lower)
                
                selected_biomas_mapa = st.multiselect(
                    "Biomas para realce",
                    options=biomas_mapa,
                    default=["Amazônia"] if "Amazônia" in biomas_mapa else [],
                    key='map_biomas_unique'
                )

                # Estados disponíveis baseados nos biomas selecionados
                estados_base = data['map_data'][data['map_data']['NM_UF'].notna()]
                estados_disponiveis_mapa = sorted(
                    estados_base['NM_UF'].unique(), 
                    key=str.lower
                )
                
                selected_estados_mapa = st.multiselect(
                    "Estados para realce",
                    options=estados_disponiveis_mapa,
                    default=[],
                    key='map_estados_unique'
                )
                
                # Municípios disponíveis baseados nos filtros anteriores
                municipios_base = data['map_data'][data['map_data']['NM_MUN'].notna()]
                if selected_estados_mapa:
                    municipios_disponiveis_mapa = sorted(
                        municipios_base[
                            municipios_base['NM_UF'].isin(selected_estados_mapa)
                        ]['NM_MUN'].unique(),
                        key=str.lower
                    )
                else:
                    municipios_disponiveis_mapa = sorted(
                        municipios_base['NM_MUN'].unique(),
                        key=str.lower
                    )
                
                selected_municipios_mapa = st.multiselect(
                    "Municípios para realce",
                    options=municipios_disponiveis_mapa,
                    default=[],
                    key='map_municipios_unique'
                )
  
            with tab_landuse:
                st.markdown("**Filtros de Cobertura Vegetal**")
                
                # Dados específicos para landuse
                landuse_data = data['landuse'].copy()
                
                # Filtros independentes para landuse
                biomas_landuse = sorted(landuse_data['bioma'].unique())
                selected_biomas_landuse = st.multiselect(
                    "Biomas",
                    options=biomas_landuse,
                    default=[],
                    key='landuse_biomas_unique',
                    help="Selecione um ou mais biomas"
                )
  
                # Estados disponíveis baseados nos biomas selecionados
                estados_disponiveis_landuse = sorted(
                    landuse_data[landuse_data['bioma'].isin(selected_biomas_landuse)]['Estado'].unique() 
                    if selected_biomas_landuse 
                    else landuse_data['Estado'].unique()
                )
                selected_estados_landuse = st.multiselect(
                    "Estados",
                    options=estados_disponiveis_landuse,
                    default=[],
                    key='landuse_estados_unique',
                    help="Selecione um ou mais estados"
                )
        
                # Municípios disponíveis baseados nos filtros anteriores
                municipios_query = []
                if selected_biomas_landuse:
                    municipios_query.append(f"bioma in {selected_biomas_landuse}")
                if selected_estados_landuse:
                    municipios_query.append(f"Estado in {selected_estados_landuse}")
                
                municipios_disponiveis_landuse = sorted(
                    landuse_data.query(" & ".join(municipios_query))['dc_municipio'].unique() 
                    if municipios_query 
                    else landuse_data['dc_municipio'].unique()
                )
                selected_municipios_landuse = st.multiselect(
                    "Municípios",
                    options=municipios_disponiveis_landuse,
                    default=[],
                    key='landuse_municipios_unique',
                    help="Selecione um ou mais municípios"
                )
             
                # Período temporal
                if pd.api.types.is_datetime64_any_dtype(landuse_data['ano']):
                    landuse_data['ano'] = landuse_data['ano'].dt.year
                
                min_year_landuse = int(landuse_data['ano'].min())
                max_year_landuse = int(landuse_data['ano'].max())
                landuse_years = st.slider(
                    "Período de Análise",
                    min_value=min_year_landuse,
                    max_value=max_year_landuse,
                    value=(1990, 2023),
                    key='landuse_years_unique'
                )
                
                show_diff = st.checkbox(
                    "Mostrar diferenças anuais", 
                    True, 
                    key='landuse_show_diff_unique'
                )
            
            return {
                "mapa_nacional": {
                    'year': int(selected_year),
                    'biomas': [str(b) for b in selected_biomas_mapa if b not in [None, 'Não informado']],
                    'estados': [str(e) for e in selected_estados_mapa if e is not None],
                    'municipios': [str(m) for m in selected_municipios_mapa if m is not None],
                    'prodes_data': data['prodes'],
                    'map_data': data['map_data']
                },
                "landuse_filters": {
                    'biomas': [str(b) for b in selected_biomas_landuse if b is not None],
                    'estados': [str(e) for e in selected_estados_landuse if e is not None],
                    'municipios': [str(m) for m in selected_municipios_landuse if m is not None],
                    'ano_inicio': int(landuse_years[0]),
                    'ano_fim': int(landuse_years[1]),
                    'show_diff': bool(show_diff)
                }
            }
            
        except Exception as e:
            st.error(f"Erro ao carregar filtros: {str(e)}")
            return default_filters

# ======================
# SERVIÇO DE PROJEÇÃO
# ======================
class ProjectionService:
    @staticmethod
    @st.cache_data
    def load_projection_data():
        """Carrega dados já no formato agrupado correto, com compatibilidade para 'taxa_conversao_anual'"""
        df = load_processed_data('landuse_processed')
        
        # Dicionário de bioma predominante por estado (já existente na classe)
        ESTADO_BIOMA = {
            'Acre': 'Amazônia',
            'Alagoas': 'Caatinga',
            'Amapá': 'Amazônia',
            'Amazonas': 'Amazônia',
            'Bahia': 'Caatinga',
            'Ceará': 'Caatinga',
            'Distrito Federal': 'Cerrado',
            'Espírito Santo': 'Mata Atlântica',
            'Goiás': 'Cerrado',
            'Maranhão': 'Cerrado',
            'Mato Grosso': 'Amazônia',
            'Mato Grosso do Sul': 'Cerrado',
            'Minas Gerais': 'Cerrado',
            'Pará': 'Amazônia',
            'Paraíba': 'Caatinga',
            'Paraná': 'Mata Atlântica',
            'Pernambuco': 'Caatinga',
            'Piauí': 'Caatinga',
            'Rio de Janeiro': 'Mata Atlântica',
            'Rio Grande do Norte': 'Caatinga',
            'Rio Grande do Sul': 'Pampa',
            'Rondônia': 'Amazônia',
            'Roraima': 'Amazônia',
            'Santa Catarina': 'Mata Atlântica',
            'São Paulo': 'Cerrado',
            'Sergipe': 'Caatinga',
            'Tocantins': 'Amazônia'
        }

        # Filtra apenas os registros do bioma predominante de cada estado
        df['bioma_predominante'] = df['Estado'].map(ESTADO_BIOMA)
        df = df[df['bioma'] == df['bioma_predominante']]
        
        # Garante que 'y' existe, usando 'taxa_conversao_anual' se necessário
        if 'y' not in df.columns:
            df['y'] = df['taxa_conversao_anual'] 
        
        # Renomeia coluna de data
        df = df.rename(columns={'ano': 'ds'})
        
        # Agrega por estado e ano (agora só terá um registro por estado/ano)
        df = df.groupby(['Estado', 'ds', 'bioma']).agg({
            'area_fazenda_ha': 'sum',
            'area_floresta_ha': 'sum',
            'y': lambda x: np.average(x, weights=df.loc[x.index, 'area_floresta_ha'])
        }).reset_index()
        
        df['ds'] = pd.to_datetime(df['ds'], format='%Y')
        return df

    @staticmethod
    def generate_state_projection(estado_selecionado, anos_projecao):
        try:
            # Mapeamento de siglas dos estados
            SIGLAS_ESTADOS = {
                'Acre': 'AC', 'Alagoas': 'AL', 'Amapá': 'AP', 'Amazonas': 'AM',
                'Bahia': 'BA', 'Ceará': 'CE', 'Distrito Federal': 'DF', 'Espírito Santo': 'ES',
                'Goiás': 'GO', 'Maranhão': 'MA', 'Mato Grosso': 'MT', 'Mato Grosso do Sul': 'MS',
                'Minas Gerais': 'MG', 'Pará': 'PA', 'Paraíba': 'PB', 'Paraná': 'PR',
                'Pernambuco': 'PE', 'Piauí': 'PI', 'Rio de Janeiro': 'RJ', 'Rio Grande do Norte': 'RN',
                'Rio Grande do Sul': 'RS', 'Rondônia': 'RO', 'Roraima': 'RR',
                'Santa Catarina': 'SC', 'São Paulo': 'SP', 'Sergipe': 'SE', 'Tocantins': 'TO'
            }

            # Obtém a sigla do estado selecionado
            sigla = SIGLAS_ESTADOS.get(estado_selecionado)
            if not sigla:
                raise ValueError(f"Sigla não encontrada para o estado: {estado_selecionado}")

            # Carrega e prepara os dados históricos
            df_historico = ProjectionService.load_projection_data()
            df_estado = df_historico[df_historico['Estado'] == estado_selecionado]

            if df_estado.empty:
                raise ValueError(f"Nenhum dado disponível para {estado_selecionado}")

            ultimo_ano = df_estado.iloc[-1]
            
            # Calcula a proporção de floresta
            total_area = ultimo_ano['area_fazenda_ha'] + ultimo_ano['area_floresta_ha']
            prop_floresta = ultimo_ano['area_floresta_ha'] / total_area if total_area > 0 else 0.0

            # Prepara as condições iniciais
            condicoes = {
                'Estado': estado_selecionado,
                'bioma': ultimo_ano['bioma'],
                'area_fazenda_ha': float(ultimo_ano['area_fazenda_ha']),
                'area_floresta_ha': float(ultimo_ano['area_floresta_ha']),
                'y': float(ultimo_ano['y']),
                'prop_floresta': float(prop_floresta),
                'last_year': int(df_estado['ds'].dt.year.iloc[-1]), 
                'estado_code': int(forecaster.encoder_estados.transform([estado_selecionado])[0]) 
 
            } 

            # Carrega o modelo e codifica o estado
            model_path = Path(f"eco_guardian/models/saved_models/unified_prophet_v4_{sigla}.pkl")
            if not model_path.exists():
                raise FileNotFoundError(f"Modelo para {estado_selecionado} não encontrado em: {model_path}")

            forecaster = UnifiedForecaster.load_model(model_path)
            condicoes['estado_code'] = int(forecaster.encoder_estados.transform([estado_selecionado])[0])

            # Gera a previsão
            forecast = forecaster.predict(condicoes, anos_projecao)
            
            return {
                'forecast': forecast,
                'historical_data': df_estado,
                'initial_conditions': condicoes
            }
            
        except Exception as e:
            st.error(f"Erro na projeção: {str(e)}")
            return None

    def render_projection_results(result, anos_projecao):
        """Renderiza gráficos e métricas dos resultados com fontes aumentadas"""
        if not result:
            return
            
        forecast = result['forecast']
        df_estado = result['historical_data']
        condicoes = result['initial_conditions']
        
        # Garante que o último ano histórico seja igual ao primeiro ano projetado
        last_historical_year = df_estado['ds'].max()
        first_proj_year = forecast['data'].min()
        
        if last_historical_year != first_proj_year:
            transition_point = pd.DataFrame({
                'data': [last_historical_year],
                'conversao_ha_prevista': [df_estado['y'].iloc[-1]],
                'Estado': [condicoes['Estado']],
                'bioma': [condicoes['bioma']]
            })
            forecast = pd.concat([transition_point, forecast], ignore_index=True)

        # ========== CONFIGURAÇÃO DO GRÁFICO COM FONTES AUMENTADAS ==========
        fig = go.Figure()
        
        # Linha de equilíbrio (0%)
        fig.add_hline(
            y=0, 
            line_dash="dot", 
            line_color="rgba(255, 0, 0, 0.7)",  # Vermelho com 70% de opacidade
            annotation_text="Linha de equilíbrio (0%)", 
            annotation_position="bottom right",
            annotation_font=dict(
                size=10, 
                color="white"  # Texto em branco (ou use "rgb(255,255,255)")
            ),
            line_width=1.5
        )
        
        # Dados históricos
        fig.add_trace(go.Scatter(
            x=df_estado['ds'], 
            y=df_estado['y'],
            name="Histórico",
            line=dict(color='blue', width=3),
            mode='lines+markers',
            marker=dict(size=8),
            hovertemplate='<b>Ano</b>: %{x|%Y}<br><b>Taxa</b>: %{y:.2%}<extra></extra>'
        ))
        
        # Projeção
        fig.add_trace(go.Scatter(
            x=forecast['data'],
            y=forecast['conversao_ha_prevista'],
            name="Previsão",
            line=dict(color='orange', width=3, dash='dot'),
            mode='lines+markers',
            marker=dict(size=8),
            hovertemplate='<b>Ano</b>: %{x|%Y}<br><b>Previsão</b>: %{y:.2%}<extra></extra>'
        ))
        
        # Layout com fontes aumentadas
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',  # Fundo do gráfico
            paper_bgcolor='rgba(0,0,0,0)', # Área externa do gráfico
            font=dict(color='white'), # Cor padrão do texto

            title={
                'text': f"<b>Projeção para {condicoes['Estado']}</b>",
                'font': {'size': 22, 'family': "Arial, sans-serif"},
                'x': 0.5,
                'xanchor': 'center'
            },
            xaxis={
                'title': '<b>Ano</b>',
                'title_font': {'size': 18},
                'tickfont': {'size': 14},
                'gridcolor': 'rgba(255, 255, 255, 0.5)',  # Branco com 10% de opacidade
            },
            yaxis={
                'title': 'Taxa de Evolução Cobertura Florestal (%)',
                'title_font': {'size': 12},
                'tickfont': {'size': 12},
                'tickformat': '.2%',
                'gridcolor': 'rgba(255, 255, 255, 0.5)'
            },
            legend={
            'font': {'size': 12, 'color': 'white'},
            'orientation': 'h',
            'y': -0.2,
            'bgcolor': 'rgba(0,0,0,0)'
            },
        
            hoverlabel={
                'font': {'size': 14},
                'bgcolor': 'rgba(40, 40, 40, 0.9)',
                'bordercolor': 'white'
            }
        )

        st.plotly_chart(fig, use_container_width=True)
        
        # ========== MÉTRICAS ==========
        col1, col2, col3, col4 = st.columns(4)
        variacao = forecast['conversao_ha_prevista'].iloc[-1] - df_estado['y'].iloc[-1]
        area_perdida = condicoes['area_floresta_ha'] * abs(variacao)
        
        with col1:
            st.metric("Bioma", condicoes['bioma'])
        with col2:
            st.metric("Última Taxa Registrada", f"{df_estado['y'].iloc[-1]:.2%}")
        with col3:
            st.metric("Variação Projetada", f"{variacao:+.2%}", delta_color="inverse")
        with col4:
            st.metric(
                "Área Florestal Afetada", 
                f"{formatar_br(abs(area_perdida))} ha", 
                help="Área projetada de perda/ganho até o final da projeção"
            )

        # ========== INTERPRETAÇÃO COM FONTE AUMENTADA ==========
        area_perdida_abs = abs(area_perdida)
        campos_futebol = area_perdida_abs / 1.08
        
        st.markdown(
            f"""
            <div style='font-size: 16px; line-height: 1.6; margin-top: 10px;'>
            <b>🌳 Interpretação:</b> Uma variação de {variacao:+.2%} significa que, em {anos_projecao} anos,
            a cobertura florestal de {condicoes['Estado']} poderá {'diminuir ⬇️' if variacao < 0 else 'aumentar ⬆️'}
            em aproximadamente <b>{formatar_br(area_perdida_abs)} hectares</b> 
            (⚽ equivalente a <b>{formatar_campos_futebol(campos_futebol)} campos de futebol</b>).
            <br><br>
            <span style='font-size: 14px;'>
            *Considerando 1 campo de futebol padrão = 1,08 hectare (108m × 68m)*
            </span>
            </div>
            """, 
            unsafe_allow_html=True
        )
# ======================
# FUNÇÃO PRINCIPAL
# ======================
def main():
    configure_page()
    filters = data_filter_panel()
    
    st.title("🌍 EcoGuardian - Painel Nacional de Monitoramento")
    
    tab1, tab4, tab2, tab3 = st.tabs([
        "Mapa Nacional",
        "Cobertura Vegetal",
        "Indicadores Econômicos", 
        "Análise Política"
    ])

    with tab1:
        with st.container():
            st.header("Mapa Nacional de Desmatamento por Bioma")
            
            # Usa os filtros já carregados
            mapa_filters = filters['mapa_nacional']

            # Container para o mapa e métricas
            map_col, metrics_col = st.columns([4, 1])
            
            with map_col:
                try:
                    # Carrega os dados necessários (já carregados nos filtros)
                    prodes_data = mapa_filters['prodes_data']
                    municipios_data = mapa_filters['map_data']
                    selected_year = mapa_filters['year']
                    
                    # Container para o mapa (fixo para animação)
                    map_container = st.empty()

                    # Cria e exibe o mapa inicial com Folium e filtros
                    m = maps.render_br_map_folium(
                        year=selected_year,
                        selected_biomas=mapa_filters['biomas'],
                        selected_estados=mapa_filters['estados'],
                        selected_municipios=mapa_filters['municipios'],
                        prodes_data=prodes_data,
                        municipios_data=municipios_data
                    )
                    
                    if m:
                        with map_container:
                            folium_static(m, height=1100, width=1100)

                except Exception as e:
                    st.error(f"Erro ao carregar o mapa: {str(e)}")

            with metrics_col:
                # Container principal
                st.markdown("""
                    <div style="margin-bottom: 10px;">
                        <h4 style='font-size: 18px; margin-bottom: 4px;'>📊 Desmatamento Acumulado por Bioma</h4>
                        <div class="tooltip" style="margin-bottom: 8px;">
                            <small>ℹ️ Legenda dos Indicadores</small>
                            <span class="tooltiptext">
                                <div style="text-align: left; line-height: 1.4; padding: 8px;">
                                    <strong style="color: #FF4B4B;">▲ + Valor:</strong> Aumento no desmatamento<br>
                                    <strong style="color: #0F9D58;">▲ - Valor:</strong> Redução no desmatamento<br><br>
                                    <strong style="color: #FF4B4B;">★ + Valor:</strong> Aceleração da tendência<br>
                                    <strong style="color: #0F9D58;">★ - Valor:</strong> Desaceleração da tendência
                                </div>
                            </span>
                        </div>
                    </div>
                    <style>
                        .tooltip {
                            position: relative;
                            display: inline-block;
                            cursor: help;
                        }
                        .tooltip .tooltiptext {
                            visibility: hidden;
                            width: 260px;
                            background-color: #1a1a1a;
                            color: #fff;
                            text-align: left;
                            border-radius: 6px;
                            padding: 12px;
                            position: absolute;
                            z-index: 999;
                            bottom: 150%;
                            left: 50%;
                            margin-left: -130px;
                            opacity: 0;
                            transition: opacity 0.3s;
                            border: 1px solid #4CAF50;
                            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
                            font-size: 14px;
                        }
                        .tooltip:hover .tooltiptext {
                            visibility: visible;
                            opacity: 1;
                        }
                        .metric-box {
                            border: 1px solid #2d2d2d;
                            border-radius: 8px;
                            padding: 12px;
                            margin-bottom: 12px;
                            background: #0e1117;
                        }
                        .metric-label {
                            font-size: 16px;
                            color: #8b8b8b;
                            margin-bottom: 4px;
                        }
                        .metric-value {
                            font-size: 28px;
                            font-weight: 500;
                            margin: 8px 0;
                        }
                        .delta-container {
                            font-size: 14px;
                            margin-top: 6px;
                        }
                        .delta-line {
                            line-height: 1.4;
                            margin: 4px 0;
                        }
                        .taxa-line {
                            line-height: 1.4;
                            margin: 4px 0;
                        }
                    </style>
                """.strip(), unsafe_allow_html=True)

                try:
                    desmatamento = load_processed_data('prodes')
                    current_year_data = desmatamento[desmatamento['ano'] == selected_year]

                    # Cálculo do ranking de biomas
                    biomas_ranking = current_year_data.groupby('bioma')['desmatado'] \
                        .sum() \
                        .sort_values(ascending=False) \
                        .reset_index()

                    for _, row in biomas_ranking.iterrows():
                        bioma = row['bioma']
                        area_desmatada = row['desmatado']
                        area_formatada = f"{area_desmatada:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

                        delta_content = ""
                        taxa_content = ""
                        show_taxa = False

                        if selected_year > min(desmatamento['ano']):
                            # Dados do ano anterior (variação anual)
                            area_anterior = desmatamento[
                                (desmatamento['ano'] == selected_year - 1) & 
                                (desmatamento['bioma'] == bioma)
                            ]['desmatado'].sum()

                            if area_anterior > 0:
                                # Cálculo variação anual
                                diferenca = area_desmatada - area_anterior
                                variacao_anual = (diferenca / area_anterior) * 100
                                
                                # Formatação BR e cores condicionais
                                dif_br = f"{diferenca:+,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                                var_br = f"{variacao_anual:+.1f}".replace(".", ",")
                                delta_color = "#FF4B4B" if diferenca > 0 else "#0F9D58"
                                
                                # Cálculo da variação de tendência (ΔTaxa)
                                if selected_year >= (min(desmatamento['ano']) + 2):
                                    area_2_anos_atras = desmatamento[
                                        (desmatamento['ano'] == selected_year - 2) & 
                                        (desmatamento['bioma'] == bioma)
                                    ]['desmatado'].sum()
                                    
                                    if area_2_anos_atras > 0:
                                        # Cálculo da tendência
                                        desmatamento_periodo_anterior = area_anterior - area_2_anos_atras
                                        desmatamento_periodo_atual = diferenca
                                        
                                        if desmatamento_periodo_anterior != 0:
                                            variacao_taxa = (
                                                (desmatamento_periodo_atual - desmatamento_periodo_anterior) / 
                                                abs(desmatamento_periodo_anterior)
                                            ) * 100
                                            
                                            # Formatação e cor condicional
                                            taxa_color = "#FF4B4B" if variacao_taxa > 0 else "#0F9D58"
                                            taxa_br = f"{variacao_taxa:+.1f}".replace(".", ",")
                                            taxa_content = f"""
                                            <div class="taxa-line">
                                                <span style="color: {taxa_color};">★ {taxa_br}% (vs. período anterior)</span>
                                            </div>
                                            """
                                            show_taxa = True

                                delta_content = f"""
                                <div class="delta-container">
                                    <div class="delta-line">
                                        <span style="color: {delta_color};">▲ {var_br}% ({dif_br} km²) vs {selected_year - 1}</span>
                                    </div>
                                    {taxa_content if show_taxa else ''}
                                </div>
                                """.replace("\n", "").replace("  ", "")

                            elif area_anterior == 0 and area_desmatada > 0:
                                dif_br = f"{area_desmatada:+,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                                delta_content = f"""
                                <div class="delta-line" style="color: #FF4B4B;">
                                    ⚠️ Novo registro: {dif_br} km²
                                </div>
                                """.replace("\n", "").replace("  ", "")

                        # Exibição da métrica
                        st.markdown(f"""
                        <div class="metric-box">
                            <div class="metric-label">{bioma}</div>
                            <div class="metric-value">{area_formatada} km²</div>
                            {delta_content}
                        </div>
                        """.strip().replace("    ", ""), unsafe_allow_html=True)

                    # Total Geral (mesma lógica aplicada)
                    total_desmatado = current_year_data['desmatado'].sum()
                    total_formatado = f"{total_desmatado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    
                    total_content = ""
                    if selected_year > min(desmatamento['ano']):
                        total_anterior = desmatamento[desmatamento['ano'] == selected_year - 1]['desmatado'].sum()
                        
                        if total_anterior > 0:
                            diferenca_total = total_desmatado - total_anterior
                            var_total = (diferenca_total / total_anterior) * 100
                            dif_br = f"{diferenca_total:+,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                            var_br = f"{var_total:+.1f}".replace(".", ",")
                            delta_color_total = "#FF4B4B" if diferenca_total > 0 else "#0F9D58"
                            
                            # Cálculo ΔTaxa para total
                            if selected_year >= (min(desmatamento['ano']) + 2):
                                total_2_anos_atras = desmatamento[
                                    desmatamento['ano'] == selected_year - 2
                                ]['desmatado'].sum()
                                
                                if total_2_anos_atras > 0:
                                    desmatamento_periodo_anterior_total = total_anterior - total_2_anos_atras
                                    desmatamento_periodo_atual_total = diferenca_total
                                    
                                    if desmatamento_periodo_anterior_total != 0:
                                        variacao_taxa_total = (
                                            (desmatamento_periodo_atual_total - desmatamento_periodo_anterior_total) / 
                                            abs(desmatamento_periodo_anterior_total)
                                        ) * 100
                                        
                                        taxa_color_total = "#FF4B4B" if variacao_taxa_total > 0 else "#0F9D58"
                                        taxa_br_total = f"{variacao_taxa_total:+.1f}".replace(".", ",")
                                        taxa_content_total = f"""
                                        <div class="taxa-line">
                                            <span style="color: {taxa_color_total};">★ {taxa_br_total}% (vs. período anterior)</span>
                                        </div>
                                        """.replace("\n", "").replace("  ", "")
                            
                            total_content = f"""
                            <div class="delta-container">
                                <div class="delta-line">
                                    <span style="color: {delta_color_total};">▲ {var_br}% ({dif_br} km²) vs {selected_year - 1}</span>
                                </div>
                                {taxa_content_total if 'taxa_content_total' in locals() else ''}
                            </div>
                            """.replace("\n", "").replace("  ", "")

                    st.divider()
                    st.markdown(f"""
                    <div class="metric-box" style="border-color: #4CAF50;">
                        <div class="metric-label">TOTAL GERAL</div>
                        <div style="font-size: 32px; font-weight: 600;">{total_formatado} km²</div>
                        {total_content}
                    </div>
                    """.strip().replace("    ", ""), unsafe_allow_html=True)

                except Exception as e:
                    st.error(f"Erro ao calcular métricas: {str(e)}")
            
            # =============================================
            # SEÇÃO: Gráfico 100% Stacked + Análise
            # =============================================
            st.markdown("---")
            st.subheader("📈 Evolução Percentual por Bioma")
            
            # Container com 2 colunas (gráfico + insights)
            chart_col, insight_col = st.columns([3, 1])
            
            with chart_col:
                try:
                    # Renderiza o gráfico de área 100% empilhado
                    stack_chart = maps.render_stacked_area_bioma()
                    if stack_chart:
                        stack_chart.update_layout(height=500)  # Aumente este valor conforme necessário
                        st.plotly_chart(stack_chart, use_container_width=True)
                    else:
                        st.warning("Dados insuficientes para gerar o gráfico")
                        
                except Exception as e:
                    st.error(f"Erro ao gerar gráfico: {str(e)}")
            
            with insight_col:
                st.markdown("""
                    #### Principais Insights
                    - **Maior Taxa de Crescimento de Área Desmatada (2000-2023):** Mata Atlântica + 4,4%  |  Amazônia: + 3,92%  | Caatinga:  +0,97%
                    - **Tendência dominante**: A amazônia e o cerrado são os biomas que concentram a maior parte do desmatamento do Brasil.
                    - **Mudanças recentes**: O Cerrado, apesar de ter um crescimento menor em termos percentuais, já possui a maior área desmatada entre os biomas, com 32,83% em 2023.
                    - **Bioma preservado**: O Pampa apresentou uma redução na área desmatada, passando de 5,52% em 2000 para 3,68% em 2023.
                    """)
                
                # Botão para detalhes (opcional)
                if st.button("🔍 Metodologia", key="method_btn"):
                    st.info("""
                        Dados normalizados para porcentagem do total anual.  
                        Fontes: PRODES/INPE (2000-2023)  
                        Atualização: Trimestral
                        """)

            # Linha divisória para próxima seção
            st.markdown("---")
        
        # =============================================
    with tab2:
        with st.container():
            st.header("Análise Econômica-Ambiental")
            
            #seletor de período para análise econômica
            min_year = 2014
            max_year = 2021  # Atualizar conforme novos dados
            year_range = st.slider(
                "Selecione o período para análise econômica",
                min_value=min_year,
                max_value=max_year,
                value=(max(min_year, 2014), min(max_year, 2021))
            )
            
            # Chama as funções de análise
            try:
                # Primeiro mostra o mapa e gráfico de culturas
                charts.display_economic_impact_map({
                    'start_year': year_range[0],
                    'end_year': year_range[1]
                })
                
                # Depois mostra a análise de correlação existente
                charts.display_agro_correlation({
                    'start_year': year_range[0],
                    'end_year': year_range[1]
                })
                
            except Exception as e:
                st.error(f"Erro na análise econômica: {str(e)}")

    with tab3:
        policy_dashboard.show_policy_dashboard()  # Substitui a chamada antiga
        st.divider()

    with tab4:
        with st.container():
            st.header("Dinâmica de Uso do Solo")
            
            # Container único para os gráficos (100% width)
            try:
                landuse_viz.show_landuse_analysis({
                    'biomas': filters['landuse_filters'].get('biomas', []),
                    'estados': filters['landuse_filters'].get('estados', []),
                    'municipios': filters['landuse_filters'].get('municipios', []),
                    'ano_inicio': filters['landuse_filters'].get('ano_inicio', 2000),
                    'ano_fim': filters['landuse_filters'].get('ano_fim', 2023)
                })
            except Exception as e:
                st.error(f"Erro na análise de cobertura: {str(e)}")
            
            # --- NOVA SEÇÃO DE PROJEÇÃO ---
            st.markdown("---")
            st.subheader("🔮 Simulação de Cenários Futuros")
                   
            col1, col2 = st.columns(2)
            with col1:
                try:
                    estados_disponiveis = ProjectionService.load_projection_data()['Estado'].unique()
                    estado_selecionado = st.selectbox(
                        "Selecione o Estado",
                        options=sorted(estados_disponiveis),
                        index=0
                    )
                except Exception as e:
                    st.error(f"Erro ao carregar estados: {str(e)}")
                    st.stop()
            
            with col2:
                anos_projecao = st.slider(  # DEFINA AQUI A VARIÁVEL
                "Horizonte de Projeção (anos)",
                min_value=1,
                max_value=5,
                value=5,
                key="proj_years",  # Chave única para o slider
                help="Período para projeção futura"
            )
            
            if st.button("▶️ Gerar Projeção", type="primary"):
                try:
                    # Mapeamento de siglas dos estados
                    SIGLAS_ESTADOS = {
                        'Acre': 'AC', 'Alagoas': 'AL', 'Amapá': 'AP', 'Amazonas': 'AM',
                        'Bahia': 'BA', 'Ceará': 'CE', 'Distrito Federal': 'DF', 'Espírito Santo': 'ES',
                        'Goiás': 'GO', 'Maranhão': 'MA', 'Mato Grosso': 'MT', 'Mato Grosso do Sul': 'MS',
                        'Minas Gerais': 'MG', 'Pará': 'PA', 'Paraíba': 'PB', 'Paraná': 'PR',
                        'Pernambuco': 'PE', 'Piauí': 'PI', 'Rio de Janeiro': 'RJ', 'Rio Grande do Norte': 'RN',
                        'Rio Grande do Sul': 'RS', 'Rondônia': 'RO', 'Roraima': 'RR',
                        'Santa Catarina': 'SC', 'São Paulo': 'SP', 'Sergipe': 'SE', 'Tocantins': 'TO'
                    }

                    # Carrega e prepara os dados
                    df_historico = ProjectionService.load_projection_data()
                    df_estado = df_historico[df_historico['Estado'] == estado_selecionado]
                    
                    if df_estado.empty:
                        raise ValueError(f"Nenhum dado disponível para {estado_selecionado}")

                    ultimo_ano = df_estado.iloc[-1]
                    
                    # Carrega o modelo específico do estado
                    sigla = SIGLAS_ESTADOS.get(estado_selecionado)
                    if not sigla:
                        raise ValueError(f"Sigla não encontrada para o estado: {estado_selecionado}")
                        
                    model_path = Path(f"eco_guardian/models/saved_models/unified_prophet_v4_{sigla}.pkl")
                    forecaster = UnifiedForecaster.load_model(model_path)

                    # Prepara condições iniciais (mantendo todas as variáveis originais)
                    condicoes = {
                        'Estado': estado_selecionado,
                        'bioma': ultimo_ano['bioma'],
                        'area_fazenda_ha': float(ultimo_ano['area_fazenda_ha']),
                        'area_floresta_ha': float(ultimo_ano['area_floresta_ha']),
                        'y': float(ultimo_ano['y']),
                        'prop_floresta': float(ultimo_ano['area_floresta_ha'] / 
                                    (ultimo_ano['area_fazenda_ha'] + ultimo_ano['area_floresta_ha'])),
                        'last_year': int(df_estado['ds'].dt.year.iloc[-1]),
                        'estado_code': int(forecaster.encoder_estados.transform([estado_selecionado])[0])
                    }

                    # Gera a previsão
                    with st.spinner("Gerando projeção..."):
                        forecast = forecaster.predict(condicoes, anos_projecao)
                        
                        # Armazena resultados na session state
                        st.session_state.ultima_projecao = {
                            'forecast': forecast,
                            'historical_data': df_estado,
                            'initial_conditions': condicoes
                        }

                    # Renderiza os resultados
                    ProjectionService.render_projection_results(
                        st.session_state.ultima_projecao,
                        anos_projecao
                    )

                except ValueError as e:
                    st.error(str(e))
                except FileNotFoundError:
                    st.error("Modelo de previsão não encontrado!")
                except Exception as e:
                    st.error(f"Erro inesperado: {str(e)}")
                    st.error("Consulte os logs para mais detalhes.")

if __name__ == "__main__":
    main()