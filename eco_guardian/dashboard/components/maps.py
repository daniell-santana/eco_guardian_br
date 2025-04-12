# dashboard/components/maps.py
import streamlit as st
from streamlit_folium import folium_static
import folium
from branca.colormap import LinearColormap
import pandas as pd
import plotly.express as px
import geopandas as gpd
from eco_guardian.utils.data_loader import load_processed_data

def format_br_number(value, decimals=2):
    """Formata números no padrão brasileiro"""
    try:
        num = float(value)
        return f"{num:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return str(value)

def render_br_map_folium(year: int, selected_biomas: list = None, 
                        selected_estados: list = None, selected_municipios: list = None,
                        prodes_data: pd.DataFrame = None, municipios_data: gpd.GeoDataFrame = None) -> folium.Map:
       
    try:        
        # Carrega dados se não forem fornecidos
        if prodes_data is None:
            prodes_data = load_processed_data('prodes')
            if 'bioma' not in prodes_data.columns:
                prodes_data['bioma'] = 'Não informado'
        
        if municipios_data is None:
            municipios_data = load_processed_data('br_municipios')
        
        # Filtra por ano se especificado
        if year:
            desmatamento = prodes_data[prodes_data['ano'] == year]
        else:
            desmatamento = prodes_data
            
        # Agrega mantendo o ano mais recente para tooltip
        desmatamento_agg = desmatamento.groupby('cd_municipio').agg({
            'desmatado': 'sum',
            'vegetacao_natural': 'mean',
            'nao_vegetacao_natural': 'mean',
            'bioma': 'first',
            'ano': 'max'
        }).reset_index()

        # Merge garantindo todas as colunas necessárias
        merged = municipios_data.merge(
            desmatamento_agg,
            on='cd_municipio',
            how='left',
            suffixes=('_municipio', '')  # Mantém 'bioma' do desmatamento_agg
        )
        
        # Remove colunas duplicadas e mantém apenas a coluna 'bioma' do desmatamento
        if 'bioma_municipio' in merged.columns:
            merged = merged.drop(columns=['bioma_municipio'])
        
        # Preenche valores nulos
        merged = merged.fillna({
            'desmatado': 0,
            'vegetacao_natural': 0,
            'nao_vegetacao_natural': 0,
            'bioma': 'Não informado',
            'ano': year if year else 'N/A'
        })

        # Formata os valores numéricos para padrão brasileiro
        merged['vegetacao_natural_fmt'] = merged['vegetacao_natural'].apply(format_br_number)
        merged['nao_vegetacao_natural_fmt'] = merged['nao_vegetacao_natural'].apply(format_br_number)
        merged['desmatado_fmt'] = merged['desmatado'].apply(format_br_number)

        # Configuração do mapa Folium
        m = folium.Map(
            location=[-14.2350, -51.9253],
            zoom_start=5,
            control_scale=True,
            prefer_canvas=True
        )
        # Adiciona camada base com nome personalizado
        folium.TileLayer(
            tiles='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
            name='Camadas do mapa',  # Nome personalizado
            attr='OpenStreetMap',
            overlay=False  # Define como camada base
        ).add_to(m)
        
        # Escala de cores
        max_val = merged['desmatado'].max()
        colormap = LinearColormap(
            ['#ffffff', '#ffcccc', '#ff9999', '#ff6666', '#ff3541', '#b30000', '#800000', '#4d0000', '#260000'],
            index=[0, 2500, 5000, 7500, 10000, 12500, 15000, 17500, max_val],
            vmin=0,
            vmax=max_val,
            caption='Área Desmatada (km²)'
        )

        # Adiciona camada principal com estilo personalizado
        folium.GeoJson(
            merged,
            name='Municípios Brasil',
            style_function=lambda x: {
                'fillColor': colormap(x['properties']['desmatado']),
                'color': '#555555',
                'weight': 0.5,
                'fillOpacity': 0.5
            },
            tooltip=folium.GeoJsonTooltip(
                fields=['NM_MUN', 'NM_UF', 'vegetacao_natural_fmt', 
                       'nao_vegetacao_natural_fmt', 'ano', 'bioma', 'desmatado_fmt'],
                aliases=[
                    'Município:', 'Estado:', 
                    'Vegetação Nativa (km²):', 'Não Vegetação Nativa (km²):',
                    'Ano de Referência:', 'Bioma:', 'Área Desmatada (km²):'
                ],
                style=("""
                    background-color: white; 
                    color: #333333; 
                    font-family: Arial; 
                    padding: 8px; 
                    border-radius: 4px;
                    box-shadow: 3px 3px 5px rgba(0,0,0,0.2);
                """),
                sticky=True
            )
        ).add_to(m)

        # Cria grupos de camadas para os realces
        biomas_group = folium.FeatureGroup(name='Biomas Selecionados', show=True)
        estados_group = folium.FeatureGroup(name='Estados Selecionados', show=True)
        municipios_group = folium.FeatureGroup(name='Municípios Selecionados', show=True)

        # Adiciona realce para biomas selecionados
        # Realce para biomas selecionados
        if selected_biomas:
            biomas_highlight = merged[merged['bioma'].isin(selected_biomas)]
            if not biomas_highlight.empty:  # Verifica se há dados
                folium.GeoJson(
                    biomas_highlight,
                    style_function=lambda x: {
                        'color': '#000000',
                        'weight': 2,
                        'fillOpacity': 0,
                        'dashArray': '5, 5'
                    },
                    tooltip=folium.GeoJsonTooltip(
                    fields=['NM_MUN', 'NM_UF', 'vegetacao_natural_fmt', 
                       'nao_vegetacao_natural_fmt', 'ano', 'bioma', 'desmatado_fmt'],
                    aliases=[
                        'Município:', 'Estado:', 
                        'Vegetação Nativa (km²):', 'Não Vegetação Nativa (km²):',
                        'Ano de Referência:', 'Bioma:', 'Área Desmatada (km²):'
                    ],
                    style=("""
                        background-color: white; 
                        color: #333333; 
                        font-family: Arial; 
                        padding: 8px; 
                        border-radius: 4px;
                        box-shadow: 3px 3px 5px rgba(0,0,0,0.2);
                    """),
                    sticky=True
                )
            ).add_to(biomas_group)

        # Realce para estados selecionados
        if selected_estados:
            estados_highlight = merged[merged['NM_UF'].isin(selected_estados)]
            folium.GeoJson(
                estados_highlight,
                style_function=lambda x: {
                    'color': '#00a84f',
                    'weight': 2,
                    'fillOpacity': 0
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=['NM_MUN', 'NM_UF', 'vegetacao_natural_fmt', 
                       'nao_vegetacao_natural_fmt', 'ano', 'bioma', 'desmatado_fmt'],
                    aliases=[
                        'Município:', 'Estado:', 
                        'Vegetação Nativa (km²):', 'Não Vegetação Nativa (km²):',
                        'Ano de Referência:', 'Bioma:', 'Área Desmatada (km²):'
                    ],
                    style=("""
                        background-color: white; 
                        color: #333333; 
                        font-family: Arial; 
                        padding: 8px; 
                        border-radius: 4px;
                        box-shadow: 3px 3px 5px rgba(0,0,0,0.2);
                    """),
                    sticky=True
                )
            ).add_to(estados_group)

        # Realce para municípios selecionados
        if selected_municipios:
            municipios_highlight = merged[merged['NM_MUN'].isin(selected_municipios)]
            folium.GeoJson(
                municipios_highlight,
                style_function=lambda x: {
                    'color': '#0066ff',
                    'weight': 3,
                    'fillOpacity': 0
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=['NM_MUN', 'NM_UF', 'vegetacao_natural_fmt', 
                       'nao_vegetacao_natural_fmt', 'ano', 'bioma', 'desmatado_fmt'],
                    aliases=[
                        'Município:', 'Estado:', 
                        'Vegetação Nativa (km²):', 'Não Vegetação Nativa (km²):',
                        'Ano de Referência:', 'Bioma:', 'Área Desmatada (km²):'
                    ],
                    style=("""
                        background-color: white; 
                        color: #333333; 
                        font-family: Arial; 
                        padding: 8px; 
                        border-radius: 4px;
                        box-shadow: 3px 3px 5px rgba(0,0,0,0.2);
                    """),
                    sticky=True
                )
            ).add_to(municipios_group)
        
        # Adiciona os grupos ao mapa
        biomas_group.add_to(m)
        estados_group.add_to(m)
        municipios_group.add_to(m)
        # Adiciona escala
        colormap.step = 2000
        colormap.add_to(m)

        # Adiciona controle de camadas
        folium.LayerControl().add_to(m)

        return m

    except Exception as e:
        st.error(f"Erro ao renderizar mapa: {str(e)}")
        return None

