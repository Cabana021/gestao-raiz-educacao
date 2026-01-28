import json
import pandas as pd
import unicodedata
from dotenv import load_dotenv
from src.utils.db_manager import get_db_engine

class FunnelEngine:
    def __init__(self, config_path="src/utils/config.json", map_path="src/utils/normalization.json"):
        load_dotenv()
        self.config = self._load_json(config_path)
        self.unit_map = self._load_json(map_path)
        self.engine = get_db_engine()
        self.alias_to_canonical = self._build_alias_map()

        # Colunas obrigatórias para a UI não quebrar
        self.required_ui_columns = [
            "unidade",
            # Funil Acumulado
            "Leads", "Contato Produtivo", "Visita Agendada", "Visita Realizada", "Matricula",
            # Cohort (Estoque)
            "Inertes em Lead", "Aguardando Agendamento", "Aguardando Visita", "Em Negociação", "Finalizados (Matrícula)"
        ]
      
    def _load_json(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Aviso: Erro ao carregar {path}: {e}")
            return {}

    def remove_accents(self, text):
        if not isinstance(text, str): return text
        return ''.join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))

    def _normalize_key(self, text):
        if not isinstance(text, str): return str(text)
        return self.remove_accents(text.upper().strip())

    def extract_marca(self, unidade):
        """Retorna a marca a partir do nome da unidade para filtros da UI."""
        unidade_norm = self._normalize_key(unidade)
        for marca, info in self.unit_map.items():
            for unidade_data in info.get("unidades", []):
                canonical = self._normalize_key(unidade_data["nome_oficial"])
                if unidade_norm == canonical:
                    return marca
        return "OUTROS"
    
    def _build_alias_map(self):
        alias_map = {}
        self.inactive_units = [] 

        for marca, info in self.unit_map.items():
            unidades = info.get("unidades", [])
            for unidade in unidades:
                canonical = unidade["nome_oficial"]
                status = unidade.get("status", "ativo")
                
                if status == "inativo":
                    self.inactive_units.append(canonical)
                    
                # Mapeia nome oficial e aliases
                alias_map[self._normalize_key(canonical)] = canonical
                for alias in unidade.get("aliases", []):
                    alias_map[self._normalize_key(alias)] = canonical
                    
        return alias_map

    def normaliza_nome_marca(self, name):
        name_str = str(name).strip().lower()
        if not name or name_str in ['nan', 'none', '', 'null']:
            return "Leads Sem Unidade Identificada"

        key = self._normalize_key(str(name))
        return self.alias_to_canonical.get(key, name)

    def get_crm_data(self):
        print("[CRM] Extraindo e processando funil de vendas...")
        
        # Filtro de data (Pode virar parâmetro dinâmico futuramente)
        data_inicio = '2025-06-01' 
        
        query = f"""
        SELECT 
            unidade, 
            hs_pipeline_stage
        FROM Tabela_Leads_Raiz_v2
        WHERE hs_createdate >= '{data_inicio}'
        """

        try:
            df = pd.read_sql(query, self.engine)
            if df.empty: return pd.DataFrame()

            # Normaliza unidade antes de agrupar
            df["unidade"] = df["unidade"].apply(self.normaliza_nome_marca)

            # --- 1. Lógica de COHORT (Onde o lead está PARADO HOJE) ---
            # Mapeia IDs do Pipeline para Nomes Legíveis da UI
            stage_labels = {v: k for k, v in self.config.items()}
            df["status_atual"] = df["hs_pipeline_stage"].map(stage_labels).fillna("OUTROS")
            
            # De-Para dos nomes internos para os nomes que a UI/Excel esperam
            cohort_cols_map = {
                "LEADS": "Inertes em Lead",
                "LEADS_CONTATADOS": "Aguardando Agendamento",
                "AGENDAMENTO_REALIZADO": "Aguardando Visita",
                "VISITA_REALIZADA": "Em Negociação",
                "MATRICULADO_TOTAL": "Finalizados (Matrícula)"
            }
            
            cohort_counts = df.groupby(["unidade", "status_atual"]).size().unstack(fill_value=0)
            cohort_counts = cohort_counts.rename(columns=cohort_cols_map)

            # --- 2. Lógica de FUNIL ACUMULADO (Histórico de conversão) ---
            # Define hierarquia: Quem está na etapa 5, passou pela 4, 3, 2, 1.
            weights = {
                self.config.get("LEADS", "1018380105"): 1,
                self.config.get("LEADS_CONTATADOS", "1018380106"): 2,
                self.config.get("AGENDAMENTO_REALIZADO", "1022335280"): 3,
                self.config.get("VISITA_REALIZADA", "1018314554"): 4,
                self.config.get("MATRICULADO_TOTAL", "1111696774"): 5
            }
            
            df["rank"] = df["hs_pipeline_stage"].map(weights).fillna(0)

            # Cria colunas booleanas para soma
            df["Leads"] = 1 # Todo mundo é lead
            df["Contato Produtivo"] = (df["rank"] >= 2).astype(int)
            df["Visita Agendada"] = (df["rank"] >= 3).astype(int)
            df["Visita Realizada"] = (df["rank"] >= 4).astype(int)
            # Matrícula no CRM é indicativo, mas usaremos ERP como fonte da verdade depois
            df["Matrícula_CRM"] = (df["rank"] >= 5).astype(int) 

            cols_accum = ["Leads", "Contato Produtivo", "Visita Agendada", "Visita Realizada"]
            res_acumulado = df.groupby("unidade")[cols_accum].sum().reset_index()
            
            # Merge: Funil Acumulado + Snapshot de Cohort
            df_merged = pd.merge(res_acumulado, cohort_counts, on="unidade", how="left").fillna(0)
            
            return df_merged

        except Exception as e:
            print(f"[CRM] Erro: {e}")
            return pd.DataFrame()

    def get_erp_data(self):
        print("[ERP] Extraindo matrículas confirmadas...")
        
        query = """
        SELECT 
            T1.FILIAL AS unidade, 
            COUNT(DISTINCT T1.RA) AS Matricula
        FROM Z_PAINELMATRICULA T1
        INNER JOIN Tabela_Matrizcurricular T2 
            ON T1.GRADE = T2.GRADE 
            AND T1.CODCOLIGADA = T2.CODCOLIGADA
            AND T1.CODFILIAL = T2.CODFILIAL
        WHERE T1.CODPERLET IN ('2026')
        AND T1.STATUS IN ('Matriculado', 'Pré-Matriculado')
        AND T2.[Matricula Validade] = 'S'
        GROUP BY T1.FILIAL
        """

        try:
            df = pd.read_sql(query, self.engine)
            if df.empty: return pd.DataFrame()

            df["unidade"] = df["unidade"].apply(self.normaliza_nome_marca)
            return df.groupby("unidade", as_index=False)["Matricula"].sum()

        except Exception as e:
            print(f"[ERP] Erro: {e}")
            return pd.DataFrame()

    def generate_full_report(self):
        df_crm = self.get_crm_data()
        df_erp = self.get_erp_data()

        if df_crm.empty and df_erp.empty:
            return None

        # Merge CRM + ERP (ERP manda no número final de matrículas)
        df_final = pd.merge(df_crm, df_erp, on="unidade", how="outer").fillna(0)

        # Filtra inativas
        df_final = df_final[~df_final["unidade"].isin(self.inactive_units)]
        df_final = df_final[df_final["unidade"].str.strip() != ""]

        # Garante que todas as colunas necessárias para a UI existem (mesmo que zeradas)
        # Isso corrige o bug onde o gráfico de pizza quebra se não houver dados em uma etapa
        for col in self.required_ui_columns:
            if col not in df_final.columns:
                df_final[col] = 0

        # Força tipos inteiros para visualização limpa
        numeric_cols = df_final.select_dtypes(include=['float', 'int']).columns
        df_final[numeric_cols] = df_final[numeric_cols].astype(int)

        # Remove linhas irrelevantes (sem lead e sem matrícula)
        df_final = df_final[
            (df_final["Leads"] > 0) |
            (df_final["Matricula"] > 0)
        ]

        df_final = df_final.sort_values("Matricula", ascending=False)
        
        print(f"\n[ENGINE] Dados gerados: {len(df_final)} linhas.")
        return df_final

if __name__ == "__main__":
    motor = FunnelEngine()
    df = motor.generate_full_report()
    if df is not None:
        print(df.head().to_string())