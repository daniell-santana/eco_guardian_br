import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import streamlit as st
from eco_guardian.utils.data_loader import load_processed_data


def formatar_br(valor, decimais=0):
    """Formata números no padrão brasileiro diretamente nos dados"""
    try:
        valor = float(valor)
        return f"{valor:,.{decimais}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "N/A"

def display_agro_correlation(filters):
    try:
        # Dicionário completo de siglas para nomes dos estados
        SIGLA_UF_NOME = {
            'AC': 'Acre', 'AL': 'Alagoas', 'AP': 'Amapá', 'AM': 'Amazonas',
            'BA': 'Bahia', 'CE': 'Ceará', 'DF': 'Distrito Federal', 
            'ES': 'Espírito Santo', 'GO': 'Goiás', 'MA': 'Maranhão',
            'MT': 'Mato Grosso', 'MS': 'Mato Grosso do Sul', 'MG': 'Minas Gerais',
            'PA': 'Pará', 'PB': 'Paraíba', 'PR': 'Paraná', 'PE': 'Pernambuco',
            'PI': 'Piauí', 'RJ': 'Rio de Janeiro', 'RN': 'Rio Grande do Norte',
            'RS': 'Rio Grande do Sul', 'RO': 'Rondônia', 'RR': 'Roraima',
            'SC': 'Santa Catarina', 'SP': 'São Paulo', 'SE': 'Sergipe',
            'TO': 'Tocantins'
        }

        # Dicionário de códigos UF para siglas
        CODIGO_UF_SIGLA = {
            11: 'RO', 12: 'AC', 13: 'AM', 14: 'RR', 15: 'PA',
            16: 'AP', 17: 'TO', 21: 'MA', 22: 'PI', 23: 'CE',
            24: 'RN', 25: 'PB', 26: 'PE', 27: 'AL', 28: 'SE',
            29: 'BA', 31: 'MG', 32: 'ES', 33: 'RJ', 35: 'SP',
            41: 'PR', 42: 'SC', 43: 'RS', 50: 'MS', 51: 'MT',
            52: 'GO', 53: 'DF'
        }

        # Carrega os dados
        desmatamento = load_processed_data('desmatamento_bioma')
        ibge = load_processed_data('ibge_consolidado')

        # Filtra por período
        desmatamento = desmatamento[
            (desmatamento['ano'] >= filters['start_year']) & 
            (desmatamento['ano'] <= filters['end_year'])
        ]
        
        # 1. Extrai código UF do município (primeiros 2 dígitos)
        desmatamento['codigo_uf'] = desmatamento['cd_municipio'].astype(str).str[:2].astype(int)
        ibge['codigo_uf'] = ibge['cd_municipio'].astype(str).str[:2].astype(int)
        
        # 2. Converte para SIGLA_UF usando o dicionário
        desmatamento['SIGLA_UF'] = desmatamento['codigo_uf'].map(CODIGO_UF_SIGLA)
        ibge['SIGLA_UF'] = ibge['codigo_uf'].map(CODIGO_UF_SIGLA)
        
        # 3. Adiciona nome completo do estado
        desmatamento['Estado'] = desmatamento['SIGLA_UF'].map(SIGLA_UF_NOME)
        ibge['Estado'] = ibge['SIGLA_UF'].map(SIGLA_UF_NOME)
        
        # 4. Agrega PIB agropecuário por estado e ano (considerando 1 registro único por município/ano)
        # Primeiro agrupa por município e ano para evitar duplicatas de cultura
        pib_por_municipio = ibge.groupby(['codigo_uf', 'SIGLA_UF', 'Estado', 'cd_municipio', 'ano'])['pib_agropecuaria'].first().reset_index()
        
        # Agora agrupa por estado e ano
        pib_agro_estado = pib_por_municipio.groupby(['Estado', 'SIGLA_UF', 'ano'])['pib_agropecuaria'].sum().reset_index()
        
        # 5. Agrega desmatamento por estado e ano
        desmatamento_estado = desmatamento.groupby(['Estado', 'SIGLA_UF', 'ano'])['desmatado'].sum().reset_index()
        
        # 6. Merge dos dados agregados
        merged = pd.merge(
            desmatamento_estado,
            pib_agro_estado,
            on=['Estado', 'SIGLA_UF', 'ano'],
            how='inner'
        )
        
        # Widget de seleção de estados (usando nomes completos)
        estados_disponiveis = sorted(merged['Estado'].unique())
        estados_selecionados = st.multiselect(
            'Selecione os estados:',
            options=estados_disponiveis,
            default=estados_disponiveis[:1],  # Mostra 5 por padrão
            help="Escolha um ou mais estados para análise"
        )
        
        # Filtra por estados selecionados
        filtered_df = merged[merged['Estado'].isin(estados_selecionados)] if estados_selecionados else merged.copy()
        
        # Gráfico principal
        fig = px.line(
            filtered_df,
            x='pib_agropecuaria',
            y='desmatado',
            color='Estado',
            title=f"Relação PIB Agropecuário vs Desmatamento ({filters['start_year']}-{filters['end_year']})",
            labels={
                'pib_agropecuaria': 'PIB Agropecuário (R$)',
                'desmatado': 'Área Desmatada (km²)',
                'Estado': 'Estado'
            },
            hover_data=['ano'],
            markers=True,
            height=700
        )
        
        # Layout do gráfico
        fig.update_layout(
            hovermode='closest',
            xaxis_title='PIB Agropecuário (R$)',
            yaxis_title='Área Desmatada (km²)',
            xaxis_tickformat=",.0f"
        )
        
        # Adiciona os anos como texto fixo nos pontos da linha
        for estado in filtered_df['Estado'].unique():
            estado_df = filtered_df[filtered_df['Estado'] == estado]
            fig.add_trace(go.Scatter(
                x=estado_df['pib_agropecuaria'],
                y=estado_df['desmatado'],
                mode='text',
                text=estado_df['ano'].astype(str),
                textposition='top center',
                showlegend=False,
                hoverinfo='skip'  # Evita que isso interfira no tooltip
            ))

        # Cálculo do TOP 10 (Desmatamento/PIB)

        # 1. Validação do intervalo temporal
        if (filters['end_year'] - filters['start_year']) < 1:
            st.error("Selecione um intervalo com pelo menos 2 anos para cálculo de variação.")
            return

        # 2. Cálculo da variação (final - inicial)
        merged_sorted = merged.sort_values(['Estado', 'ano'])
        full_metric_df = merged_sorted.groupby(['Estado', 'SIGLA_UF']).agg({
            'desmatado': lambda x: x.iloc[-1] - x.iloc[0] if len(x) > 1 else 0,
            'pib_agropecuaria': lambda x: x.iloc[-1] - x.iloc[0] if len(x) > 1 else 0
        }).reset_index()

        # 3. Função de formatação BR
        def formatar_br(valor, decimais=0):
            return f"{float(valor):,.{decimais}f}".replace(",", "X").replace(".", ",").replace("X", ".")

        # 4. Cálculo do ratio com tratamento de divisão por zero
        full_metric_df['ratio'] = full_metric_df.apply(
            lambda row: row['desmatado'] / (row['pib_agropecuaria'] / 1_000_000) 
            if row['pib_agropecuaria'] != 0 else 0, 
            axis=1
        )

        # Exibição em colunas
        col1, col2 = st.columns([4, 2])
        with col1:
            st.plotly_chart(fig, use_container_width=True)
            
        with col2:
            # TOP 10 FIXO
            st.write("**Top 10 Estados (Desmatamento/PIB):**")
            if not full_metric_df.empty:
                # Filtra PIB positivo para ranking
                ranking_df = full_metric_df[full_metric_df['pib_agropecuaria'] > 0]
                top10_fixo = ranking_df.nlargest(10, 'ratio')
                
                for _, row in top10_fixo.iterrows():
                    ratio_value = row['ratio']
                    formatted_value = formatar_br(ratio_value, 2)
                    pib_var = formatar_br(row['pib_agropecuaria'])
                    
                    # Versão correta para ambos os casos
                    if estados_selecionados and row['Estado'] in estados_selecionados:
                        st.markdown(
                            f"- ✅ **{row['Estado']}:** {formatted_value} km²/milhão"
                            f"(ΔPIB: 💵 {pib_var})"
                        )
                    else:
                        st.markdown(
                            f"- {row['Estado']}: {formatted_value} km²/milhão "
                            f"(ΔPIB: 💵 {pib_var})"
                        )
            else:
                st.warning("Não há dados válidos para calcular o ranking.")
                
            # Cálculo da média
            metric_df = full_metric_df[full_metric_df['Estado'].isin(estados_selecionados)] if estados_selecionados else full_metric_df
            label = "Média dos Selecionados" if estados_selecionados else "Média Nacional"
            
            if not metric_df.empty:
                media_ratio = metric_df['ratio'].mean()
                media_formatada = formatar_br(media_ratio, 2)
                media_text = f"**{label}:** {media_formatada} km²/milhão R$"
            else:
                media_text = f"**{label}:** Indisponível"
            
            # Seção de interpretação
            st.caption(f"""
            {media_text}

            <div style='font-size:12px; font-weight:bold; margin-bottom:4px;'>INTERPRETAÇÃO</div>  <!-- Margem inferior reduzida -->
            <div style='font-size:12px; margin:0; padding:0;'>  <!-- Remove margens e paddings padrão -->
            O valor indica a relação entre a <b>variação total do desmatamento</b> e a <b>variação do PIB agropecuário</b> no período analisado:<br>

            { 
                f"<div style='margin:2px 0;'><b>Relação Positiva (+):</b> Aumento do PIB agropecuário acompanhado de crescimento do desmatamento</div>" 
                f"<div style='margin:2px 0;'><b>Relação Negativa (-):</b> Queda no PIB agropecuário ocorreu junto com <b>aumento</b> do desmatamento</div>" 
                if 'media_formatada' in locals() else ""
            }

            <div style='margin:4px 0;'>  <!-- Margem personalizada -->
            { 
                f"Exemplo: {media_formatada} km²/milhão " + 
                (
                    "significa que para cada <b>aumento</b> de 1.000.000 de reais no PIB agropecuário, " 
                    f"houve desmatamento de {media_formatada} km²"
                    if media_ratio > 0 else
                    "indica que para cada <b>queda</b> de 1.000.000 de reais no PIB agropecuário, " 
                    f"houve <b>aumento</b> de {abs(media_ratio):.2f} km² no desmatamento"
                ) 
                if 'media_formatada' in locals() else 
                "Exemplo: X,XX km²/milhão"
            }
            </div>

            <div style='margin-top:4px;'>  <!-- Margem superior reduzida -->
            ❗ <b>Contexto importante:</b><br>
            - Dados de desmatamento são <b>acumulativos</b> em relação ao ano base (2014).<br>
            - Variações negativas no PIB agropecuário podem refletir quedas pontuais ou baixo crescimento.<br>
            - Valores negativos <b>não indicam regeneração florestal</b>.
            </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Botão de metodologia
            if st.button("🔍 Métodologia", key=f"method_btn_{filters['start_year']}_{filters['end_year']}"):
                st.info("""
                **Cálculo da Relação Desmatamento/PIB:**
                
                A métrica é calculada através da fórmula:
                ```
                (Desmatamento Total no Período) / (Variação do PIB Agropecuário no Período ÷ 1.000.000)
                ```
                
                - **Desmatamento Total:** Soma da área desmatada (km²) entre {start} e {end}
                - **Variação do PIB:** Diferença entre o valor final e inicial do PIB agropecuário (R$)
                - **Divisão por 1 milhão:** Para normalizar a relação para cada milhão de reais
                
                **Nota sobre os dados:**
                - Dados do PIB agropecuário disponíveis até 2021 (fonte: IBGE)
                - Valores monetários em Reais correntes
                - Dados de desmatamento consolidados até 2023
                """.format(start=filters['start_year'], end=filters['end_year']))
            

    except Exception as e:
        st.error(f"Erro na análise: {str(e)}")
        with st.expander("Detalhes do erro"):
            st.write("Dados de desmatamento:", desmatamento.head() if 'desmatamento' in locals() else "Não disponível")
            st.write("Dados do IBGE:", ibge.head() if 'ibge' in locals() else "Não disponível")

def display_economic_impact_map(filters):
    """Exibe mapa de impacto econômico-ambiental por estado"""
    with st.container():
        
        try:
            # 1. Carrega todas as bases necessárias
            desmatamento = load_processed_data('desmatamento_bioma')
            ibge = load_processed_data('ibge_consolidado')
            estados_geo = load_processed_data('br_estados')
            
            # 2. Filtra por período
            desmatamento = desmatamento[
                (desmatamento['ano'] >= filters['start_year']) & 
                (desmatamento['ano'] <= filters['end_year'])
            ]
            ibge = ibge[
                (ibge['ano'] >= filters['start_year']) & 
                (ibge['ano'] <= filters['end_year'])
            ]
            
            # 3. Processamento dos dados
            # Extrai código UF e converte para sigla
            desmatamento['codigo_uf'] = desmatamento['cd_municipio'].astype(str).str[:2].astype(int)
            ibge['codigo_uf'] = ibge['cd_municipio'].astype(str).str[:2].astype(int)
            
            CODIGO_UF_SIGLA = {
                11: 'RO', 12: 'AC', 13: 'AM', 14: 'RR', 15: 'PA',
                16: 'AP', 17: 'TO', 21: 'MA', 22: 'PI', 23: 'CE',
                24: 'RN', 25: 'PB', 26: 'PE', 27: 'AL', 28: 'SE',
                29: 'BA', 31: 'MG', 32: 'ES', 33: 'RJ', 35: 'SP',
                41: 'PR', 42: 'SC', 43: 'RS', 50: 'MS', 51: 'MT',
                52: 'GO', 53: 'DF'
            }
            
            desmatamento['SIGLA_UF'] = desmatamento['codigo_uf'].map(CODIGO_UF_SIGLA)
            ibge['SIGLA_UF'] = ibge['codigo_uf'].map(CODIGO_UF_SIGLA)
            
            # 4. Cálculo da VARIAÇÃO (último ano - primeiro ano) por estado
            # Para desmatamento
            desmatamento_var = desmatamento.groupby(['SIGLA_UF', 'ano'])['desmatado'].sum().groupby('SIGLA_UF').agg(
                lambda x: x.iloc[-1] - x.iloc[0] if len(x) > 1 else 0
            ).reset_index(name='desmatamento_total')

            # Para PIB (agrupar por município primeiro para evitar duplicatas)
            pib_por_municipio = ibge.groupby(['SIGLA_UF', 'cd_municipio', 'ano'])['pib_agropecuaria'].first().reset_index()
            pib_var = pib_por_municipio.groupby(['SIGLA_UF', 'ano'])['pib_agropecuaria'].sum().groupby('SIGLA_UF').agg(
                lambda x: x.iloc[-1] - x.iloc[0] if len(x) > 1 else 0
            ).reset_index(name='variacao_pib')

            # 5. Merge e cálculo da relação
            estado_stats = pd.merge(
                desmatamento_var,
                pib_var,
                on='SIGLA_UF',
                how='inner'
            )
            estado_stats['ratio'] = estado_stats['desmatamento_total'] / (estado_stats['variacao_pib'] / 1_000_000)

            # 6. Merge com shapes
            final_df = estados_geo.merge(
                estado_stats,
                on='SIGLA_UF',
                how='left'
            ).dropna(subset=['ratio'])
            
            # Layout com duas colunas
            col1, col2 = st.columns([2, 2])
            
            with col1:
                # Pré-formata os dados antes de criar o gráfico
                final_df['desmatamento_formatado'] = final_df['desmatamento_total'].apply(lambda x: formatar_br(x, 2))
                final_df['pib_formatado'] = final_df['variacao_pib'].apply(lambda x: formatar_br(x, 2))
                final_df['ratio_formatado'] = final_df['ratio'].apply(lambda x: formatar_br(x, 4))

                # Adiciona coluna com período selecionado (ex: "2010-2023")
                final_df['periodo'] = f"{filters['start_year']}-{filters['end_year']}"

                # Calcula os extremos simétricos baseados na magnitude
                ratio_min = final_df['ratio'].min()
                ratio_max = final_df['ratio'].max()
                max_abs = max(abs(ratio_min), abs(ratio_max))  # Maior valor absoluto (negativo ou positivo)
                cmin = -max_abs  # Força simetria negativa
                cmax = max_abs   # Força simetria positiva

                # Escala de cores divergente (azul -> branco -> vermelho)
                color_scale = [
                    [0.0, "darkblue"],    # Valor mínimo (mais negativo)
                    [0.45, "lightblue"],   # Transição para negativo próximo de zero
                    [0.5, "white"],        # Zero (branco)
                    [0.55, "lightcoral"],  # Transição para positivo próximo de zero
                    [1.0, "darkred"]       # Valor máximo (mais positivo)
                ]

                # Mapa coroplético com escala personalizada
                fig_map = px.choropleth_mapbox(
                    final_df,
                    geojson=final_df.geometry,
                    locations=final_df.index,
                    color='ratio',
                    hover_name='SIGLA_UF',
                    hover_data={
                        'periodo': True,
                        'desmatamento_formatado': True,
                        'pib_formatado': True,
                        'ratio_formatado': True,
                        'SIGLA_UF': False
                    },
                    color_continuous_scale=color_scale,  # Escala personalizada
                    range_color=(cmin, cmax),  # Limites simétricos
                    mapbox_style="carto-darkmatter",
                    zoom=3,
                    center={"lat": -14, "lon": -55},
                    opacity=0.7
                )
                            
                # Tooltip corrigido
                fig_map.update_traces(
                    hovertemplate=(
                        "<b>%{hovertext}</b><br>"  # sempre usar hovertext
                        "Período: %{customdata[0]}<br>"  # Campo período
                        "Variação Desmatamento: %{customdata[1]} km²<br>"  # Desmatamento
                        "Variação PIB Agro: R$ %{customdata[2]}<br>"  # PIB
                        "Relação: %{customdata[3]} km²/milhão R$"  # Ratio
                    )
                )
                
                # Configuração crítica da escala
                fig_map.update_layout(
                    title={
                        'text': f"Distribuição da Relação entre Desmatamento e PIB Agro no Período {filters['start_year']}-{filters['end_year']}",
                        'x':0.5,  # Centraliza o título
                        'xanchor': 'center'
                    },
                    height=600,
                    margin={"r":0, "t":30, "l":0, "b":0},
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    coloraxis=dict(
                        cmin=cmin,
                        cmax=cmax,
                        cmid=0,
                        colorbar=dict(
                            title='km²/milhão R$',
                            thickness=10
                        )
                    ),
                    mapbox=dict(
                        style='carto-darkmatter',
                        layers=[]
                    )
                )

                st.plotly_chart(fig_map, use_container_width=True)
            
            with col2:
                try:
                    # Filtra os dados pelo período selecionado
                    ibge_filtrado = ibge[
                        (ibge['ano'] >= filters['start_year']) & 
                        (ibge['ano'] <= filters['end_year'])
                    ]

                    # Processamento dos dados - remove None, "Total" e "Outros"
                    area_plantada = ibge_filtrado[
                        (ibge_filtrado['cultura'].notna()) & 
                        (~ibge_filtrado['cultura'].isin(['Total', 'Outros'])) & 
                        (ibge_filtrado['area_plantada'].notna())
                    ][['SIGLA_UF', 'cultura', 'area_plantada']].copy()
                    
                    # Converte para km² e agrega
                    area_plantada['area_km2'] = area_plantada['area_plantada'] / 100
                    area_grouped = area_plantada.groupby(['SIGLA_UF', 'cultura'])['area_km2'].sum().reset_index()
                    
                    # Ordenação para tooltip (maior para menor área)
                    area_grouped = area_grouped.sort_values(['SIGLA_UF', 'area_km2'], ascending=[True, False])
                    
                    # Formatação para tooltip
                    area_grouped['area_formatada'] = area_grouped['area_km2'].apply(lambda x: formatar_br(x, 0))
                    
                    # Ordenação de estados por área total
                    ordem_estados = area_grouped.groupby('SIGLA_UF')['area_km2'].sum()\
                                            .sort_values(ascending=False).index.tolist()

                    # Gráfico com dimensões ajustadas
                    fig_bar = px.bar(
                        area_grouped,
                        x='SIGLA_UF',
                        y='area_km2',
                        color='cultura',
                        custom_data=['area_formatada'],
                        category_orders={
                            'SIGLA_UF': ordem_estados,
                            'cultura': area_grouped.groupby('cultura')['area_km2'].sum()
                                                .sort_values(ascending=False).index.tolist()
                        },
                        labels={'area_km2': 'Área (km²)', 'SIGLA_UF': 'Estado'},
                        height=600,
                        width=600
                    )

                    # Tooltip compacto e ordenado
                    fig_bar.update_traces(
                        hovertemplate=(
                            'Área: %{customdata[0]} km²'
                        ),
                        hoverlabel=dict(
                            bgcolor='white',
                            font_size=11,
                            namelength=-1,
                            align='left'
                        )
                    )

                    # Layout otimizado
                    fig_bar.update_layout(
                        barmode='stack',
                        xaxis={'categoryorder':'array', 'categoryarray': ordem_estados},
                        legend=dict(
                            title=None,
                            orientation="h",
                            yanchor="bottom",
                            y=-0.3,
                            x=0.5,
                            xanchor="center",
                            font=dict(size=10)
                        ),
                        margin=dict(t=60, b=100, l=50, r=50),
                        hovermode='x unified',
                        hoverdistance=100,
                        title={
                            'text': f"Área Plantada Acumulada por Cultura entre: ({filters['start_year']}-{filters['end_year']})",
                            'x': 0.5,
                            'xanchor': 'center'
                        }
                    )

                    # Container com scroll se necessário
                    st.plotly_chart(fig_bar, use_container_width=True)

                except Exception as e:
                    st.error(f"Erro ao gerar gráfico: {str(e)}")
                
        except Exception as e:
            st.error(f"Erro ao gerar visualizações: {str(e)}")
            with st.expander("Detalhes do erro"):
                st.write("Dados de desmatamento:", desmatamento.head() if 'desmatamento' in locals() else "Não disponível")
                st.write("Dados do IBGE:", ibge.head() if 'ibge' in locals() else "Não disponível")
                st.write("Dados geoespaciais:", estados_geo.head() if 'estados_geo' in locals() else "Não disponível")