def render_evolution_map(municipio_cod: int):
    """
    Renderiza mapa de evolução temporal para um município específico.

    Args:
        municipio_cod: Código IBGE do município (7 dígitos)
    """
    try:
        # Carrega dados históricos
        cols = ['cd_municipio', 'ano', 'desmatado', 'vegetacao_natural']
        desmatamento = load_processed_data('prodes')[cols]
        municipio_data = desmatamento[desmatamento['cd_municipio'] == municipio_cod]

        if municipio_data.empty:
            st.warning(f"Nenhum dado encontrado para o município {municipio_cod}")
            return None
            
        # Formata os valores para padrão brasileiro
        municipio_data['desmatado_fmt'] = municipio_data['desmatado'].apply(format_br_number)
        municipio_data['vegetacao_natural_fmt'] = municipio_data['vegetacao_natural'].apply(format_br_number)
            
        # Cria gráfico de evolução temporal
        fig = px.line(
            municipio_data,
            x='ano',
            y=['desmatado', 'vegetacao_natural'],
            title=f"Evolução do Desmatamento - Código: {municipio_cod}",
            labels={'value': 'Área (km²)', 'ano': 'Ano'},
            markers=True,
            hover_data={
                'desmatado': ':.2f',
                'vegetacao_natural': ':.2f',
                'ano': True
            }
        )
        fig.update_layout(
            hovermode='x unified',
            legend_title='Tipo de Área',
            yaxis_tickformat=',.2f'
        )
        fig.update_traces(
            hovertemplate="<br>".join([
                "Ano: %{x}",
                "Área: %{y:,.2f} km²"
            ])
        )
        return fig
        
    except Exception as e:
        st.error(f"Erro no mapa de evolução: {str(e)}")
        return None

