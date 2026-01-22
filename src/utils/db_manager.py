import os
import sqlalchemy
from urllib.parse import quote_plus
from dotenv import load_dotenv


def get_db_engine():
    """
    Cria e retorna uma engine SQLAlchemy para SQL Server.
    Totalmente desacoplada do restante do sistema.
    """
    load_dotenv()

    conn_str = (
        f"DRIVER={{SQL Server}};"
        f"SERVER={os.getenv('SERVER')};"
        f"DATABASE={os.getenv('DATABASE')};"
        f"UID={os.getenv('USER')};"
        f"PWD={os.getenv('SENHA')};"
        "ApplicationIntent=ReadOnly;"
    )

    params = quote_plus(conn_str)
    return sqlalchemy.create_engine(
        f"mssql+pyodbc:///?odbc_connect={params}"
    )
