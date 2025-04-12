import argparse
from pathlib import Path
import logging
import sys
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
from eco_guardian.utils.data_loader import load_processed_data
from eco_guardian.models.time_series_model import UnifiedForecaster

# Configuração de logging (mantida)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('training.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def _validate_input_data(df: pd.DataFrame) -> None:
    """Valida colunas e valores CRÍTICOS antes do pré-processamento principal"""
    required_columns = {
        'ds': 'Data',  # Alterado de 'ano' para 'ds'
        'y': 'Taxa de conversão',
        'Estado': 'Estado',
        'bioma': 'Bioma',
        'area_fazenda_ha': 'Área de fazenda (ha)',
        'area_floresta_ha': 'Área de floresta (ha)'
    }
    
    missing = [k for k in required_columns if k not in df.columns]
    if missing:
        raise ValueError(f"Colunas obrigatórias faltando: {missing}")

    # Validações numéricas e de datas (ajustadas para os nomes ORIGINAIS)
    area_cols = ['area_floresta_ha', 'area_fazenda_ha']
    if df[area_cols].isnull().any().any():
        raise ValueError("Valores NaN encontrados nas áreas")
    
    if (df[area_cols] < 0).any().any():
        raise ValueError("Valores negativos nas áreas")

    try:
        pd.to_datetime(df['ds'], format='%Y')  # Alterado de 'ano' para 'ds'
    except ValueError as e:
        raise ValueError(f"Formato de data inválido: {str(e)}")

def parse_args():
    """Configura os argumentos de CLI (mantido)"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_file', type=str, default='landuse_processed')
    parser.add_argument('--output_file', type=str, default='unified_prophet_v4.pkl')
    return parser.parse_args()

def main():
    args = parse_args()
    try:
        logger.info("Carregando dados...")
        df = load_processed_data(args.input_file)

        # Garantir valores mínimos ANTES do agrupamento
        df['area_fazenda_ha'] = df['area_fazenda_ha'].clip(lower=0.0001)
        df['area_floresta_ha'] = df['area_floresta_ha'].clip(lower=0.0001)

        # Agrupamento e validação (mantido igual).
        df = df.groupby(['Estado', 'ano', 'bioma']).agg({
            'area_fazenda_ha': 'sum',
            'area_floresta_ha': 'sum',
            'taxa_conversao_anual': lambda x: np.average(x, weights=df.loc[x.index, 'area_fazenda_ha'])
        }).reset_index().rename(columns={
            'ano': 'ds',
            'taxa_conversao_anual': 'y'
        })
        _validate_input_data(df)
        df['ds'] = pd.to_datetime(df['ds'], format='%Y')

        # Dicionário de siglas dos estados
        SIGLAS_ESTADOS = {
            'Acre': 'AC', 'Alagoas': 'AL', 'Amapá': 'AP', 'Amazonas': 'AM',
            'Bahia': 'BA', 'Ceará': 'CE', 'Distrito Federal': 'DF', 'Espírito Santo': 'ES',
            'Goiás': 'GO', 'Maranhão': 'MA', 'Mato Grosso': 'MT', 'Mato Grosso do Sul': 'MS',
            'Minas Gerais': 'MG', 'Pará': 'PA', 'Paraíba': 'PB', 'Paraná': 'PR',
            'Pernambuco': 'PE', 'Piauí': 'PI', 'Rio de Janeiro': 'RJ', 'Rio Grande do Norte': 'RN',
            'Rio Grande do Sul': 'RS', 'Rondônia': 'RO', 'Roraima': 'RR',
            'Santa Catarina': 'SC', 'São Paulo': 'SP', 'Sergipe': 'SE', 'Tocantins': 'TO'
        }

        # CRIAR ENCODER GLOBAL PARA TODOS OS ESTADOS (ANTES DO LOOP).
        estado_encoder = LabelEncoder()
        estado_encoder.fit(df['Estado'].unique())  # Ajusta em TODOS os estados

        # Treina um modelo por estado
        for estado in df['Estado'].unique():
            sigla = SIGLAS_ESTADOS.get(estado, 'XX')  # 'XX' como fallback
            logger.info(f"Treinando modelo para {estado} ({sigla})...")
            
            # 2. CONFIGURAR O ENCODER NO MODELO (ADICIONE ESTA LINHA)
            forecaster = UnifiedForecaster()
            forecaster.encoder_estados = estado_encoder  # <--- CONFIGURAÇÃO CRÍTICA
            
            df_estado = df[df['Estado'] == estado].copy()
            df_estado['estado_code'] = estado_encoder.transform([estado])[0]
            
            forecaster.train(df_estado)
            
            # Salva com o padrão: unified_prophet_v4_<SIGLA>.pkl.
            output_path = Path('eco_guardian/models/saved_models') / f"unified_prophet_v4_{sigla}.pkl"
            forecaster.save_model(output_path)
            logger.info(f"Modelo salvo em: {output_path}")

        logger.info("Processo concluído!")
        return 0

    except Exception as e:
        logger.error(f"Erro: {str(e)}", exc_info=True)
        return 1

if __name__ == '__main__':
    sys.exit(main())