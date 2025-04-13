# 🌍 EcoGuardian Brasil - Painel de Monitoramento Ambiental

[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)](https://eco-guardian-1008531514747.us-central1.run.app)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://hub.docker.com/r/daniellsantanaa/eco-guardian)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT_4o-mini-412991?style=for-the-badge&logo=openai&logoColor=white)]([https://openai.com/](https://platform.openai.com/docs/models/gpt-4o-mini))

![Dashboard Preview](https://raw.githubusercontent.com/daniell-santana/eco_guardian_br/main/assets/dashboard_preview.png)

## 🚀 Acesso Online
**Aplicação Publicada:**  
https://eco-guardian-1008531514747.us-central1.run.app

## 🎯 Objeto do Projeto
Dashboard interativo para monitoramento ambiental no Brasil com:
- Análise geoespacial em tempo real
- **Modelos preditivos para taxa de conversão florestal (todos estados)**
- IA generativa para análise de políticas públicas
- Classificação automática de políticas segundo critérios OCDE

**Diferencial estratégico:** Sistema pioneiro de avaliação de políticas ambientais com framework OCDE via GPT-4o.

---

## ✨ Destaques Técnicos
### 🔍 Análise OCDE Automatizada
- Extração estruturada de 6 critérios-chave da OCDE
- Detecção de metas, prazos e indicadores quantitativos
- Geração de relatório executivo com identificação do ente responsável

### 📈 Modelagem Preditiva
- Previsão de conversão florestal para 5 anos
- Modelos Prophet customizados por estado
- Média harmônica ponderada para agregação municipal->estadual

### 🤖 Pipeline de IA
- Processamento de PDFs com PDFPlumber
- Context window de 120k tokens para documentos extensos
- Temperatura controlada (0.5) para análises balanceadas

---

## 📂 Fontes de Dados Principais
| Dado | Fonte | Resolução |
|------|-------|-----------|
| Séries Temporais Florestais | [PRODES/INPE](https://terrabrasilis.dpi.inpe.br/) | Municipal/Anual |
| Políticas Públicas | [MMA](https://www.gov.br/mma) | Leis/Decretos |
| Dados Econômicos | [SIDRA/IBGE](https://sidra.ibge.gov.br/) | Municipal |
| Limites Geográficos | [IBGE](https://www.ibge.gov.br/) | 2023 |

---

## 🛠 Arquitetura
```python
# Stack Principal
Python 3.10+
Streamlit       # Interface web
Docker          # Containerização
Prophet         # Modelagem temporal
OpenAI API      # GPT-4o para análise textual
GeoPandas       # Processamento geoespacial

# Infraestrutura
Google Cloud Run    # Deploy
Docker Hub          # Registry (daniellsantanaa/eco-guardian)
