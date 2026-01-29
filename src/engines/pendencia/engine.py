import pandas as pd
from src.engines.base import EngineBase

class PendenciaEngine(EngineBase):
    """
    Responsável por coletar dados de alunos (Pendentes e Matriculados).
    Herda conexão e log da EngineBase.
    """

    # SQL constants movidas para atributos de classe para limpeza
    SQL_PENDENTES = """
    SELECT
        CAST(P.CODCOLIGADA AS VARCHAR) AS CODCOLIGADA,
        CASE 
            WHEN P.FILIAL LIKE '%BOM TEMPO%' OR P.NOMEGRUPO LIKE '%BOM TEMPO%' THEN 'GLOBAL TREE'
            WHEN P.FILIAL LIKE '%INTEGRA EDUCACAO%' THEN 'APOGEU'
            ELSE UPPER(LTRIM(RTRIM(P.NOMEGRUPO)))
        END AS Marca,
        CASE 
            WHEN P.FILIAL LIKE '%BOM TEMPO%' THEN 'GLOBAL TREE - BOTAFOGO'
            WHEN P.FILIAL LIKE '%INTEGRA EDUCACAO%' THEN 'APOGEU GLOBAL SCHOOL CIDADE ALTA'
            ELSE UPPER(LTRIM(RTRIM(P.FILIAL)))
        END AS Filial,
        P.RA,
        UPPER(P.ALUNO) AS Aluno,
        P.CPFRESPFINANCEIRO AS CPF_Resp,
        UPPER(P.RESPFINANCEIRO) AS Responsável,
        UPPER(P.[TIPO MATRICULA]) AS Tipo_Matricula,
        P.SERIE AS Série,
        P.TURNO AS Turno,
        UPPER(P.STATUS) AS STATUS,
        P.[DATA CADASTRO] AS Data_Cadastro
    FROM Z_PAINELMATRICULA P
    WHERE 
        P.CODPERLET = '2026'
        AND P.ALUNO NOT LIKE '%TESTE%'
        AND (
            P.STATUS LIKE '%PENDENTE%' OR 
            P.STATUS LIKE '%AGUARDANDO%' OR 
            P.STATUS LIKE '%ANALISE%' OR 
            P.STATUS LIKE '%REQ%' OR
            P.STATUS LIKE '%RESERVA%' OR
            P.STATUS LIKE '%PRÉ%'
        )
        AND P.STATUS NOT IN ('MATRICULADO', 'ATIVO', 'CURSANDO', 'CONFIRMADO', 'REMATRÍCULA')
        AND NOT (P.NOMEGRUPO LIKE '%UNIFICADO%' AND P.FILIAL LIKE '%RAMIRO%')
        AND NOT (P.NOMEGRUPO LIKE '%QI%' AND P.FILIAL LIKE '%BOTAFOGO%')
        AND NOT (P.NOMEGRUPO LIKE '%AO CUBO%' AND (P.FILIAL LIKE '%RECREIO%' OR P.FILIAL LIKE '%TIJUCA%'))
        AND NOT (P.NOMEGRUPO LIKE '%APOGEU%' AND (P.FILIAL LIKE '%DIVINÓPOLIS%' OR P.FILIAL LIKE '%UBÁ%'))
    """

    SQL_MATRICULADOS = """
    SELECT DISTINCT RA
    FROM Tabela_Matrizcurricular
    WHERE [Matricula Validade] = 'S'
    """

    def __init__(self):
        super().__init__() # Inicializa o EngineBase (Logger e DB)

    def get_pendentes(self) -> pd.DataFrame:
        """Busca alunos pendentes e aplica tipagem básica."""
        self.logger.info("Iniciando extração de pendentes...")
        
        df = self.executar_query(self.SQL_PENDENTES)
        
        if not df.empty:
            # Tratamento de tipos seguro
            df['RA'] = df['RA'].astype(str).str.strip()
            df['Data_Cadastro'] = pd.to_datetime(df['Data_Cadastro'], dayfirst=True, errors='coerce')
        
        return df

    def get_matriculados_ra(self) -> set:
        """Retorna um SET de RAs matriculados para verificação rápida (O(1))."""
        self.logger.info("Buscando RAs matriculados...")
        
        df = self.executar_query(self.SQL_MATRICULADOS)
        
        if not df.empty and 'RA' in df.columns:
            return set(df['RA'].astype(str).str.strip().unique())
            
        return set()