import pandas as pd
import logging
import json
from sqlalchemy import text
from src.utils.db_manager import get_db_engine


class FunnelEngine:
    def __init__(self):
        self.db = get_db_engine()
        self.logger = logging.getLogger(__name__)
        self.unit_map = {}

        try:
            with open("src/utils/config.json", "r") as f:
                config = json.load(f)
                self.data_inicio = config.get("DATA_INICIO")
        except Exception as e:
            self.logger.error(f"Erro ao carregar config.json: {e}")
            self.data_inicio = "2025-01-01"  # Fallback de segurança

    def extract_marca(self, unidade_str):
        """
        Método auxiliar para extrair a MARCA de uma string 'MARCA - UNIDADE'.
        Chamado pela UI para agrupar os cards.
        """
        if pd.isna(unidade_str) or not isinstance(unidade_str, str):
            return "OUTROS"

        parts = unidade_str.split("-")
        if parts:
            return parts[0].strip()
        return unidade_str

    def generate_full_report(self):
        """
        Orquestra a busca de dados do CRM e ERP e consolida as informações.
        """
        try:
            # 1. Buscar dados
            df_crm = self._get_crm_data()
            df_erp = self._get_erp_data()

            # 2. Validação se tudo falhar
            if df_crm.empty and df_erp.empty:
                self.logger.warning(
                    "Ambas as fontes de dados (CRM e ERP) retornaram vazio."
                )
                return pd.DataFrame()

            # 3. Processamento / Merge
            df_consolidado = self._process_data(df_crm, df_erp)

            if not df_consolidado.empty and "unidade" in df_consolidado.columns:
                unique_units = df_consolidado["unidade"].unique()
                self.unit_map = {u: u for u in unique_units}

            self.logger.info(
                f"Relatório consolidado gerado: {len(df_consolidado)} linhas."
            )
            return df_consolidado

        except Exception as e:
            self.logger.error(f"Erro no fluxo do Funil: {e}")
            return pd.DataFrame()

    def _get_crm_data(self):
        """Busca volumetria do CRM (Leads, Inscritos, etc)"""
        self.logger.info("Extraindo dados do CRM...")

        query = f"""
        SELECT 
            unidade, 
            hs_pipeline_stage,
            1 as Leads
        FROM Tabela_Leads_Raiz_v2
        WHERE hs_createdate >= '{self.data_inicio}'
        """
        try:
            with self.db.connect() as conn:
                df = pd.read_sql(text(query), conn)
                return df
        except Exception as e:
            self.logger.error(f"Erro query CRM: {e}")
            return pd.DataFrame()

    def _get_erp_data(self):
        """Busca dados financeiros/acadêmicos do ERP"""
        self.logger.info("Extraindo dados do ERP...")
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
            with self.db.connect() as conn:
                df = pd.read_sql(text(query), conn)
                return df
        except Exception as e:
            self.logger.error(f"Erro query ERP: {e}")
            return pd.DataFrame()

    def _process_data(self, df_crm, df_erp):
        """Cruza os dados do CRM e ERP pela Unidade, Traduz os Códigos do Pipeline e Pivota"""

        # 1. Normalização das Chaves (Unidade) - Upper e Strip para garantir o match
        if not df_crm.empty:
            df_crm["unidade"] = df_crm["unidade"].astype(str).str.strip().str.upper()

        if not df_erp.empty:
            df_erp["unidade"] = df_erp["unidade"].astype(str).str.strip().str.upper()

        # 2. Tratamento do CRM (Tradução dos Códigos e Pivotagem)
        if not df_crm.empty:
            # --- MAPA DE TRADUÇÃO (DE-PARA) ---
            # Converte os IDs numéricos do HubSpot para os nomes usados no Dashboard
            stage_mapper = {
                "1018380105": "Novos Leads",  # LEADS (Entrada)
                "1018380106": "Leads Contatados",  # LEADS_CONTATADOS
                "1022335280": "Visita Agendada",  # AGENDAMENTO_REALIZADO (Nome exato do Card)
                "1018314554": "Visita Realizada",  # VISITA_REALIZADA (Nome exato do Card)
                "1111696774": "Matriculado CRM",  # MATRICULADO_TOTAL (No CRM)
                "1018314555": "Declinado",  # DECLINADO
            }

            # Garante que a coluna de estágio seja string limpa para bater com o dicionário
            df_crm["hs_pipeline_stage"] = (
                df_crm["hs_pipeline_stage"].astype(str).str.strip()
            )

            # Aplica a tradução. Se o código não estiver no mapa, mantém o original.
            df_crm["hs_pipeline_stage"] = df_crm["hs_pipeline_stage"].replace(
                stage_mapper
            )

            # Pivota: Transforma linhas (estágios) em colunas
            # index = Unidade
            # columns = Estágios (Visita Agendada, Visita Realizada, etc.)
            # values = Leads (contagem)
            df_crm_pivot = df_crm.pivot_table(
                index="unidade",
                columns="hs_pipeline_stage",
                values="Leads",
                aggfunc="sum",
                fill_value=0,
            )

            # 3. Cálculo do Total de LEADS
            # Soma todas as colunas numéricas geradas pelo pivot para ter o volume total
            df_crm_pivot["Leads"] = df_crm_pivot.sum(axis=1)

            # 4. Garantia de Colunas Críticas
            # Se ninguém estiver na etapa "Visita Agendada", a coluna não é criada pelo pivot.
            # Forçamos a criação dela com 0 para não quebrar a UI.
            colunas_obrigatorias = ["Visita Agendada", "Visita Realizada"]
            for col in colunas_obrigatorias:
                if col not in df_crm_pivot.columns:
                    df_crm_pivot[col] = 0

            # Reseta o índice para 'unidade' voltar a ser coluna
            df_crm_pivot = df_crm_pivot.reset_index()

        else:
            # Caso o CRM não retorne nada
            df_crm_pivot = pd.DataFrame(
                columns=["unidade", "Leads", "Visita Agendada", "Visita Realizada"]
            )

        # 5. Tratamento do ERP
        if df_erp.empty:
            # Se não tem dados do ERP, adiciona coluna de matrícula zerada
            df_crm_pivot["Matricula"] = 0
            return df_crm_pivot

        # 6. Merge Final (União CRM + ERP)
        # Outer Join: Mantém unidades que só existem no CRM e unidades que só existem no ERP
        df_final = pd.merge(df_crm_pivot, df_erp, on="unidade", how="outer").fillna(0)

        # 7. Limpeza Final
        # Garante que colunas essenciais existam e sejam numéricas
        cols_check = ["Leads", "Matricula", "Visita Agendada", "Visita Realizada"]
        for col in cols_check:
            if col not in df_final.columns:
                df_final[col] = 0

        return df_final
