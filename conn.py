import pyodbc
import pandas as pd
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente e configura a conexão com o DB
load_dotenv()

conn_str = (
    f"DRIVER={{SQL Server}};"
    f"SERVER={os.getenv('SERVER')};"
    f"DATABASE={os.getenv('DATABASE')};"
    f"UID={os.getenv('USER')};"
    f"PWD={os.getenv('SENHA')};"
    "ApplicationIntent=ReadOnly;"
)


def explorar_banco():
    """Conecta independentemente para listar tabelas e colunas."""
    try:
        with pyodbc.connect(conn_str) as conn:
            print("[Explorar] Conexão bem sucedida!\n")
            
            print("Buscando tabelas...")
            query_tabelas = """
            SELECT TABLE_SCHEMA, TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
            """
            df_tabelas = pd.read_sql(query_tabelas, conn)
            print(df_tabelas.to_string())
            print("-" * 50)

            print("\nProcurando colunas 'Lead', 'Visit', 'Matric'...")
            query_colunas = """
            SELECT t.name AS Tabela, c.name AS Coluna
            FROM sys.columns c
            JOIN sys.tables t ON c.object_id = t.object_id
            WHERE c.name LIKE '%Lead%' 
               OR c.name LIKE '%Visit%' 
               OR c.name LIKE '%Matric%'
               OR c.name LIKE '%Renov%'
            ORDER BY t.name
            """
            df_colunas = pd.read_sql(query_colunas, conn)
            
            if not df_colunas.empty:
                print("\nColunas encontradas:")
                print(df_colunas.to_string())
            else:
                print("\nNenhuma coluna encontrada.")

    except Exception as e:
        print(f"Erro ao explorar banco: {e}")

def espiar_tabela(nome_tabela, conexao):
    print(f"\nEspiando: {nome_tabela}")
    try:
        # Pega as 5 primeiras linhas para ver o conteúdo
        query = f"SELECT TOP 5 * FROM {nome_tabela}"
        df = pd.read_sql(query, conexao)
        
        if not df.empty:
            # Mostra todas as colunas, não resume
            pd.set_option('display.max_columns', None) 
            print(df.head())
            
            # Se tiver colunas de Status, lista os valores únicos para ver os nomes exatos
            cols_status = [c for c in df.columns if 'Status' in c or 'Fase' in c or 'Etapa' in c]
            for col in cols_status:
                print(f"\nValues únicos em '{col}':")
                # Pega valores distintos para mapearmos o funil
                q_distinct = f"SELECT DISTINCT {col} FROM {nome_tabela}"
                df_dist = pd.read_sql(q_distinct, conexao)
                print(df_dist[col].tolist())
        else:
            print("Tabela vazia.")
    except Exception as e:
        print(f"Erro ao ler {nome_tabela}: {e}")
    

if __name__ == "__main__":
    tabela_matriculas = 'Z_PAINELMATRICULA'
    tabela_matriz = 'Tabela_Matrizcurricular'
    ano_desejado = '2026'
    
    print(f"Iniciando processamento para o ano: {ano_desejado}")
    
    try:
        with pyodbc.connect(conn_str) as conn:
            print("Conectado! Iniciando inspeção...")

            # 1. Investigar a tabela de Leads/CRM (Onde devem estar as Visitas e Leads)
            espiar_tabela('Tabela_Hubspot', conn)
            
            # Se a Hubspot falhar, tentamos a Leads Raiz v2
            espiar_tabela('Tabela_Leads_Raiz_v2', conn)

            # 2. Investigar a tabela de Matrículas (Onde está a conversão final)
            espiar_tabela('Z_PAINELMATRICULA', conn)
            
            # 3. Investigar Marcas e Filiais (Para fazer o agrupamento correto)
            espiar_tabela('Tabela_Lista_Filiais', conn)

    except Exception as e:
        print(f"Erro fatal: {e}")
    
    
    try:
        with pyodbc.connect(conn_str) as conn:
            print("Conexão principal aberta.")
                
        print("\n--- Iniciando Exploração do Schema ---")
        explorar_banco()

    except pyodbc.Error as ex:
        sqlstate = ex.args[1]
        print(f"Erro de Banco de Dados: {sqlstate}")
    except Exception as e:
        print(f"Erro Geral: {e}")
    
    print("\nFim do processamento.")