def handle_map_interaction(selected_feature: dict):
    """
    Processa interações do usuário com o mapa.

    Args:
        selected_feature: Dados do elemento selecionado no mapa
    """
    if selected_feature:
        props = selected_feature.get('properties', {})
        info = {
            'municipio': props.get('NM_MUN'),
            'estado': props.get('NM_UF'),
            'codigo': props.get('cd_municipio'),
            'desmatado': format_br_number(props.get('desmatado', 0))
        }
        st.session_state['selected_municipio'] = info
        st.success(f"Município selecionado: {info['municipio']} - {info['estado']}")
def render_stacked_area_bioma():
    """Renderiza gráfico de 100% empilhado por bioma com tooltip unificado"""
    try:
        desmatamento = load_processed_data('prodes')
        
        # Processamento dos dados
        df = desmatamento.groupby(['ano', 'bioma'])['desmatado'].sum().reset_index()
        # Calcula a ordem decrescente baseada no total histórico
        biomas_ordenados = df.groupby('bioma')['desmatado'].sum().sort_values(ascending=False).index.tolist()
        
        # Inverte a ordem para empilhamento (maior no topo)
        ordem_empilhamento = biomas_ordenados[::-1]  # Inverte a lista

        # Calcula porcentagem
        df['porcentagem'] = df.groupby('ano')['desmatado'].transform(lambda x: x/x.sum()*100)
        
        # Cores dos biomas
        cores_biomas = {
            'Amazônia': '#009445',
            'Cerrado': '#f6e8c3',     
            'Mata Atlântica': '#3c5785',
            'Caatinga': '#d8b365',
            'Pampa': '#d87914',
            'Pantanal': '#5ab4ac'
        }
        
        # Criação do gráfico
        fig = px.area(
            df,
            x='ano',
            y='porcentagem',
            color='bioma',
            color_discrete_map=cores_biomas,
            category_orders={'bioma': biomas_ordenados},  # Ordem decrescente
            title="Distribuição Percentual de área(km²) desmatada por Bioma",
            labels={'ano': 'Ano', 'porcentagem': '%Desmatamento Total'},
        )
         # Ajusta a ordem de empilhamento (maior no topo)
        for i, trace in enumerate(fig.data):
            trace.stackgroup = 'one'
            trace.legendgroup = 'one'
            trace.offsetgroup = 'one'
        
        # Ordena as traças para empilhar do maior (topo) para menor (base)
        fig.data = sorted(fig.data, key=lambda x: df[df['bioma']==x.name]['porcentagem'].mean())
        
        # Configuração do tooltip unificado
        fig.update_layout(
            hovermode="x unified",
            hoverlabel=dict(
                bgcolor="#0e1118",
                font_size=12,
                font_color="white",
                bordercolor="#444"
            )
        )
        
        # Formatação do texto no tooltip
        fig.update_traces(
            hovertemplate="%{y:.2f}%",
            hoverinfo="x+y+name"
        )
        
        return fig
        
    except Exception as e:
        st.error(f"Erro ao gerar gráfico de biomas: {str(e)}")
        return None