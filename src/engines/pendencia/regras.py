import pandas as pd
import numpy as np
import logging

class ProcessadorRegras:
    """
    Atua como adaptador entre os dados brutos SQL e o Relatório.
    Calcula KPIs derivados (Dias, Prioridade) e armazena a lista de matriculados
    para que o report.py consiga calcular conversão.
    """
    def __init__(self, config=None):
        # Estes atributos são lidos pelo report.py
        self.cruzamento_realizado = False
        self.ras_matriculados_atuais = set()
        self.config = config
        
    def aplicar_regras(self, df_pendentes, set_matriculados=None):
        """
        Recebe o DF bruto do SQL e aplica as colunas calculadas necessárias para o dashboard.
        Também filtra falsos positivos (quem já está matriculado).
        """
        # Inicializa set vazio se for None para evitar erro
        if set_matriculados is None:
            set_matriculados = set()

        # Retorna DF vazio se não houver dados de entrada
        if df_pendentes is None or df_pendentes.empty:
            return pd.DataFrame()

        logging.info("Business: Calculando indicadores de tempo e prioridade...")
        
        # 1. Armazena matriculados para o report usar depois
        self.ras_matriculados_atuais = set_matriculados
        self.cruzamento_realizado = True

        # 2. Remove Pendentes que JÁ estão Matriculados 
        if 'RA' in df_pendentes.columns:
            # .astype(str) garante que a comparação funcione mesmo se um lado for int e outro str
            df = df_pendentes[~df_pendentes['RA'].astype(str).isin(self.ras_matriculados_atuais)].copy()
        else:
            df = df_pendentes.copy()
        
        if df.empty:
            logging.warning("Business: Todos os pendentes já constam como matriculados ou lista vazia.")
            return df

        # 3. Limpeza final de nomes de Filial (Refinamento Visual)
        def limpar_nome_filial(row):
            # O .get evita erro se a coluna não existir
            marca = str(row.get('Marca', ''))
            filial = str(row.get('Filial', ''))
            if filial.startswith(marca):
                return filial[len(marca):].strip(" -|")
            return filial

        df['Filial'] = df.apply(limpar_nome_filial, axis=1)

        # 4. Cálculo de Dias e Prioridade (CRÍTICO PARA O EXCEL)
        hoje = pd.Timestamp.now().normalize()
        
        # Correção: Identifica qual coluna de data está disponível
        coluna_data = None
        if 'Data_Pendencia' in df.columns:
            coluna_data = 'Data_Pendencia'
        elif 'Data_Cadastro' in df.columns:
            coluna_data = 'Data_Cadastro'
        elif 'Data' in df.columns:
            coluna_data = 'Data'

        if coluna_data:
            # Converte para datetime garantindo tratamento de erros
            df[coluna_data] = pd.to_datetime(df[coluna_data], errors='coerce')
            # Calcula a diferença em dias
            df['Dias_Pendente'] = (hoje - df[coluna_data]).dt.days.fillna(0).astype(int)
        else:
            # Fallback se não achar data nenhuma
            logging.warning("Nenhuma coluna de data encontrada para calcular Dias_Pendente.")
            df['Dias_Pendente'] = 0

        # Regra de Prioridade Visual
        conditions = [(df['Dias_Pendente'] > 15), (df['Dias_Pendente'] >= 7)]
        choices = ['Crítico', 'Atenção']
        df['Status_Prioridade'] = np.select(conditions, choices, default='Novo')

        # 5. Ordenação para o relatório sair bonito
        cols_ordenacao = [c for c in ['Marca', 'Filial', 'Aluno'] if c in df.columns]
        if cols_ordenacao:
            df.sort_values(by=cols_ordenacao, inplace=True)

        logging.info(f"Business: {len(df)} pendências reais identificadas após cruzamento.")
        return df
