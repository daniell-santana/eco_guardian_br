import logging
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Union, List, Optional
from sklearn.preprocessing import StandardScaler, OneHotEncoder, LabelEncoder
from sklearn.compose import ColumnTransformer
from prophet import Prophet
import joblib
import warnings
warnings.filterwarnings("ignore")

# Configuração do logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('time_series_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

warnings.filterwarnings("ignore")

class UnifiedForecaster:
    def __init__(self):
        """Inicializa o modelo com configurações otimizadas e validações"""
        # 1. Configuração do Prophet
        self.model = Prophet(
            growth='flat',                 # Define o crescimento como 'flat' (constante), ou seja, assume que não há crescimento exponencial ao longo do tempo — ideal quando se modela séries estacionárias como taxas.
            seasonality_mode='additive',  # Define que as sazonalidades serão somadas ao valor da série (em vez de multiplicadas), o que é adequado para dados que não variam proporcionalmente à magnitude do valor base.
            changepoint_prior_scale=0.03,  # Controla a flexibilidade do modelo para se ajustar a mudanças estruturais (changepoints); quanto maior o valor, mais sensível ele será a mudanças — valor 0.3 é relativamente flexível.
            interval_width=0.95,          # Define o intervalo de confiança das previsões como 95% — padrão em análises estatísticas para maior segurança nas projeções.
            mcmc_samples=300,             # Ativa a estimação bayesiana com amostragem Monte Carlo (MCMC), gerando incerteza mais realista nas previsões — útil para cenários com alta variabilidade como meio ambiente.
            yearly_seasonality=False        # 🔴 Desliga porque os dados são anuais
        ).add_seasonality(
            name='custom',                # Nome dado à sazonalidade adicional (personalizada).
            period=365.25,                # Define que essa sazonalidade ocorre em ciclos anuais (365.25 dias para incluir ano bissexto).
            fourier_order=1               # Define a complexidade da sazonalidade com 1 termo de Fourier — quanto menor o valor, mais suave o padrão capturado; evita overfitting.
        )
                
        # 2. Definição das features (X) - todas devem existir após o pré-processamento
        self.feature_columns = [
            'area_fazenda_ha',     # Área agrícola
            'area_floresta_ha',    # Área florestal
            'prop_floresta',       # Proporção calculada
            'estado_code'          # Estado codificado
        ]
        
        # 3. Metadados geográficos (não usados como features)
        self.geo_columns = ['Estado', 'bioma']  # Para referência pós-predição
        
        # 4. Pré-processador
        self.preprocessor = self._create_preprocessor()
        
        # 5. Estado do modelo
        self.is_trained = False
        
        # 6. Codificador de estados
        self.encoder_estados = None  # Será configurado durante o treino

        # Validação interna
        self._validate_init()

    def _validate_init(self):
        """Valida consistência interna na inicialização"""
        required_features = {'area_fazenda_ha', 'area_floresta_ha', 'prop_floresta', 'estado_code'}
        if not required_features.issubset(set(self.feature_columns)):
            missing = required_features - set(self.feature_columns)
            raise ValueError(f"Features obrigatórias faltando: {missing}")

    def _create_preprocessor(self):
        """Cria pré-processador apenas para as features numéricas"""
        return ColumnTransformer(
            [('num', StandardScaler(), self.feature_columns)],
            remainder='passthrough',
            verbose_feature_names_out=False  # Nomes originais são mantidos
        )

    def preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Pré-processamento com agrupamento por estado/ano/bioma e cálculos corretos"""
        # 1. Validação inicial
        if 'y' not in df.columns:
            raise ValueError("Coluna 'y' não encontrada no DataFrame de entrada")
        
        required_cols = {'ds', 'y', 'Estado', 'area_floresta_ha', 'area_fazenda_ha', 'bioma'}
        if missing := required_cols - set(df.columns):
            raise ValueError(f"Colunas obrigatórias faltando: {missing}")

        # 2. Preparação dos dados
        df = df.copy()
        df['ds'] = pd.to_datetime(df['ds'])
        df['y'] = df['y'].replace([np.inf, -np.inf], np.nan).fillna(0)

        # 3. Agrupamento dos dados
        df_grouped = df.groupby(['Estado', 'ds', 'bioma']).agg({
            'area_fazenda_ha': 'sum',
            'area_floresta_ha': 'sum',
            'y': 'first'  # Usa o valor já pré-calculado
        }).reset_index()

        # 3.a. Verificação dos valores originais de área
        total_area_original = df_grouped['area_fazenda_ha'] + df_grouped['area_floresta_ha']
        assert not (total_area_original <= 0).any(), "Área total inválida detectada"

        # 4. Cálculo da proporção de floresta
        df_grouped['prop_floresta'] = np.where(
            total_area_original > 0,
            df_grouped['area_floresta_ha'] / total_area_original,
            0.0
        )

        # 5. Codificação de estados 
        if self.encoder_estados is None:
            raise RuntimeError("Encoder de estados não configurado - deve ser passado externamente")
        try:
            df_grouped['estado_code'] = self.encoder_estados.transform(df_grouped['Estado'])
        except ValueError as e:
            missing = set(df_grouped['Estado']) - set(self.encoder_estados.classes_)
            raise ValueError(f"Estados não mapeados: {missing}") from e

        # 6. Processamento das features com escalonamento
        processed = df_grouped.copy()
        try:
            features = df_grouped[self.feature_columns]
            if hasattr(self.preprocessor, 'mean_'):
                processed[self.feature_columns] = self.preprocessor.transform(features)
            else:
                processed[self.feature_columns] = self.preprocessor.fit_transform(features)
        except Exception as e:
            raise RuntimeError(f"Falha no escalonamento: {str(e)}")
        
        # A verificação de total de área pós-escalonamento é removida, pois o StandardScaler pode gerar valores negativos

        # 7. Ordem garantida das colunas
        col_order = [
            'ds', 
            'y', 
            'Estado', 
            'bioma',
            'area_fazenda_ha',
            'area_floresta_ha',
            'prop_floresta',
            'estado_code'
        ] 
        return processed[col_order]

    @staticmethod
    def _aggregate_taxa(series: pd.Series, areas: pd.Series) -> float:
        """Calcula a média harmônica ponderada das taxas municipais por estado
        Args:
            series: Série com as taxas de conversão municipais
            areas: Série com as áreas totais (floresta + fazenda) de cada município
        """
        # Remove infinitos e NaNs
        valid_mask = series.replace([np.inf, -np.inf], np.nan).notna()
        series = series[valid_mask]
        areas = areas[valid_mask]
        
        if series.empty:
            return 0.0
        
        # Caso especial: se todas as taxas são zero
        if (series == 0).all():
            return 0.0
        
        # Média harmônica ponderada pelas áreas
        try:
            return 1 / np.average(1 / series, weights=areas)
        except ZeroDivisionError:
            # Fallback para média harmônica simples se pesos zerados
            return 1 / np.mean(1 / series)

    def train(self, df: pd.DataFrame) -> None:
        """Treina o modelo com validações robustas
        
        Args:
            df: DataFrame com colunas originais (será pré-processado)
            
        Raises:
            ValueError: Se dados estiverem inconsistentes
            RuntimeError: Se pré-processamento falhar
        """
        try:
            # 1. Pré-processamento
            df_processed = self.preprocess_data(df)
            
            # 2. Validação das colunas essenciais
            required_cols = {'ds', 'y'} | set(self.preprocessor.get_feature_names_out())
            missing = required_cols - set(df_processed.columns)
            if missing:
                raise ValueError(f"Colunas faltando após pré-processamento: {missing}")
            
            # 3. Seleciona APENAS as features definidas em self.feature_columns
            # (evita vazamento de dados ou colunas inválidas)
            feature_cols = [col for col in self.feature_columns 
                        if col in df_processed.columns]
            
            # 4. Adiciona regressores com verificação
            for col in feature_cols:
                if col not in self.model.extra_regressors:  # Evita duplicação
                    self.model.add_regressor(col, standardize=True)

            # 5. Treinamento com dataset final
            self.model.fit(df_processed[['ds', 'y'] + feature_cols])
            self.is_trained = True
            
        except Exception as e:
            self.is_trained = False
            raise RuntimeError(f"Falha no treinamento: {str(e)}")

    def predict(self, initial_conditions: Dict, horizon: int = 5) -> pd.DataFrame:
        """Gera previsões para um estado específico usando condições iniciais.'"""
        if 'last_year' not in initial_conditions:
            raise ValueError("'last_year' é obrigatório nas condições iniciais")
        
        try:
            self._validate_inputs(initial_conditions)
            
            if not isinstance(horizon, int) or horizon <= 0:
                raise ValueError("horizon deve ser um inteiro positivo")

            if 'estado_code' not in initial_conditions:
                initial_conditions['estado_code'] = self.encoder_estados.transform([initial_conditions['Estado']])[0]

            if 'prop_floresta' not in initial_conditions:
                total_area = initial_conditions['area_fazenda_ha'] + initial_conditions['area_floresta_ha']
                initial_conditions['prop_floresta'] = (initial_conditions['area_floresta_ha'] / total_area) if total_area > 0 else 0.0

            future = self._create_future_dataframe(initial_conditions, horizon)
            
            future_processed = pd.DataFrame(
                self.preprocessor.transform(future[self.feature_columns]),
                columns=self.feature_columns  # Mantém os nomes originais
            )
            # Mantenha as colunas originais para o Prophet:
            future_processed = pd.concat([future[['ds', 'y']], future_processed], axis=1)

            forecast = self.model.predict(future_processed)
            forecast = forecast.join(future[self.geo_columns])

            result = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper', 'Estado', 'bioma']].rename(columns={
                'ds': 'data',
                'yhat': 'conversao_ha_prevista',
                'yhat_lower': 'limite_inferior',
                'yhat_upper': 'limite_superior'
            })

            initial_floresta = initial_conditions['area_floresta_ha']
            result['area_floresta_projetada'] = initial_floresta * (1 - result['conversao_ha_prevista']).cumprod()
            result['area_fazenda_projetada'] = (
                initial_conditions['area_fazenda_ha'] + 
                (initial_floresta - result['area_floresta_projetada'])
            )

            return result[[
                'data', 'Estado', 'bioma',
                'conversao_ha_prevista', 'limite_inferior', 'limite_superior',
                'area_floresta_projetada', 'area_fazenda_projetada'
            ]].round(4)

        except Exception as e:
            logger.error(f"Erro na previsão para {initial_conditions.get('Estado', 'Estado desconhecido')}: {str(e)}")
            raise RuntimeError(f"Falha na geração de previsões: {str(e)}") from e

    def _validate_inputs(self, inputs: Dict) -> None:
        # 1. Verificar campos obrigatórios
        required_keys = self.feature_columns + self.geo_columns + ['y', 'last_year']
        missing = [k for k in required_keys if k not in inputs]
        if missing:
            raise ValueError(f"Inputs faltando: {missing}")

        # 2. Validação de tipos
        type_checks = {
            'y': (int, float, np.number),
            'area_fazenda_ha': (int, float, np.number),
            'area_floresta_ha': (int, float, np.number),
            'Estado': str,
            'bioma': str,
            'prop_floresta': (int, float, np.number),
            'estado_code': (int, np.integer),
            'last_year': (int, np.integer), 
        }
        
        for key, valid_types in type_checks.items():
            if key in inputs and not isinstance(inputs[key], valid_types):
                raise TypeError(f"{key} deve ser do tipo {valid_types}. Recebido: {type(inputs[key])}")

        # 3. Validação de valores numéricos
        numeric_checks = {
            'area_fazenda_ha': (0, None),  # > 0
            'area_floresta_ha': (0, None),  # > 0
            'prop_floresta': (0, 1)        # Entre 0 e 1
            # 'y' pode ser qualquer número real (positivo, negativo ou zero)
        }
        
        for key, (min_val, max_val) in numeric_checks.items():
            value = inputs[key]
            if min_val is not None and value < min_val:
                raise ValueError(f"{key} deve ser maior ou igual a {min_val}. Recebido: {value}")
            if max_val is not None and value > max_val:
                raise ValueError(f"{key} deve ser menor ou igual a {max_val}. Recebido: {value}")

        # 4. Validação de bioma
        valid_biomas = ['Amazônia', 'Caatinga', 'Cerrado', 'Pantanal', 'Mata Atlântica', 'Pampa']
        if inputs['bioma'] not in valid_biomas:
            raise ValueError(f"Bioma inválido. Opções: {valid_biomas}")

        # 5. Validação do estado (se encoder estiver disponível)
        if hasattr(self, 'encoder_estados') and hasattr(self.encoder_estados, 'classes_'):
            if inputs['Estado'] not in self.encoder_estados.classes_:
                raise ValueError(f"Estado '{inputs['Estado']}' não foi visto durante o treinamento")

    def _create_future_dataframe(self, initial: Dict, horizon: int) -> pd.DataFrame:
        """Garante continuidade temporal começando no ano seguinte ao último histórico"""
        # Validação de tipos
        for col in ['area_fazenda_ha', 'area_floresta_ha', 'prop_floresta', 'y']:
            if not isinstance(initial[col], (int, float, np.number)):
                raise TypeError(f"{col} deve ser numérico, recebido {type(initial[col])}")

        # Garante que o estado_code está correto
        try:
            estado_code = self.encoder_estados.transform([initial['Estado']])[0]
        except ValueError as e:
            raise ValueError(f"Erro ao codificar estado: {str(e)}")
        
        # Pega o último ano dos dados históricos
        last_year = initial['last_year']
        
        # Cria datas começando no ano seguinte (2024 se último ano for 2023)
        dates = pd.date_range(
            start=f"{last_year + 1}-01-01",
            periods=horizon + 1,  # +1 para incluir o primeiro ano de projeção
            freq='YS'
        )
        dates = dates[:horizon]  # Mantém apenas os anos solicitados
        
        # DataFrame base
        df = pd.DataFrame({
            'ds': dates,
            'y': float(initial['y']),
            'area_fazenda_ha': float(initial['area_fazenda_ha']),
            'area_floresta_ha': float(initial['area_floresta_ha']),
            'prop_floresta': float(initial['prop_floresta']),
            'estado_code': int(initial['estado_code']),
            'Estado': initial['Estado'],
            'bioma': initial['bioma']
        })

        return df


    def _format_output(self, forecast: pd.DataFrame, initial: Dict) -> pd.DataFrame:
        """Formata os resultados da previsão """
        result = forecast[[
            'ds', 'yhat', 'yhat_lower', 'yhat_upper',
            'Estado', 'bioma'  # Mantém apenas estado e bioma
        ]].rename(columns={
            'ds': 'data',
            'yhat': 'conversao_ha_prevista',
            'yhat_lower': 'limite_inferior',
            'yhat_upper': 'limite_superior'
        })
        
        # Calcular métricas derivadas
        initial_floresta = initial['area_floresta_ha']
        result['area_floresta_projetada'] = initial_floresta * (1 - initial['y'])**(result.index + 1)  # Usar 'y'
        result['area_fazenda_projetada'] = initial['area_fazenda_ha'] + (initial_floresta - result['area_floresta_projetada'])
        
        # Ordenar colunas
        return result[[
            'data', 'Estado', 'bioma',
            'conversao_ha_prevista', 'limite_inferior', 'limite_superior',
            'area_floresta_projetada', 'area_fazenda_projetada'
        ]].round(2)

    def save_model(self, output_path: Union[str, Path]) -> None:
        """Salva o modelo com verificação de integridade"""
        if not self.is_trained:
            raise RuntimeError("Modelo não treinado")
            
        required_artifacts = ['model', 'preprocessor', 'encoder_estados']
        for artifact in required_artifacts:
            if not hasattr(self, artifact) or getattr(self, artifact) is None:
                raise ValueError(f"Artefato {artifact} não está disponível para salvar")

        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            joblib.dump({
                'model': self.model,
                'preprocessor': self.preprocessor,
                'encoder_estados': self.encoder_estados,
                'feature_columns': self.feature_columns,
                'geo_columns': self.geo_columns,
                'metadata': {
                    'train_date': pd.Timestamp.now(),
                    'states_trained': list(self.encoder_estados.classes_)
                }
            }, output_path)
            
        except Exception as e:
            logger.error(f"Erro ao salvar modelo: {str(e)}")
            raise

    @classmethod
    def load_model(cls, model_path: Union[str, Path]) -> 'UnifiedForecaster':
        """Carrega um modelo salvo garantindo que o pré-processador está ajustado"""
        try:
            # Carrega os artefatos
            artifacts = joblib.load(model_path)
        
            # Cria uma nova instância do forecaster
            forecaster = cls()
            
            # Restaura os componentes
            forecaster.model = artifacts.get('model')
            forecaster.preprocessor = artifacts.get('preprocessor')
            forecaster.feature_columns = artifacts.get('feature_columns', [])
            forecaster.geo_columns = artifacts.get('geo_columns', [])
            # Recuperar o encoder
            forecaster.encoder_estados = artifacts.get('encoder_estados')

            # Verifica se o encoder_estados está presente
            if forecaster.encoder_estados is None:
                raise RuntimeError("Encoder de estados não encontrado")

            # Verifica se o pré-processador está ajustado
            if hasattr(forecaster.preprocessor, 'transform'):
                # Se já estiver fitted, apenas retorna
                forecaster.is_trained = True
            else:
                raise RuntimeError("Pré-processador não foi ajustado corretamente")
                
            return forecaster
        except FileNotFoundError:
            raise FileNotFoundError(f"Modelo não encontrado em: {model_path}")
        except Exception as e:
            raise RuntimeError(f"Erro ao carregar o modelo: {e}")
        
    def get_state_historical_data(self, df: pd.DataFrame, estado: str) -> Dict[str, float]:
        """Extrai médias históricas de um estado específico para usar como condições iniciais"""
        # Mapeamento de colunas alternativas
        col_y = 'y' if 'y' in df.columns else 'taxa_conversao_anual'
        
        required_cols = {'Estado', 'bioma', 'area_fazenda_ha', 'area_floresta_ha', col_y}
        if missing := required_cols - set(df.columns):
            raise ValueError(f"Colunas faltando no DataFrame: {missing}")

        state_data = df[df['Estado'] == estado]
        
        if state_data.empty:
            raise ValueError(f"Dados não encontrados para o estado: {estado}")
        
        # Calcula proporção média de floresta
        total_area = state_data['area_fazenda_ha'] + state_data['area_floresta_ha']
        prop_floresta = (state_data['area_floresta_ha'] / total_area).mean()
        
        return {
            'Estado': estado,
            'bioma': state_data['bioma'].iloc[0],
            'area_fazenda_ha': state_data['area_fazenda_ha'].mean(),
            'area_floresta_ha': state_data['area_floresta_ha'].mean(),
            'prop_floresta': prop_floresta,
            'y': state_data[col_y].mean(),  # Alterado para 'y'
            'estado_code': state_data['estado_code'].iloc[0] if 'estado_code' in state_data.columns else 0
        }