import pandas as pd
import logging
import os
import urllib.parse
from sqlalchemy import create_engine
from dotenv import load_dotenv
from src.engines.engine import EngineBase

# Carrega variáveis do .env
load_dotenv()

class PendenciaLoader(EngineBase): 
    def __init__(self, arquivo_path=None, config_dict=None):
        super().__init__() 
        self.config = config_dict or {}

    def get_connection(self):
        """Cria conexão com banco SQL Server via SQLAlchemy + PyODBC."""
        try:
            server = os.getenv("SERVER")
            database = os.getenv("DATABASE")
            username = os.getenv("USER")
            password = os.getenv("SENHA")
            
            # Fallback de driver se não estiver no env
            driver = os.getenv("DB_DRIVER", "SQL Server")

            if not all([server, database, username, password]):
                logging.error("Variáveis de conexão SQL incompletas no .env")
                return None

            connection_string = f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};UID={username};PWD={password}"
            params = urllib.parse.quote_plus(connection_string)
            
            # fast_executemany=True otimiza, mas para leitura simples não é crítico.
            db_url = f"mssql+pyodbc:///?odbc_connect={params}"

            return create_engine(db_url)

        except Exception as e:
            logging.error(f"Erro ao configurar string de conexão: {e}")
            return None

    def carregar_dados(self):
        """Executa a query na Z_PAINELMATRICULA."""
        logging.info("Loader: Iniciando conexão SQL...")
        
        engine_sql = self.get_connection()
        if not engine_sql:
            return None

        query = """
        SELECT 
            NOMEGRUPO as Marca,
            FILIAL as Filial,
            RA,
            ALUNO as Aluno,
            RESPFINANCEIRO as Responsável,
            CPFRESPFINANCEIRO as CPF_Resp,
            [TIPO MATRICULA] as Tipo_Matricula,
            STATUS,
            SERIE as Série,
            TURNO as Turno,
            CURSO as Curso,
            GRADE as Grade,
            [DATA CADASTRO] as Data_Cadastro,
            [DATA MATRÍCULA] as Data_Matricula
        FROM Z_PAINELMATRICULA
        WHERE CODPERLET = '2026'
        """

        try:
            with engine_sql.connect() as conn:
                df = pd.read_sql(query, conn)

            if df.empty:
                logging.warning("Loader: Query retornou 0 registros para 2026.")
                return None

            # Normalização preliminar das colunas
            df.columns = df.columns.astype(str).str.strip()
            
            # Preenchimento de nulos para evitar erros nas operações de string
            cols_str = ['Marca', 'Filial', 'RA', 'Aluno', 'STATUS', 'Turno']
            for col in cols_str:
                if col in df.columns:
                    df[col] = df[col].fillna('').astype(str)

            logging.info(f"Loader: {len(df)} linhas carregadas do SQL.")
            return df

        except Exception as e:
            logging.error(f"Loader: Erro crítico na execução SQL: {e}", exc_info=True)
            return None
