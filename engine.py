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

    def extract_marca(self, unidade):
        """
        Retorna a marca (chave do normalization.json) a partir do nome oficial da unidade
        """
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

        # Percorre cada Marca no JSON
        for marca, info in self.unit_map.items():
            # Entra na lista de unidades de cada marca
            unidades = info.get("unidades", [])
            
            for unidade in unidades:
                canonical = unidade["nome_oficial"]
                status = unidade.get("status", "ativo")
                
                # Se a unidade for inativa, guardamos o nome oficial para filtrar no final
                if status == "inativo":
                    self.inactive_units.append(canonical)
                    
                # Mapeia o nome oficial para ele mesmo
                alias_map[self._normalize_key(canonical)] = canonical
                
                # Mapeia todos os apelidos (aliases) para o nome oficial
                for alias in unidade.get("aliases", []):
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
        print("[CRM] Extraindo e processando funil de vendas (2026)...")

        # 1. Filtro fixo para 2026 (ou via config se preferir manter dinâmico)
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
            if df.empty:
                return pd.DataFrame()

            # Normalização do nome da marca para bater com o ERP depois
            df["unidade"] = df["unidade"].apply(self.normaliza_nome_marca)
            
            df["stage_rank"] = df["hs_pipeline_stage"].map(self.stage_order).fillna(0)

            # Definição das Métricas Acumuladas
            # Nível 1: Leads (Todo mundo que entrou no banco é Lead, mesmo que perdido)
            df["Leads"] = 1 
            
            # Nível 2: Contato Produtivo (Quem avançou para rank 2 ou mais)
            df["Contato Produtivo"] = (df["stage_rank"] >= 2).astype(int)
            
            # Nível 3: Visita Agendada (Quem avançou para rank 3 ou mais)
            df["Visita Agendada"] = (df["stage_rank"] >= 3).astype(int)
            
            # Nível 4: Visita Realizada (Quem avançou para rank 4 ou mais)
            df["Visita Realizada"] = (df["stage_rank"] >= 4).astype(int)

            # Agrupamento
            return (
                df.groupby("unidade")[[
                    "Leads",
                    "Contato Produtivo",
                    "Visita Agendada",
                    "Visita Realizada"
                ]]
                .sum()
                .reset_index()
            )

        except Exception as e:
            print(f"[CRM] Erro: {e}")
            return pd.DataFrame()

    def get_erp_data(self):
        print("[ERP] Extraindo matrículas confirmadas e pré-matrículas (2025-2026)...")
        
        # Query ajustada para incluir 2025/2026, status pré-matriculado e validade 'S'
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
            if df.empty:
                return pd.DataFrame()

            # Normaliza para garantir que o "merge" com o CRM funcione
            df["unidade"] = df["unidade"].apply(self.normaliza_nome_marca)
            
            # Como o GROUP BY já foi feito no SQL, aqui só agrupamos se a normalização
            # tiver juntado duas filiais (ex: 'Unidade Centro' e 'Centro' viraram a mesma)
            return df.groupby("unidade", as_index=False)["Matricula"].sum()

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
            "Leads",
            "Contato Produtivo",
            "Visita Agendada",
            "Visita Realizada",
            "Matricula"
        ]
        df_final[cols] = df_final[cols].astype(int)

        # Remove marcas irrelevantes
        df_final = df_final[
            (df_final["Leads"] > 0) |
            (df_final["Matricula"] > 0)
        ]

        df_final = df_final.sort_values("Matricula", ascending=False)

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

    if df_funil is not None:
        df_funil.to_excel("funil_consolidado.xlsx", index=False)
        print("\nArquivo Excel gerado: funil_consolidado.xlsx")
