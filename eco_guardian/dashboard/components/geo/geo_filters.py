from typing import Dict
import pandas as pd

class GeoFilter:
    @staticmethod
    def filter_by_geo(df: pd.DataFrame, filters: Dict) -> pd.DataFrame:
        """Aplica filtros geográficos"""
        valid_filters = {
            'estado': lambda x: x.astype(str).isin(filters['estado']),
            'bioma': lambda x: x.isin(filters['bioma']),
            'cd_municipio': lambda x: x.isin(filters['cd_municipio'])
        }
        
        query_parts = []
        for key, values in filters.items():
            if key in valid_filters and values:
                query_parts.append(valid_filters[key](values))
                
        if query_parts:
            return df.loc[pd.concat(query_parts, axis=1).all(axis=1)]
        return df