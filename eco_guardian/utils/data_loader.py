# utils/data_loader.py
import pandas as pd
from pathlib import Path
from typing import Union, Optional
import logging
import sys
import streamlit as st

try:
    import geopandas as gpd
    GEOPANDAS_AVAILABLE = True
except ImportError:
    GEOPANDAS_AVAILABLE = False

class DataLoader:
    def __init__(self):
        self.base_path = Path(__file__).parents[2] / "data"  # Subir 2 níveis
        self.logger = logging.getLogger(__name__)
        self._setup_logging()
        
    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )

    def _validate_file(self, file_path: Path):
        """Valida se o arquivo existe com mensagem detalhada"""
        if not file_path.exists():
            parent_dir = file_path.parent
            available_files = "\n".join([f"• {f.name}" for f in parent_dir.glob("*") if f.is_file()])
            
            self.logger.error(
                f"Arquivo não encontrado: {file_path.name}\n"
                f"Diretório: {parent_dir}\n"
                f"Arquivos disponíveis:\n{available_files}"
            )
            raise FileNotFoundError(f"Arquivo {file_path.name} não encontrado")

    def _load_file(self, file_path: Path) -> Union[pd.DataFrame, gpd.GeoDataFrame]:
        """Carrega arquivo com tratamento de erro aprimorado"""
        try:
            self._validate_file(file_path)
            
            if file_path.suffix == '.parquet':
                return pd.read_parquet(file_path)
            elif file_path.suffix == '.csv':
                return pd.read_csv(file_path)
            elif file_path.suffix in ('.shp', '.gpkg'):
                if not GEOPANDAS_AVAILABLE:
                    raise ImportError("Geopandas necessário para arquivos geoespaciais")
                return gpd.read_file(str(file_path))  # Convertendo para string para compatibilidade
            else:
                raise ValueError(f"Formato não suportado: {file_path.suffix}")
        except Exception as e:
            self.logger.error(f"Falha ao carregar {file_path}: {str(e)}")
            raise

    def load_custom_path(self, file_path: Union[str, Path]) -> Union[pd.DataFrame, gpd.GeoDataFrame]:
        """Carrega dados de um caminho específico"""
        full_path = Path(file_path) if isinstance(file_path, str) else file_path
        if not full_path.is_absolute():
            full_path = self.base_path / full_path
        return self._load_file(full_path)

    def load_landuse(self) -> pd.DataFrame:
        """Carrega dados de uso do solo processados"""
        file_path = self.base_path / "processed" / "landuse_processed.parquet"
        df = self._load_file(file_path)
        
        required_cols = {
            'cd_municipio': 'Código IBGE',  # Nome real da coluna
            'dc_municipio': 'Nome Município', 
            'Estado': 'Estado',
            'bioma': 'Bioma',
            'ano': 'Ano',
            'area_floresta_ha': 'Área floresta (ha)',
            'area_fazenda_ha': 'Área fazenda (ha)',
            'conversao_ha': 'Conversão anual (ha)'
        }
        
        # Verificação de colunas obrigatórias
        missing = [k for k in required_cols if k not in df.columns]
        if missing:
            raise ValueError(f"Colunas obrigatórias faltando: {missing}")

        # Tratamento de NaN
        nan_cols = df[['area_floresta_ha', 'area_fazenda_ha']].columns[df[['area_floresta_ha', 'area_fazenda_ha']].isna().any()]
        if not nan_cols.empty:
            df[nan_cols] = df[nan_cols].fillna(0.001)
            self.logger.warning(
                f"Substituídos {df[nan_cols].isna().sum().sum()} valores NaN por 0.001 nas colunas: {list(nan_cols)}"
            )

        # Verificação de valores negativos
        if (df[['area_floresta_ha', 'area_fazenda_ha']] < 0).any().any():
            negative_counts = (df[['area_floresta_ha', 'area_fazenda_ha']] < 0).sum()
            raise ValueError(
                f"Valores negativos encontrados:\n{negative_counts[negative_counts > 0].to_string()}"
            )
            
        return df
        
    def load_br_municipios(self) -> gpd.GeoDataFrame:
        """Versão corrigida com tipo consistente"""
        file_path = self.base_path / "raw" / "ibge" / "geografico" / "BR_Municipios_2023.geojson"
        
        # Adicione encoding='latin-1':
        gdf = gpd.read_file(file_path, encoding='latin-1')
        
        # Garante que a coluna seja sempre 'cd_municipio' (converte para int)
        gdf['cd_municipio'] = gdf['CD_MUN'].astype(str).str.strip().str[:7].astype(int)
        
        return gdf.drop(columns=['CD_MUN'])
    def load_br_estados(self) -> gpd.GeoDataFrame:
        """Versão corrigida com tipo consistente"""
        file_path = self.base_path / "raw" / "ibge" / "geografico" / "BR_UF_2023.geojson"
        
        # Adicione encoding='latin-1':
        gdf = gpd.read_file(file_path, encoding='latin-1')
        # Garante que as siglas estejam em maiúsculas
        gdf['SIGLA_UF'] = gdf['SIGLA_UF'].str.upper()
        
        return gdf 
    
    def load_desmatamento_bioma(self) -> pd.DataFrame:
        """Carrega dados de desmatamento por bioma com padronização do código do município."""
        
        file_path = self.base_path / "processed" / "prodes" / "desmatamento_municipio_bioma.parquet"
        
        try:
            df = self._load_file(file_path)
            print(f"Colunas originais: {df.columns.tolist()}")

            # **Garante que a coluna seja sempre 'cd_municipio'**
            if 'id_municipio' in df.columns:
                df.rename(columns={'id_municipio': 'cd_municipio'}, inplace=True)
            
            if 'cd_municipio' not in df.columns:
                raise ValueError("Coluna 'cd_municipio' não encontrada no arquivo")

            # Garante que a coluna cd_municipio seja numérica (7 dígitos)
            df['cd_municipio'] = df['cd_municipio'].astype(str).str.strip().str[:7].astype(int)
            print(f"Exemplo de conversão:\n{df[['cd_municipio']].head(2)}")
            
            print(f"Colunas finais: {df.columns.tolist()}")
            return df

        except Exception as e:
            print(f"Erro detalhado no loader: {str(e)}")
            raise ValueError(f"Falha ao processar dados de desmatamento: {str(e)}")

    def load_policy_data(self) -> pd.DataFrame:
        """Carrega e padroniza dados do Código Florestal (Lei 12.651/2012)"""
        file_path = self.base_path / "processed" / "policy" / "codigo_florestal_analisado.parquet"
        df = self._load_file(file_path)
        
        # Garante que todos os registros tenham ano_politica = 2012
        df['ano_politica'] = 2012  # Ano fixo da legislação
        
        # Verificação das colunas essenciais
        required_cols = ['texto', 'relevancia_ambiental', 'categoria']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            raise ValueError(f"Colunas obrigatórias faltando: {missing_cols}")
        
        return df

    def load_ibge_data(self) -> pd.DataFrame:
        """Carrega dados consolidados do IBGE"""
        file_path = self.base_path / "processed" / "ibge" / "ibge_consolidado.parquet"
        df = self._load_file(file_path)
        
        # Garantir tipos corretos
        numeric_cols = ['populacao', 'pib', 'pib_agropecuaria']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Converter código municipal para inteiro
        if 'cd_municipio' in df.columns:
            df['cd_municipio'] = df['cd_municipio'].astype(int)
        
        return df

    def load_municipios_brasil(self) -> gpd.GeoDataFrame:
        """Carrega dados geoespaciais de municípios brasileiros"""
        if not GEOPANDAS_AVAILABLE:
            raise ImportError("Instale geopandas: pip install geopandas")
        return self.load_br_municipios()
    
    def load_estados_brasil(self) -> gpd.GeoDataFrame:
        """Carrega dados geoespaciais de municípios brasileiros"""
        if not GEOPANDAS_AVAILABLE:
            raise ImportError("Instale geopandas: pip install geopandas")
        return self.load_br_estados()

    def load_model(self, model_name: str):
        """Carrega modelos com verificação de versão"""
        model_path = self.base_path.parent / "models" / "saved_models" / f"{model_name}.pkl"
        self._validate_file(model_path)
        
        try:
            import joblib
            return joblib.load(model_path)
        except ImportError:
            raise ImportError("Instale joblib: pip install joblib")

