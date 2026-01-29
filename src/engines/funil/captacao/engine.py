import pandas as pd
import logging
from sqlalchemy import text
from src.utils.db_manager import get_db_engine

class FunnelEngine:
    def __init__(self):
        self.db = get_db_engine()
        self.logger = logging.getLogger(__name__)
        # CORREÇÃO 1: Inicializa o atributo esperado pelos filtros da UI
        self.unit_map = {} 

    def extract_marca(self, unidade_str):
        """
        Método auxiliar para extrair a MARCA de uma string 'MARCA - UNIDADE'.
        Chamado pela UI para agrupar os cards.
        """
        if pd.isna(unidade_str) or not isinstance(unidade_str, str):
            return "OUTROS"
        
        parts = unidade_str.split('-')
        if parts:
            return parts[0].strip()
        return unidade_str

    # CORREÇÃO 2: Renomeado de 'get_funnel_data' para 'generate_full_report'
    # para bater com a chamada da linha 352 do funil_screen.py
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
                self.logger.warning("Ambas as fontes de dados (CRM e ERP) retornaram vazio.")
                return pd.DataFrame()

            # 3. Processamento / Merge
            df_consolidado = self._process_data(df_crm, df_erp)
            
            # CORREÇÃO 3: Popula o unit_map para os filtros da UI funcionarem
            if not df_consolidado.empty and 'unidade' in df_consolidado.columns:
                unique_units = df_consolidado['unidade'].unique()
                self.unit_map = {u: u for u in unique_units}

            self.logger.info(f"Relatório consolidado gerado: {len(df_consolidado)} linhas.")
            return df_consolidado

        except Exception as e:
            self.logger.error(f"Erro no fluxo do Funil: {e}")
            return pd.DataFrame()

    def _get_crm_data(self):
        """Busca volumetria do CRM (Leads, Inscritos, etc)"""
        self.logger.info("Extraindo dados do CRM...")
        
        # Ajuste a query conforme suas tabelas reais. 
        # Mantendo estrutura genérica robusta.
        query = """
        SELECT 
            u.nome as unidade,
            COUNT(c.id) as total_leads,
            SUM(CASE WHEN c.etapa = 'Inscrito' THEN 1 ELSE 0 END) as inscritos,
            SUM(CASE WHEN c.etapa = 'Vestibular' THEN 1 ELSE 0 END) as vestibular,
            SUM(CASE WHEN c.etapa = 'Matriculado' THEN 1 ELSE 0 END) as matriculados_crm
        FROM tb_crm_candidatos c
        JOIN tb_unidades u ON c.unidade_id = u.id
        WHERE c.data_cadastro >= DATEADD(day, -30, GETDATE())
        GROUP BY u.nome
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
            u.nome as unidade,
            COUNT(m.ra) as matriculados_erp,
            SUM(m.valor_pago) as receita
        FROM tb_erp_matriculas m
        JOIN tb_unidades u ON m.unidade_id = u.id
        WHERE m.status = 'ATIVO'
          AND m.data_matricula >= DATEADD(day, -30, GETDATE())
        GROUP BY u.nome
        """
        try:
            with self.db.connect() as conn:
                df = pd.read_sql(text(query), conn)
                return df
        except Exception as e:
            self.logger.error(f"Erro query ERP: {e}")
            return pd.DataFrame()

    def _process_data(self, df_crm, df_erp):
        """Cruza os dados do CRM e ERP pela Unidade"""
        
        # Normalização para garantir o merge (Upper case e strip)
        if not df_crm.empty:
            df_crm['unidade'] = df_crm['unidade'].astype(str).str.strip().str.upper()
        
        if not df_erp.empty:
            df_erp['unidade'] = df_erp['unidade'].astype(str).str.strip().str.upper()

        # Merge (Left Join priorizando CRM, pois é o funil de vendas)
        if df_crm.empty:
            return df_erp
        
        if df_erp.empty:
            df_crm['matriculados_erp'] = 0
            df_crm['receita'] = 0.0
            return df_crm

        # Junção
        df_final = pd.merge(df_crm, df_erp, on='unidade', how='left').fillna(0)
        
        return df_final