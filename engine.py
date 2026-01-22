import json
import pandas as pd
import unicodedata
from datetime import datetime
from dotenv import load_dotenv
from src.utils.db_manager import get_db_engine

class FunnelEngine:
    def __init__(self, config_path="src/utils/config.json", map_path="src/utils/normalization.json"):
        load_dotenv()
        self.config = self._load_json(config_path)
        self.unit_map = self._load_json(map_path)
        self.engine = get_db_engine()
        self.alias_to_canonical = self._build_alias_map()

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
        '''Obtém dados do Hubspot'''
        
        print("[CRM] Extraindo e normalizando dados...")
        query = f"""
        SELECT unidade, hs_pipeline_stage, status_de_chamada
        FROM Tabela_Leads_Raiz_v2
        WHERE hs_createdate >= '{self.config["DATA_CORTE_INICIO"]}'
        """
        try:
            df = pd.read_sql(query, self.engine)
            df["unidade"] = df["unidade"].astype(str).apply(self.normaliza_nome_marca)

            df["metric_leads"] = 1
            df["metric_contatos"] = df["status_de_chamada"].apply(lambda x: 1 if str(x).lower() == "chamada produtiva" else 0)
            df["metric_agendamentos"] = df["hs_pipeline_stage"].apply(lambda x: 1 if str(x) == self.config["STAGE_AGENDADO"] else 0)
            df["metric_visitas"] = df["hs_pipeline_stage"].apply(lambda x: 1 if str(x) == self.config["STAGE_VISITADO"] else 0)

            # Agrupamento essencial para consolidar aliases
            return df.groupby("unidade")[["metric_leads", "metric_contatos", "metric_agendamentos", "metric_visitas"]].sum().reset_index()
        except Exception as e:
            print(f"[CRM] Erro: {e}"); return pd.DataFrame()

    def get_erp_data(self):
        '''Obtém dados do TOTVS.'''
        
        print("[ERP] Extraindo e unificando matrículas...")
        query = """
        SELECT FILIAL AS unidade, COUNT(*) AS metric_matriculas
        FROM Z_PAINELMATRICULA
        WHERE CODPERLET = '2026' AND STATUS = 'Matriculado' AND [TIPO MATRICULA] <> 'REMATRÍCULA'
        GROUP BY FILIAL
        """
        try:
            df = pd.read_sql(query, self.engine)
            df["unidade"] = df["unidade"].apply(self.normaliza_nome_marca)
            # Soma unidades que o mapa unificou (ex: Apogeu 1 e 2)
            return df.groupby("unidade", as_index=False)["metric_matriculas"].sum()
        except Exception as e:
            print(f"[ERP] Erro: {e}"); return pd.DataFrame()

    def generate_full_report(self):
        df_crm = self.get_crm_data()
        df_erp = self.get_erp_data()

        if df_crm.empty and df_erp.empty: return None

        df_final = pd.merge(df_crm, df_erp, on="unidade", how="outer").fillna(0)

        # Remove qualquer linha onde a unidade seja o nome oficial de uma marca inativa
        inativas = [d["nome_oficial"] for d in self.unit_map.values() if d.get("status") == "inativo"]
        df_final = df_final[~df_final["unidade"].isin(inativas)]
        
        # Remove a linha fantasma (strings vazias que escaparam)
        df_final = df_final[df_final["unidade"].str.strip() != ""]  
        
        cols = ["metric_leads", "metric_contatos", "metric_agendamentos", "metric_visitas", "metric_matriculas"]
        df_final[cols] = df_final[cols].astype(int)
        
        # Filtro de relevância: remove unidades sem leads E sem matrículas 
        df_final = df_final[(df_final["metric_leads"] > 0) | (df_final["metric_matriculas"] > 0)]
        
        # Filtro de marcas desconsideradas
        df_final = df_final[~df_final["unidade"].isin(self.inactive_units)]
        
        # Ordenação por volume de matrículas
        df_final = df_final.sort_values("metric_matriculas", ascending=False)
        
        print("\nFUNIL DE VENDAS CONSOLIDADO (CRM + ERP)")
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
