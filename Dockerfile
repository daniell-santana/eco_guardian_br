# Imagem base otimizada para geoespacial
FROM python:3.9-slim AS builder

# Variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PROJ_LIB=/usr/local/share/proj

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    proj-data \
    proj-bin \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Configurar diretório de trabalho
WORKDIR /app

# Copiar tudo para o container (exceto o que está no .dockerignore)
COPY . .

# Instalar dependências Python
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install pyproj==3.6.1

# Expor porta do Streamlit
EXPOSE 8501

# Comando de inicialização
CMD ["streamlit", "run", "eco_guardian/dashboard/main.py", "--server.port=8501", "--server.address=0.0.0.0"]

