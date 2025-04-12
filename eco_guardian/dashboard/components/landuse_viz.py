# dashboard/components/landuse_viz.py
import plotly.express as px
import pandas as pd
import numpy as np
import streamlit as st
from eco_guardian.utils.data_loader import load_processed_data

def show_landuse_analysis(filters):
    """Exibe análise de transição floresta-fazenda com visualização hierárquica"""
    df = load_processed_data("landuse_processed")
    
    # Converte ano para int se necessário
    if pd.api.types.is_datetime64_any_dtype(df['ano']):
        df['ano'] = df['ano'].dt.year
    
    # Aplica filtros hierárquicos
    query_parts = []
    if filters.get('biomas'):
        query_parts.append(f"bioma in {filters['biomas']}")
    if filters.get('estados'):
        query_parts.append(f"Estado in {filters['estados']}")
    if filters.get('municipios'):
        query_parts.append(f"dc_municipio in {filters['municipios']}")
    
    filtered = df.query(" & ".join(query_parts)) if query_parts else df
    
    if filtered.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados")
        return
    
    # Container com duas colunas de igual largura (50% cada)
    col1, col2 = st.columns(2)
    
    with col1:
        # Gráfico de transição (acumulado)
        viz_data = filtered.groupby(['ano'])[['area_floresta_ha', 'area_fazenda_ha']].sum().reset_index()
        viz_data = viz_data.melt(id_vars='ano', var_name='Tipo', value_name='Área (ha)')

        # Filtra por período
        viz_data = viz_data[
            (viz_data['ano'] >= int(filters['ano_inicio'])) &
            (viz_data['ano'] <= int(filters['ano_fim']))
        ]

        fig = px.area(
            viz_data,
            x='ano',
            y='Área (ha)',
            color='Tipo',
            title="Transição Floresta-Fazenda (Área Total)",
            labels={'Área (ha)': 'Área (hectares)', 'Tipo': 'Tipo de Cobertura'}
        )

        # Renomear as legendas
        new_legend_names = {'area_floresta_ha': 'Floresta', 'area_fazenda_ha': 'Fazenda'}
        for trace in fig.data:
            if trace.name in new_legend_names:
                trace.name = new_legend_names[trace.name]

        # Mover a legenda para abaixo do eixo y (canto inferior esquerdo)
        fig.update_layout(
            legend=dict(
                orientation="h",  # Legenda vertical para ficar abaixo do eixo y
                yanchor="top",    # Ancorar a parte superior da legenda
                y=-0.2,           # Ajustar a posição vertical (negativo para baixo)
                xanchor="left",   # Ancorar a parte esquerda da legenda
                x=0.01            # Ajustar a posição horizontal
            ),
            legend_title_text='Tipo de Cobertura' # Define o título da legenda
        )

        st.plotly_chart(fig, use_container_width=True, key="chart_area")
    
    with col2:
        # Gráfico de taxa de conversão por bioma
        if not filtered.empty:
            # Certifica-se de que a coluna 'area_floresta_ha' exista no DataFrame
            if 'area_floresta_ha' not in filtered.columns:
                st.error("A coluna 'area_floresta_ha' não foi encontrada nos dados filtrados.")
            else:
                # Calcula a média ponderada por ano e bioma utilizando apenas a área de floresta
                conversao = filtered.groupby(['ano', 'bioma']).apply(
                    lambda x: np.average(x['taxa_conversao_anual'], weights=x['area_floresta_ha'])
                ).reset_index(name='taxa_conversao_anual')
                
                # Filtra por período conforme definido pelos filtros
                conversao = conversao[
                    (conversao['ano'] >= int(filters['ano_inicio'])) & 
                    (conversao['ano'] <= int(filters['ano_fim']))
                ]
                
                if not conversao.empty:
                    # Dicionário de cores padrão para cada bioma
                    cores_biomas = {
                        'Amazônia': '#1f77b4',
                        'Cerrado': '#ff7f0e',
                        'Caatinga': '#2ca02c',
                        'Mata Atlântica': '#d62728',
                        'Pampa': '#9467bd',
                        'Pantanal': '#8c564b'
                    }

                    # Define os limites do eixo Y com base nos dados calculados
                    y_min = conversao['taxa_conversao_anual'].min()
                    y_max = conversao['taxa_conversao_anual'].max()
                    #y_padding = max(0.05, (y_max - y_min) * 0.1)  # 10% de padding ou 0.1 mínimo

                    # Criação do gráfico de linha usando Plotly Express
                    fig = px.line(
                        conversao,
                        x='ano',
                        y='taxa_conversao_anual',
                        color='bioma',
                        color_discrete_map=cores_biomas,
                        title="Evolução Anual da Cobertura Florestal: Perda ou Recuperação por Bioma",
                        markers=True,
                        labels={
                            'taxa_conversao_anual': 'Taxa de Conversão',
                            'ano': 'Ano',
                            'bioma': 'Bioma'
                        }
                    )
                    
                    # Ajuste de estilo do gráfico
                    fig.update_traces(
                        line=dict(width=2),
                        marker=dict(size=8)
                    )
                    
                    fig.update_layout(
                        yaxis_title="Taxa de Evolução (%)",
                        xaxis_title="Ano",
                        margin=dict(l=20, r=20, t=40, b=20),
                        yaxis=dict(
                            tickformat=".1%",  # Formata os ticks como porcentagem com 1 decimal
                            showgrid=True,
                            zeroline=True,
                            zerolinecolor='black'
                        ),
                        legend=dict(
                            title_text='Biomas',
                            orientation="h",
                            yanchor="bottom",
                            y=-0.5,
                            xanchor="center",
                            x=0.5
                        )
                    )
                    
                    # Adiciona uma linha horizontal no zero para referência
                    fig.add_hline(
                        y=0, 
                        line_dash="dot",
                        line_color="#d94322",
                        annotation_text="Linha de Equilíbrio",
                        annotation_position="bottom right"
                    )
                    
                    st.plotly_chart(fig, use_container_width=True, key="chart_linha")
                else:
                    st.warning("Nenhum dado disponível para o período selecionado")