import pandas as pd
import os
from datetime import datetime
from src.engines.base import EngineBase


class PendenciaEngine(EngineBase):
    """
    Motor otimizado para Pendências TOTVS com validação cruzada de Matriz Curricular.
    Reconciliado com Power Query em 30/01/2026.

    Atualizações:
    - DEDUPLICAÇÃO TOTAL: Agora agrupa por RA/Aluno considerando a DATA MÍNIMA (1º interesse).
    - CORREÇÃO ERRO 8711: Removido ORDER BY dentro do STRING_AGG.
    - Limpeza visual via Pandas.
    """

    SQL_PENDENTES_AVANCADO = """
    WITH CTE_MatrizValida AS (
        SELECT DISTINCT 
            CAST(CODCOLIGADA AS VARCHAR) AS CODCOLIGADA, 
            CAST(CODFILIAL AS VARCHAR) AS CODFILIAL, 
            UPPER(LTRIM(RTRIM(GRADE))) AS GRADE
        FROM Tabela_Matrizcurricular
        WHERE [Matricula Validade] = 'S'
    ),
    
    CTE_DadosBrutos AS (
        SELECT 
            CAST(P.CODCOLIGADA AS VARCHAR) AS CODCOLIGADA,
            P.CODFILIAL,
            CASE 
                WHEN P.FILIAL LIKE '%BOM TEMPO%' OR P.NOMEGRUPO LIKE '%BOM TEMPO%' THEN 'GLOBAL TREE'
                WHEN P.FILIAL LIKE '%INTEGRA EDUCACAO%' THEN 'APOGEU'
                ELSE UPPER(LTRIM(RTRIM(P.NOMEGRUPO)))
            END AS Marca,
            CASE 
                WHEN P.FILIAL LIKE '%BOM TEMPO%' THEN 'GLOBAL TREE - BOTAFOGO'
                WHEN P.FILIAL LIKE '%INTEGRA EDUCACAO%' THEN 'APOGEU GLOBAL SCHOOL CIDADE ALTA'
                ELSE UPPER(LTRIM(RTRIM(P.FILIAL)))
            END AS Filial_Tratada,
            P.RA,
            UPPER(LTRIM(RTRIM(P.ALUNO))) AS Aluno,
            UPPER(LTRIM(RTRIM(P.CURSO))) AS Curso,
            P.SERIE AS Serie,
            UPPER(LTRIM(RTRIM(P.GRADE))) AS GRADE,
            UPPER(LTRIM(RTRIM(P.TURNO))) AS Turno,
            UPPER(LTRIM(RTRIM(P.STATUS))) AS Status_CRM,
            P.[DATA CADASTRO] AS Data_Cadastro
            -- Removemos o DATEDIFF daqui, faremos no agrupamento final
        FROM Z_PAINELMATRICULA P
        INNER JOIN CTE_MatrizValida M 
            ON CAST(P.CODCOLIGADA AS VARCHAR) = M.CODCOLIGADA 
            AND CAST(P.CODFILIAL AS VARCHAR) = M.CODFILIAL 
            AND UPPER(LTRIM(RTRIM(P.GRADE))) = M.GRADE
        WHERE 
            P.CODPERLET = '2026'
            AND P.STATUS = 'Pendente'
            AND P.ALUNO NOT LIKE '%TESTE%'
            AND P.ALUNO NOT LIKE '%SARAH DAWSEY%' 
            AND P.ALUNO NOT LIKE '%ESCOLA%'       
            AND P.ALUNO NOT LIKE '%INFANTIL%'     
            AND NOT (P.NOMEGRUPO LIKE '%QI%' AND P.FILIAL LIKE '%BOTAFOGO%')
            AND NOT (P.NOMEGRUPO LIKE '%UNIFICADO%' AND P.FILIAL LIKE '%RAMIRO%')
            AND NOT (P.NOMEGRUPO LIKE '%AO CUBO%' AND (P.FILIAL LIKE '%RECREIO%' OR P.FILIAL LIKE '%TIJUCA%'))
            AND NOT (P.NOMEGRUPO LIKE '%APOGEU%' AND (P.FILIAL LIKE '%DIVINÓPOLIS%' OR P.FILIAL LIKE '%UBÁ%'))
    )

    -- Etapa 3: Agrupamento final COM DATA MÍNIMA
    SELECT 
        CODCOLIGADA,
        CODFILIAL,
        Marca,
        Filial_Tratada,
        RA,
        Aluno,
        Curso,
        Serie,
        STRING_AGG(GRADE, ' | ') AS GRADE,
        STRING_AGG(Turno, ', ') AS Turno, 
        Status_CRM,
        -- AQUI ESTÁ A MUDANÇA: Pegamos a menor data (mais antiga)
        MIN(Data_Cadastro) AS Data_Cadastro,
        -- Recalculamos os dias com base nessa data antiga
        DATEDIFF(day, MIN(Data_Cadastro), GETDATE()) AS Dias_Pendente
    FROM CTE_DadosBrutos
    GROUP BY 
        CODCOLIGADA,
        CODFILIAL,
        Marca,
        Filial_Tratada,
        RA,
        Aluno,
        Curso,
        Serie,
        Status_CRM
        -- REMOVIDO: Data_Cadastro e Dias_Pendente do GROUP BY
    ORDER BY Dias_Pendente DESC
    """

    def __init__(self):
        super().__init__()

    def get_pendentes(self) -> pd.DataFrame:
        self.logger.info("Executando Query 2026 Final (Agrupamento por Data Mínima)...")

        try:
            df = self.executar_query(self.SQL_PENDENTES_AVANCADO)

            if df is not None and not df.empty:
                # Tratamento de datas
                df["Data_Cadastro"] = pd.to_datetime(
                    df["Data_Cadastro"], dayfirst=True, errors="coerce"
                )

                # Tratamento numérico
                df["Dias_Pendente"] = (
                    pd.to_numeric(df["Dias_Pendente"], errors="coerce")
                    .fillna(0)
                    .astype(int)
                )

                # Regra de SLA
                def definir_prioridade(dias):
                    if dias > 90:
                        return "Crítico"
                    if dias < 7:
                        return "Novo"
                    return "Atenção"

                df["SLA_Status"] = df["Dias_Pendente"].apply(definir_prioridade)

                # Normalização final
                df["Marca"] = df["Marca"].astype(str).str.strip().str.upper()
                df["Filial_Tratada"] = (
                    df["Filial_Tratada"].astype(str).str.strip().str.upper()
                )

                # Limpeza e Ordenação Visual das Strings Agrupadas
                def limpar_duplicatas_string(texto, separador):
                    if pd.isna(texto):
                        return ""
                    items = [x.strip() for x in str(texto).split(separador)]
                    return separador.join(sorted(set(items)))

                df["Turno"] = df["Turno"].apply(
                    lambda x: limpar_duplicatas_string(x, ",")
                )
                df["GRADE"] = df["GRADE"].apply(
                    lambda x: limpar_duplicatas_string(x, "|")
                )

                # Geração automática do Excel de conferência
                self.exportar_analise_bruta(df)

            return df

        except Exception as e:
            self.logger.error(f"Erro Crítico no Engine: {e}")
            return None

    def exportar_analise_bruta(self, df: pd.DataFrame):
        try:
            filename = f"analise_2026_unificado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            df.to_excel(filename, index=False)
            self.logger.info(f"✅ Arquivo de conferência gerado: {filename}")
            print(f"\n[DEBUG] Relatório gerado com {len(df)} linhas únicas: {filename}")
        except Exception as e:
            self.logger.error(f"Falha ao gerar excel: {e}")
