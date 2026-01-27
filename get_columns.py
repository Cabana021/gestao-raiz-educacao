import pandas as pd
from src.utils.db_manager import get_db_engine

def inspect_visita_realizada():
    engine = get_db_engine()

    # 1️⃣ Exemplos
    query_exemplos = """
    SELECT TOP 10
        unidade,
        hs_pipeline_stage,
        hs_createdate,
        hs_lastmodifieddate
    FROM Tabela_Leads_Raiz_v2
    WHERE hs_pipeline_stage = '1018314554'
    ORDER BY hs_lastmodifieddate DESC
    """


    df_exemplos = pd.read_sql(query_exemplos, engine)

    print("\nEXEMPLOS — STATUS 1018314554 (VISITA REALIZADA)")
    print(df_exemplos.to_string(index=False))

    # 2️⃣ Total
    query_total = """
    SELECT COUNT(*) AS total
    FROM Tabela_Leads_Raiz_v2
    WHERE hs_pipeline_stage = '1018314554'
    """

    # Colunas CRM
    query_cols = """
    SELECT TOP 1 *
    FROM Tabela_Leads_Raiz_v2
    """
    
    df = pd.read_sql(query_cols, engine)
    print(df.columns.tolist())
    
    df_total = pd.read_sql(query_total, engine)
    total = df_total.iloc[0]["total"]

    print(f"\nTOTAL DE REGISTROS COM STATUS 1018314554: {total}")

    return df_exemplos, total

def inspect_db():
    engine = get_db_engine()
    
    tables = {
        "CRM (HubSpot)": "Tabela_Leads_Raiz_v2",
        "ERP (TOTVS)": "Z_PAINELMATRICULA",
        "Matriculas": "Tabela_f_matriculas",
        "Matriz curricular": "Tabela_Matrizcurricular"
    }
    
    for sistema, tabela in tables.items():
        print(f"\n{'='*60}")
        print(f"INSPEÇÃO: {sistema} | Tabela: {tabela}")
        print(f"{'='*60}")
        
        try:
            # Pega apenas 1 linha para ver a estrutura sem pesar o banco
            query = f"SELECT TOP 1 * FROM {tabela}"
            df = pd.read_sql(query, engine)
            
            print(f"\nCOLUNAS ENCONTRADAS ({len(df.columns)}):")
            for col in df.columns:
                val = df[col].iloc[0]
                # Mostra o nome da coluna e um exemplo do dado que tem nela
                print(f" - {col:<30} | Exemplo: {val}")
                
        except Exception as e:
            print(f"Erro ao acessar {tabela}: {e}")

if __name__ == "__main__":
    inspect_db()
    inspect_visita_realizada()
