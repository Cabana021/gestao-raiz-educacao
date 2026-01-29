import os
import logging
import urllib.parse
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Variável global para armazenar a instância única do pool
_db_engine_instance = None

def get_db_engine():
    """
    Retorna a instância Singleton da engine SQLAlchemy.
    Garante que o pool de conexões seja reutilizado.
    """
    global _db_engine_instance

    if _db_engine_instance is not None:
        return _db_engine_instance

    load_dotenv()

    server = os.getenv("SERVER")
    database = os.getenv("DATABASE")
    user = os.getenv("USER")
    password = os.getenv("SENHA")
    driver = os.getenv("DRIVER")
    
    if not all([server, database, user, password]):
        raise ValueError("Configurações de banco de dados incompletas no .env")

    # Construção segura da Connection String
    conn_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        "ApplicationIntent=ReadOnly;"
    )
    
    params = urllib.parse.quote_plus(conn_str)
    
    try:
        _db_engine_instance = create_engine(
            f"mssql+pyodbc:///?odbc_connect={params}",
            pool_pre_ping=True, # Verifica se a conexão caiu antes de usar
            pool_size=10,       # Mantém até 10 conexões abertas
            max_overflow=20     # Permite picos temporários
        )
        logging.info("Engine de Banco de Dados inicializada (Singleton).")
        return _db_engine_instance
    except Exception as e:
        logging.critical(f"Falha fatal ao criar engine de banco: {e}")
        raise
