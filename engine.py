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

        # Ordem hierárquica do funil 
        self.stage_order = {
            self.config["LEADS"]: 1,
            self.config["LEADS_CONTATADOS"]: 2,
            self.config["AGENDAMENTO_REALIZADO"]: 3,
            self.config["VISITA_REALIZADA"]: 4,
            self.config["MATRICULADO_TOTAL"]: 5
        }
      
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
        return self.remove_accents(text.upper().strip())

    def _build_alias_map(self):
        alias_map = {}
        self.inactive_units = [] # Nova lista para controle

        for _, data in self.unit_map.items():
            canonical = data["nome_oficial"]
            
            # Se a unidade for inativa, guardamos o nome oficial dela
            if data.get("status") == "inativo":
                self.inactive_units.append(canonical)
                
            alias_map[self._normalize_key(canonical)] = canonical
            for alias in data["aliases"]:
                alias_map[self._normalize_key(alias)] = canonical
        return alias_map

    def normaliza_nome_marca(self, name):
        # 1. Trata nulos, vazios e strings de erro
        name_str = str(name).strip().lower()
        if not name or name_str in ['nan', 'none', '', 'null']:
            return self.unit_map.get("DESCONHECIDO", {}).get("nome_oficial", "Leads Raiz Sem Unidades")

        # 2. Normaliza para buscar no dicionário de aliases
        key = self._normalize_key(str(name))
        
        # 3. Busca o nome canônico. 
        return self.alias_to_canonical.get(key, name)

    def get_crm_data(self):
        print("[CRM] Extraindo e processando funil...")

        query = f"""
        SELECT
            unidade,
            hs_pipeline_stage
        FROM Tabela_Leads_Raiz_v2
        WHERE hs_createdate >= '{self.config["DATA_CORTE_INICIO"]}'
        """

        try:
            df = pd.read_sql(query, self.engine)
            if df.empty:
                return pd.DataFrame()

            df["unidade"] = df["unidade"].apply(self.normaliza_nome_marca)

            # Mapeia prioridade do estágio
            df["stage_rank"] = df["hs_pipeline_stage"].map(self.stage_order).fillna(0)

            # Classificação acumulada do funil
            df["metric_leads"] = 1
            df["metric_contatos"] = (df["stage_rank"] >= 2).astype(int)
            df["metric_agendamentos"] = (df["stage_rank"] >= 3).astype(int)
            df["metric_visitas"] = (df["stage_rank"] >= 4).astype(int)

            return (
                df.groupby("unidade")[[
                    "metric_leads",
                    "metric_contatos",
                    "metric_agendamentos",
                    "metric_visitas"
                ]]
                .sum()
                .reset_index()
            )

        except Exception as e:
            print(f"[CRM] Erro: {e}")
            return pd.DataFrame()

    def get_erp_data(self):
        print("[ERP] Extraindo matrículas...")

        query = """
        SELECT
            FILIAL AS unidade,
            COUNT(DISTINCT RA) AS metric_matriculas
        FROM Z_PAINELMATRICULA
        WHERE CODPERLET = '2026'
          AND STATUS = 'Matriculado'
          AND [TIPO MATRICULA] <> 'REMATRÍCULA'
        GROUP BY FILIAL
        """

        try:
            df = pd.read_sql(query, self.engine)
            if df.empty:
                return pd.DataFrame()

            df["unidade"] = df["unidade"].apply(self.normaliza_nome_marca)
            return df.groupby("unidade", as_index=False)["metric_matriculas"].sum()

        except Exception as e:
            print(f"[ERP] Erro: {e}")
            return pd.DataFrame()

    def generate_full_report(self):
        df_crm = self.get_crm_data()
        df_erp = self.get_erp_data()

        if df_crm.empty and df_erp.empty:
            return None

        df_final = pd.merge(df_crm, df_erp, on="unidade", how="outer").fillna(0)

        # Remove marcas inativas
        df_final = df_final[~df_final["unidade"].isin(self.inactive_units)]
        df_final = df_final[df_final["unidade"].str.strip() != ""]

        cols = [
            "metric_leads",
            "metric_contatos",
            "metric_agendamentos",
            "metric_visitas",
            "metric_matriculas"
        ]
        df_final[cols] = df_final[cols].astype(int)

        # Remove marcas irrelevantes
        df_final = df_final[
            (df_final["metric_leads"] > 0) |
            (df_final["metric_matriculas"] > 0)
        ]

        df_final = df_final.sort_values("metric_matriculas", ascending=False)

        print("\nFUNIL DE CAPTAÇÃO CONSOLIDADO (CRM + ERP)")
        print(df_final.to_string(index=False))
        return df_final

    def quick_query(self, query, limit=None):
        try:
            df = pd.read_sql(query, self.engine)
            if limit: df = df.head(limit)
            print(df.to_string(index=False))
            return df
        except Exception as e:
            print(f"Erro: {e}"); return pd.DataFrame()

if __name__ == "__main__":
    motor = FunnelEngine()
    df_funil = motor.generate_full_report()
