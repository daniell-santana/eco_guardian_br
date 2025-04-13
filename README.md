# 🌍 EcoGuardian Brasil - Painel de Monitoramento Ambiental

[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)](https://eco-guardian-1008531514747.us-central1.run.app)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://hub.docker.com/r/daniellsantanaa/eco-guardian)
[![OpenAI GPT-4o Mini](https://img.shields.io/badge/OpenAI-GPT_4o_Mini-412991?style=for-the-badge&logo=openai&logoColor=white)](https://openai.com/index/gpt-4o-mini-advancing-cost-efficient-intelligence/)

![Dashboard Preview](https://raw.githubusercontent.com/daniell-santana/eco_guardian_br/main/assets/dashboard_preview.png)

## 🚀 Acesso Online
**Aplicação Publicada:**  
https://eco-guardian-1008531514747.us-central1.run.app

## 🎯 Objeto do Projeto
Plataforma integrada de análise ambiental com:
- Modelos preditivos de conversão florestal para **todos os estados brasileiros**
- Sistema de avaliação de políticas públicas via **framework OCDE**
- Integração com [GPT-4o Mini](https://openai.com/index/gpt-4o-mini-advancing-cost-efficient-intelligence/) para processamento de documentos

**Diferencial estratégico:**  
Automatização completa do ciclo de análise de políticas ambientais com extração estruturada de 6 critérios OCDE.

---

## ✨ Destaques Técnicos
### 🔍 Motor de Análise OCDE
- Classificação automática de políticas segundo critérios internacionais (Relevância, Efetividade, Eficiência, Sustentabilidade, Coerência e Impacto)
- Detecção de 15+ tipos de dados quantitativos (metas, prazos, orçamentos)
- Geração de relatórios executivos

### 📈 Modelagem Preditiva Avançada
- Previsão de conversão florestal para 5 anos
- Modelos Prophet customizados por estado
- Agregação municipal->estadual via média harmônica ponderada

### 🗺️ Base Geoespacial
- Dados territoriais do [IBGE Malhas](https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais/15774-malhas.html)
- Camadas dinâmicas de desmatamento (PRODES/INPE)
- Integração com dados do [Observatório Legal Amazonia](https://legal-amazonia.org/maranhao-politicas-ambientais-do-governo-carlos-brandao/)
- Dados de Biomas Brasil [MAPBIOMAS](https://brasil.mapbiomas.org/estatisticas/)
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
