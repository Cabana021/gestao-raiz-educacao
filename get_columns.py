import pandas as pd
from src.utils.db_manager import get_db_engine

def inspect_db():
    engine = get_db_engine()
    
    tables = {
        "CRM (HubSpot)": "Tabela_Leads_Raiz_v2",
        "ERP (TOTVS)": "Z_PAINELMATRICULA"
    }
    
    for sistema, tabela in tables.items():
        print(f"\n{'='*60}")
        print(f"🔍 INSPEÇÃO: {sistema} | Tabela: {tabela}")
        print(f"{'='*60}")
        
        try:
            # Pega apenas 1 linha para ver a estrutura sem pesar o banco
            query = f"SELECT TOP 1 * FROM {tabela}"
            df = pd.read_sql(query, engine)
            
            print(f"\n📋 COLUNAS ENCONTRADAS ({len(df.columns)}):")
            for col in df.columns:
                val = df[col].iloc[0]
                # Mostra o nome da coluna e um exemplo do dado que tem nela
                print(f" - {col:<30} | Exemplo: {val}")
                
        except Exception as e:
            print(f"❌ Erro ao acessar {tabela}: {e}")

if __name__ == "__main__":
    inspect_db()