def load_processed_data(table_name: str) -> Union[pd.DataFrame, gpd.GeoDataFrame]:
    """Carrega dados processados com 3 modos:
    1. Nome da tabela (sem extensão)
    2. Nome do arquivo (com extensão)
    3. Caminho completo
    """
    loader = DataLoader()
    
    # Tenta carregar como caminho absoluto/relativo
    if Path(table_name).exists():
        return loader.load_custom_path(table_name)
        
    # Remove extensão se presente
    clean_name = Path(table_name).stem
    
    # Mapeamento de tabelas
    loaders = {
        "landuse_processed": loader.load_landuse,
        "ibge": loader.load_ibge_data,
        "ibge_consolidado": loader.load_ibge_data,
        "municipios": loader.load_municipios_brasil,
        "codigo_florestal_analisado": loader.load_policy_data,
        "policy": loader.load_policy_data,
        "br_municipios": loader.load_br_municipios,
        "br_estados": loader.load_br_estados,
        "estados": loader.load_estados_brasil,
        "desmatamento_bioma": loader.load_desmatamento_bioma,
        "prodes": loader.load_desmatamento_bioma
    }
    
    if clean_name not in loaders:
        available = ", ".join(loaders.keys())
        raise ValueError(
            f"Tabela desconhecida: {table_name}\n"
            f"Opções válidas:\n"
            f"- Nomes de tabelas: {available}\n"
            f"- Caminhos completos para arquivos .parquet"
        )
    
    return loaders[clean_name]()

if __name__ == "__main__":
    try:
        loader = DataLoader()
        test_cases = [
            "landuse_processed",
            "br_municipios",
            "desmatamento_bioma",
            "prodes",
            "ibge_consolidado",
            "ibge",
            "municipios",
            "codigo_florestal_analisado"

        ]
        
        for case in test_cases:
            print(f"\n=== Testando: {case} ===")
            result = load_processed_data(case)
            print(f"Tipo: {type(result)}")
            print(result.head())
            
    except Exception as e:
        print(f"\nERRO: {str(e)}")
        sys.exit(1)