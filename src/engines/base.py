import pandas as pd
import logging
from abc import ABC
from src.utils.db_manager import get_db_engine

class EngineBase(ABC):
    """
    Classe base abstrata. Fornece acesso padronizado ao banco de dados
    e utilitários de log para todas as engines filhas.
    """
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        try:
            # Centraliza a obtenção da conexão
            self.db_engine = get_db_engine()
        except Exception as e:
            self.logger.error(f"Não foi possível vincular o DB Manager: {e}")
            self.db_engine = None

    def executar_query(self, query: str, params=None) -> pd.DataFrame:
        """
        Executa uma consulta SQL e retorna um DataFrame.
        Trata erros e logs de forma centralizada.
        """
        if not self.db_engine:
            self.logger.error("Tentativa de query sem conexão ativa.")
            return pd.DataFrame()

        try:
            self.logger.debug(f"Executando query (início): {query[:50]}...")
            # O Pandas gerencia abrir/fechar a conexão automaticamente ao receber a engine
            df = pd.read_sql(query, self.db_engine, params=params)
            self.logger.info(f"Query executada com sucesso. Linhas retornadas: {len(df)}")
            return df
        except Exception as e:
            self.logger.error(f"Erro na execução da query: {e}")
            # Retorna DataFrame vazio para não quebrar pipelines que esperam DF
            return pd.DataFrame()