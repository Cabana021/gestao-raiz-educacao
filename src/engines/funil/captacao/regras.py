import pandas as pd
import unicodedata
import logging

class FunnelBusinessRules:
    """
    Responsável por todas as regras de negócio, normalização de nomes,
    cálculos de colunas e consolidação de DataFrames.
    """
    def __init__(self, config, unit_map):
        self.config = config
        self.unit_map = unit_map
        self.alias_to_canonical, self.inactive_units = self._build_alias_map()
        
        # Colunas exigidas pela UI
        self.required_ui_columns = [
            "unidade",
            "Leads", "Contato Produtivo", "Visita Agendada", "Visita Realizada", "Matricula",
            "Inertes em Lead", "Aguardando Agendamento", "Aguardando Visita", "Em Negociação", "Finalizados (Matrícula)"
        ]

    # Helpers de Texto 
    def remove_accents(self, text):
        if not isinstance(text, str): return text
        return ''.join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))

    def _normalize_key(self, text):
        if not isinstance(text, str): return str(text)
        return self.remove_accents(text.upper().strip())

    def _build_alias_map(self):
        alias_map = {}
        inactive_units = [] 

        for marca, info in self.unit_map.items():
            for unidade in info.get("unidades", []):
                nome_oficial = unidade["nome_oficial"]
                
                # Verifica status e sucessão
                if "sucessora" in unidade:
                    nome_destino = unidade["sucessora"]
                    inactive_units.append(nome_oficial)
                else:
                    nome_destino = nome_oficial
                    if unidade.get("status") == "inativo":
                        inactive_units.append(nome_oficial)

                # Mapeia nome oficial
                key_oficial = self._normalize_key(nome_oficial)
                alias_map[key_oficial] = nome_destino

                # Mapeia aliases
                for alias in unidade.get("aliases", []):
                    key_alias = self._normalize_key(alias)
                    alias_map[key_alias] = nome_destino
                        
        return alias_map, inactive_units

    def normaliza_nome_marca(self, name):
        """Aplica a normalização baseada no mapa de aliases."""
        name_str = str(name).strip().lower()
        if not name or name_str in ['nan', 'none', '', 'null']:
            return "Leads Sem Unidade Identificada"

        key = self._normalize_key(str(name))
        return self.alias_to_canonical.get(key, name)

    # --- Lógica de Transformação CRM ---
    def transformar_dados_crm(self, df):
        """
        Recebe o DataFrame bruto do SQL do CRM e aplica as regras de funil:
        labels, pesos, cohort e acumulação.
        """
        if df.empty: return pd.DataFrame()

        # 1. Normalização de Unidade
        df["unidade"] = df["unidade"].apply(self.normaliza_nome_marca)

        # 2. Mapeamento de Status
        stage_labels = {v: k for k, v in self.config.items()}
        df["status_atual"] = df["hs_pipeline_stage"].map(stage_labels).fillna("OUTROS")
        
        # 3. Cohort (Onde o lead está parado hoje)
        cohort_cols_map = {
            "LEADS": "Inertes em Lead",
            "LEADS_CONTATADOS": "Aguardando Agendamento",
            "AGENDAMENTO_REALIZADO": "Aguardando Visita",
            "VISITA_REALIZADA": "Em Negociação",
            "MATRICULADO_TOTAL": "Finalizados (Matrícula)"
        }
        
        cohort_counts = df.groupby(["unidade", "status_atual"]).size().unstack(fill_value=0)
        cohort_counts = cohort_counts.rename(columns=cohort_cols_map)

        # 4. Cálculo de Pesos e Funil Acumulado
        weights = {
            self.config.get("LEADS", "1018380105"): 1,
            self.config.get("LEADS_CONTATADOS", "1018380106"): 2,
            self.config.get("AGENDAMENTO_REALIZADO", "1022335280"): 3,
            self.config.get("VISITA_REALIZADA", "1018314554"): 4,
            self.config.get("MATRICULADO_TOTAL", "1111696774"): 5
        }
        
        df["rank"] = df["hs_pipeline_stage"].map(weights).fillna(0)
        df["Leads"] = 1 
        df["Contato Produtivo"] = (df["rank"] >= 2).astype(int)
        df["Visita Agendada"] = (df["rank"] >= 3).astype(int)
        df["Visita Realizada"] = (df["rank"] >= 4).astype(int)
        
        cols_accum = ["Leads", "Contato Produtivo", "Visita Agendada", "Visita Realizada"]
        res_acumulado = df.groupby("unidade")[cols_accum].sum().reset_index()
        
        # Merge final do processamento CRM
        df_merged = pd.merge(res_acumulado, cohort_counts, on="unidade", how="left").fillna(0)
        return df_merged

    # --- Lógica de Consolidação Final ---
    def consolidar_relatorios(self, df_crm, df_erp):
        """
        Unifica CRM e ERP, remove inativos, garante colunas da UI e ordena.
        """
        # Merge
        df_final = pd.merge(df_crm, df_erp, on="unidade", how="outer").fillna(0)
        df_final["unidade"] = df_final["unidade"].apply(self.normaliza_nome_marca)
        
        # Agrupamento final para garantir unicidade
        df_final = df_final.groupby("unidade", as_index=False).sum(numeric_only=True)

        # Filtro de inativos e vazios
        df_final = df_final[~df_final["unidade"].isin(self.inactive_units)]
        df_final = df_final[df_final["unidade"].str.strip() != ""]

        # Garantia de colunas (Schema da UI)
        for col in self.required_ui_columns:
            if col not in df_final.columns:
                df_final[col] = 0

        # Tipagem
        numeric_cols = df_final.select_dtypes(include=['float', 'int']).columns
        df_final[numeric_cols] = df_final[numeric_cols].astype(int)

        # Filtro de linhas zeradas relevantes
        df_final = df_final[
            (df_final["Leads"] > 0) |
            (df_final["Matricula"] > 0)
        ]
        
        # Ordenação
        df_final = df_final.sort_values("Matricula", ascending=False)
        
        return df_final
