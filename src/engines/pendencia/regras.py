import pandas as pd
import numpy as np
import logging

class PendenciaBusiness:
    def __init__(self, arquivo_path=None):
        self.cruzamento_realizado = True

    def aplicar_regras(self, df):
        """
        Aplica regras de negócio para identificar pendências reais.
        """
        if df is None or df.empty:
            return df

        logging.info("Business: Aplicando regras de saneamento e filtros...")
        
        # 1. Normalização para UpperCase 
        cols_norm = ['Marca', 'Filial', 'Aluno', 'STATUS', 'Turno', 'Tipo_Matricula', 'Curso', 'Grade']
        for col in cols_norm:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().str.upper()

        # 2. Remoção dos testes
        df = df[~df['Aluno'].str.contains('TESTE', na=False)].copy()

        # 3. Tranforma a marca Bom tempo em Global Tree Botafogo
        mask_bom_tempo = (df['Filial'].str.contains('BOM TEMPO', na=False)) | \
                         (df['Marca'].str.contains('BOM TEMPO', na=False))
        
        if mask_bom_tempo.any():
            logging.info(f"Business: Convertendo {mask_bom_tempo.sum()} registros 'Bom Tempo' para 'GLOBAL TREE'.")
            df.loc[mask_bom_tempo, 'Marca'] = 'GLOBAL TREE'
            df.loc[mask_bom_tempo, 'Filial'] = 'GLOBAL TREE - BOTAFOGO'

        # NOVA REGRA: MIGRAÇÃO INTEGRA EDUCACAO -> APOGEU CIDADE ALTA
        mask_integra = df['Filial'].str.contains('INTEGRA EDUCACAO', na=False)
        if mask_integra.any():
            logging.info(f"Business: Migrando {mask_integra.sum()} registros de 'INTEGRA' para 'APOGEU - CIDADE ALTA'.")
            df.loc[mask_integra, 'Marca'] = 'APOGEU'
            df.loc[mask_integra, 'Filial'] = 'APOGEU GLOBAL SCHOOL CIDADE ALTA'

        # 4. Blacklist de Marca e Filial
        exclusoes = [
            ('UNIFICADO', 'RAMIRO'),
            ('QI', 'BOTAFOGO'),
            ('AO CUBO', 'RECREIO'),
            ('AO CUBO', 'TIJUCA'),
            ('APOGEU', 'DIVINÓPOLIS'),
            ('APOGEU', 'UBÁ'),
        ]

        for marca_excl, filial_excl in exclusoes:
            mask_exc = (df['Marca'].str.contains(marca_excl, na=False)) & \
                       (df['Filial'].str.contains(filial_excl, na=False))
            if mask_exc.any():
                df = df[~mask_exc]

        # Filtro genérico para SÃO TOMÁS DE AQUINO
        mask_sao_tomas = df['Filial'].str.contains('SÃO TOMÁS', na=False) | \
                         df['Marca'].str.contains('SÃO TOMÁS', na=False)
        df = df[~mask_sao_tomas]

        # 5. FILTRO DE MARCAS VÁLIDAS (WHITELIST)
        marcas_validas = [
            'QI', 'SARAH DAWSEY', 'AMERICANO', 'LEONARDO DA VINCI', 
            'UNIÃO', 'SAP', 'GLOBAL TREE', 'MATRIZ', 
            'SÁ PEREIRA', 'UNIFICADO', 'APOGEU', 'AO CUBO'
        ]
        
        regex_marcas = '|'.join(marcas_validas)
        df = df[df['Marca'].str.contains(regex_marcas, regex=True, na=False)].copy()

        # 6. LÓGICA DE MATRICULADOS VS PENDENTES         
        status_confirmados = ['MATRICULADO', 'ATIVO', 'CURSANDO', 'CONFIRMADO', 'REMATRÍCULA']
        status_falso_positivo = ['PRÉ', 'PRE-', 'REQ', 'AGUARDANDO', 'PENDENTE', 'ANÁLISE', 'ANALISE']

        def checar_matricula_efetiva(status_val):
            if not any(k in status_val for k in status_confirmados):
                return False
            if any(k in status_val for k in status_falso_positivo):
                return False
            return True

        mask_is_matriculado = df['STATUS'].apply(checar_matricula_efetiva)
        
        # O set garante unicidade dos RAs matriculados
        ras_matriculados = set(df.loc[mask_is_matriculado, 'RA'].unique())

        if ras_matriculados:
            qtd_removida = df[df['RA'].isin(ras_matriculados)].shape[0]
            logging.info(f"Business: Removendo {len(ras_matriculados)} alunos (total {qtd_removida} linhas) que já possuem MATRÍCULA EFETIVADA.")
            df = df[~df['RA'].isin(ras_matriculados)].copy()

        # 7. FILTRO FINAL DE STATUS PENDENTE
        status_pendencia_keywords = ['PENDENTE', 'EM ANÁLISE', 'AGUARDANDO', 'RESERVA', 'PRÉ-MATRÍCULA', 'PRE-MATRÍCULA', 'REQ']
        
        def is_pendente(st):
            return any(k in st for k in status_pendencia_keywords)

        df = df[df['STATUS'].apply(is_pendente)].copy()

        # 8. DEDUPLICAÇÃO (TURNO/CURSO)
        # Garante que só tenhamos uma linha por aluno pendente
        if not df.empty:
            antes_dedup = len(df)
            df.drop_duplicates(subset=['RA'], keep='first', inplace=True)
            logging.info(f"Business: Deduplicação de Turnos/Cursos removeu {antes_dedup - len(df)} linhas.")

        # Ex: Marca="COLÉGIO QI", Filial="COLÉGIO QI RECREIO" -> Filial="RECREIO"
        if not df.empty:
            def limpar_nome_filial(row):
                marca = row['Marca']
                filial = row['Filial']
                # Verifica se a filial começa com o nome da marca
                if filial.startswith(marca):
                    # Remove o tamanho da string da marca do início da filial
                    novo_nome = filial[len(marca):]
                    # Remove espaços, hífens ou caracteres indesejados que sobraram no início
                    return novo_nome.strip(" -|")
                return filial

            df['Filial'] = df.apply(limpar_nome_filial, axis=1)

        # 9. CÁLCULOS FINAIS
        # ------------------------------------------------------------------
        if not df.empty:
            df['Data_Cadastro'] = pd.to_datetime(df['Data_Cadastro'], dayfirst=True, errors='coerce')
            hoje = pd.Timestamp.now().normalize()
            df['Dias_Pendente'] = (hoje - df['Data_Cadastro']).dt.days.fillna(0).astype(int)

            conditions = [(df['Dias_Pendente'] > 15), (df['Dias_Pendente'] >= 7)]
            choices = ['Crítico', 'Atenção']
            df['Status_Prioridade'] = np.select(conditions, choices, default='Novo')

            # Ordenação final
            df.sort_values(by=['Marca', 'Filial', 'Aluno'], inplace=True)

        return df
