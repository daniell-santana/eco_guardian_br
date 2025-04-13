# 🌍 EcoGuardian Brasil - Painel de Monitoramento Ambiental

[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)](https://eco-guardian-1008531514747.us-central1.run.app)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://hub.docker.com/r/daniellsantanaa/eco-guardian)
[![OpenAI](https://img.shields.io/badge/GPT-4o_Mini-412991?style=for-the-badge&logo=openai&logoColor=white)](https://openai.com/index/gpt-4o-mini-advancing-cost-efficient-intelligence/)

![Dashboard Preview](https://raw.githubusercontent.com/daniell-santana/eco_guardian_br/main/assets/dashboard_preview.png)

## 🚀 Acesso Online
**Aplicação Publicada:**  
https://eco-guardian-1008531514747.us-central1.run.app

## 🎯 Objetivos do Projeto
1. Monitoramento de desmatamento por bioma com séries históricas
2. Análise da relação entre avanço do PIB pecuário e desmatamento
3. Avaliação automatizada de políticas públicas ambientais
4. Projeções de conversão florestal para todos os estados brasileiros

**Diferencial estratégico:**  
Automatização completa do ciclo de análise de políticas ambientais com framework OCDE via [GPT-4o Mini](https://openai.com/index/gpt-4o-mini-advancing-cost-efficient-intelligence/).

---

## ✨ Destaques Técnicos
### 🔍 Automação no Processo de Análise e Avaliação da Política Pública:
- Classificação automática de políticas segundo critérios OCDE:
  - **Relevância**
  - **Efetividade** 
  - **Eficiência**
  - **Sustentabilidade**
  - **Coerência**
  - **Impacto**
- Detecção de 15+ tipos de dados quantitativos (metas, prazos, orçamentos)
- Geração de relatórios executivos com identificação do ente responsável

### 📊 Monitoramento por Bioma
- Evolução histórica do desmatamento em 6 biomas principais
- Correlação com indicadores econômicos setoriais
- Alertas de tendências críticas

### 📈 Modelagem Preditiva Avançada
- Previsão de conversão florestal para 5 anos
- Modelos Prophet customizados por estado
- Agregação municipal->estadual via média harmônica ponderada

### 📂 Fontes de Dados Oficiais
Categoria	Fontes Principais	Exemplo de Uso
- Políticas Ambientais:	Observatório Legal Amazonia, MMA	Análise de políticas estaduais
- Dados Territoriais:	IBGE Malhas	Mapas municipais e estaduais
- Séries Temporais:	PRODES/INPE	Modelagem preditiva

## 🗂 Estrutura do Projeto
```eco_guardian/
├── 📁 data/ # Dados ambientais e econômicos
│ ├── processed/ # Dados tratados (Parquet)
│ └── raw/ # Fontes originais (IBGE, PRODES, MapBiomas)
│
├── 📁 dashboard/ # Interface Streamlit
│ ├── components/ # Módulos visuais (mapas, gráficos, filtros)
│ └── main.py # Estrutura principal do dashboard
│
├── 📁 models/ # Lógica de análise
│ ├── llm_policy.py # Avaliação de políticas com GPT-4o Mini
│ ├── time_series_model.py # Modelos preditivos por estado
│ └── saved_models/ # Prophet treinados (1 por UF)
│
├── 📁 utils/ # Ferramentas auxiliares
│ └── data_loader.py # Carregamento otimizado de datasets
│
├── 📄 Dockerfile # Configuração de container
├── 📄 requirements.txt # Dependências Python
└── 📄 .env # Variáveis de ambiente (API keys)

**Principais Fluxos:**
1. `main.py` → Orquestra todos os módulos do dashboard
2. `data_loader.py` → Centraliza acesso aos dados processados
3. `llm_policy.py` → Processa PDFs de políticas ambientais
4. `time_series_model.py` → Gera projeções de desmatamento

> **Nota:** Todos os modelos preditivos estão pré-treinados e armazenados em `saved_models/` (um para cada estado brasileiro)
---

## 🛠 Arquitetura Principal
```python
# Stack de Inteligência Artificial
GPT-4o Mini          # Análise textual (120k tokens)
PDFPlumber           # Extração de textos
Prophet              # Séries temporais

# Geo Processamento
GeoPandas            # Manipulação de shapes
Folium/Plotly        # Visualização interativa

# Infraestrutura
Google Cloud Run     # Deploy
Docker Hub           # Imagem: daniellsantanaa/eco-guardian
