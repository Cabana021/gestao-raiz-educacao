import pandas as pd
import os
import glob
import logging
import time
from datetime import datetime

class PendenciaReporter:
    def __init__(self, config, pasta_historico_raiz):
        self.config = config
        self.pasta_historico_raiz = pasta_historico_raiz

    def gerar_por_marca(self, df_atual, pasta_destino, business_obj):
        """Itera sobre as marcas e gera os relatórios individuais."""
        if df_atual is None or df_atual.empty:
            logging.warning("Nenhum dado para gerar relatório.")
            return

        marcas_unicas = df_atual['Marca'].unique()
        
        for marca in marcas_unicas:
            nome_marca_limpo = str(marca).strip().replace(" ", "_").replace("/", "-")
            
            # Gerenciamento de Pastas e Histórico
            pasta_hist_marca = os.path.join(self.pasta_historico_raiz, nome_marca_limpo)
            os.makedirs(pasta_hist_marca, exist_ok=True)

            # Filtra dados da escola
            df_escola = df_atual[df_atual['Marca'] == marca].copy()
            
            # Carrega Histórico Anterior (para o comparativo do Dashboard)
            df_ant = self._carregar_historico_recente(pasta_hist_marca)

            # Gera Arquivo
            data_str = datetime.now().strftime("%Y-%m-%d")
            caminho_relatorio = os.path.join(pasta_destino, f"Pendencias_{nome_marca_limpo}_{data_str}.xlsx")
            
            # Chama a função completa de exportação
            sucesso = self._exportar_excel(df_escola, df_ant, caminho_relatorio, marca, business_obj)

            # Salva novo histórico se deu tudo certo
            if sucesso:
                self._salvar_historico(df_escola, pasta_hist_marca, nome_marca_limpo)

    def _carregar_historico_recente(self, pasta):
        """Busca o arquivo mais recente na pasta de histórico."""
        arquivos = glob.glob(os.path.join(pasta, "*.xlsx"))
        if not arquivos:
            return pd.DataFrame()
        
        try:
            arquivo_recente = max(arquivos, key=os.path.getctime)
            df = pd.read_excel(arquivo_recente)
            if 'RA' in df.columns:
                df['RA'] = df['RA'].astype(str).str.strip()
            return df
        except Exception:
            return pd.DataFrame()

    def _salvar_historico(self, df, pasta, nome_marca):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        caminho = os.path.join(pasta, f"DB_Pend_{nome_marca}_{timestamp}.xlsx")
        try:
            df.to_excel(caminho, index=False)
        except Exception as e:
            logging.error(f"Erro ao salvar histórico DB: {e}")

    def _exportar_excel(self, df_atual, df_anterior, caminho, nome_escola, business_obj):
        """
        Gera relatório com dashboard. 
        Contém toda a lógica visual.
        """
        
        # 1: Configuração de cores (Lê do config injetado)
        colors = self.config.get('cores_excel', {})
        c_brand = colors.get('brand_primary', '#203764')       
        c_brand_light = colors.get('brand_secondary', '#4472C4') 
        c_pos_bg = colors.get('positivo_bg', '#C6EFCE')
        c_pos_font = colors.get('positivo_font', '#006100')
        c_neg_bg = colors.get('negativo_bg', '#FFC7CE')
        c_neg_font = colors.get('negativo_font', '#9C0006')
        c_alert_bg = colors.get('alerta_bg', '#FFEB9C')
        c_alert_font = colors.get('alerta_font', '#9C5700')
        c_neu_bg = colors.get('neutro_bg', '#E6E6E6')
        c_neu_font = colors.get('neutro_font', '#203764')

        # 2: Cálculo dos dados (Comparativo)
        qtd_anterior = 0
        qtd_novos = 0
        qtd_convertidos = 0 
        qtd_desistentes = 0
        
        if not df_anterior.empty:
            ras_antigos = set(df_anterior['RA'].astype(str).str.strip())
            ras_atuais = set(df_atual['RA'].astype(str).str.strip())
            
            qtd_anterior = len(ras_antigos)
            qtd_novos = len(ras_atuais - ras_antigos)
            
            ras_resolvidos = ras_antigos - ras_atuais
            
            # Usa os dados do objeto de regras.py
            if business_obj.cruzamento_realizado:
                for ra in ras_resolvidos:
                    if ra in business_obj.ras_matriculados_atuais:
                        qtd_convertidos += 1
                    else:
                        qtd_desistentes += 1
            else:
                qtd_desistentes = len(ras_resolvidos)
        else:
            qtd_novos = len(df_atual)

        df = df_atual.fillna('')
        
        # 3: Dataframes Auxiliares para o Dashboard
        
        # Tempo de Espera
        bins = [0, 30, 90, 9999]
        labels = ['Recente (0-30d)', 'Médio (31-90d)', 'Crítico (>90d)']
        df['Faixa_Dias'] = pd.cut(df['Dias_Pendente'], bins=bins, labels=labels, right=False)
        resumo_aging = df.groupby('Faixa_Dias', observed=False).size().reset_index(name='Qtd')

        # Status
        resumo_status = df.groupby('Status_Prioridade').size().reset_index(name='Qtd')

        # Ordena os anos letivos
        ordem_educacional = [
            'INFANTIL', 'PRÉ-ESCOLA', '1º ANO', '2º ANO', '3º ANO', '4º ANO', 
            '5º ANO', '6º ANO', '7º ANO', '8º ANO', '9º ANO', 
            '1ª SÉRIE', '2ª SÉRIE', '3ª SÉRIE'
        ]
        mapa_ordem = {serie: i for i, serie in enumerate(ordem_educacional)}

        # Pivot Table
        resumo_serie_pivot = df.pivot_table(
            index='Série', columns='Tipo_Matricula', values='RA', aggfunc='count', fill_value=0
        ).reset_index()

        for col in ['REMATRÍCULA', 'MATRÍCULA']:
            if col not in resumo_serie_pivot.columns: resumo_serie_pivot[col] = 0
        
        resumo_serie_pivot['Total'] = resumo_serie_pivot['REMATRÍCULA'] + resumo_serie_pivot['MATRÍCULA']
        
        # Normaliza e ordena
        resumo_serie_pivot['Série_Norm'] = (
            resumo_serie_pivot['Série']
            .astype(str).str.strip().str.upper()
            .str.replace('°', 'º')
            .str.replace('  ', ' ')
        )
        resumo_serie_pivot['Ordem_Aux'] = resumo_serie_pivot['Série_Norm'].map(mapa_ordem).fillna(99)
        resumo_serie_pivot.sort_values(by=['Ordem_Aux', 'Série_Norm'], ascending=[True, True], inplace=True)
        resumo_serie_pivot.drop(columns=['Série_Norm', 'Ordem_Aux'], inplace=True)

        # Totais Gerais
        total_pendencias = len(df)
        kpi_remat = len(df[df['Tipo_Matricula'].str.upper().str.strip() == 'REMATRÍCULA'])
        kpi_matr = len(df[df['Tipo_Matricula'].str.upper().str.strip() == 'MATRÍCULA'])
        qtd_zombies = df[df['Dias_Pendente'] > 90].shape[0]

        try:
            writer = pd.ExcelWriter(caminho, engine='xlsxwriter')
            wb = writer.book

            # Estilos
            fmt_header = wb.add_format({'bold': True, 'font_color': 'white', 'bg_color': c_brand, 'border': 1, 'align': 'center', 'valign': 'vcenter'})
            fmt_dash_title = wb.add_format({'bold': True, 'font_size': 16, 'font_color': c_brand, 'align': 'left'})
            fmt_table_header = wb.add_format({'bold': True, 'font_color': 'white', 'bg_color': c_brand_light, 'border': 1, 'align': 'center'})
            
            fmt_critico = wb.add_format({'bg_color': c_neg_bg, 'font_color': c_neg_font, 'border': 1, 'align': 'center'})
            fmt_atencao = wb.add_format({'bg_color': c_alert_bg, 'font_color': c_alert_font, 'border': 1, 'align': 'center'})
            fmt_novo = wb.add_format({'bg_color': c_pos_bg, 'font_color': c_pos_font, 'border': 1, 'align': 'center'})
            
            fmt_familia_a = wb.add_format({'bg_color': '#FFFFFF', 'border': 1, 'valign': 'vcenter'})
            fmt_familia_b = wb.add_format({'bg_color': '#F2F2F2', 'border': 1, 'valign': 'vcenter'})
            fmt_manual = wb.add_format({'bg_color': '#FFFFE0', 'border': 1})

            # Aba 1: Lista de Ação
            ws_lista = wb.add_worksheet('Lista de Ação')
            ws_lista.hide_gridlines(2)
            
            headers_lista = ['Status', 'Dias Pendentes', 'Marca', 'Filial', 'RA', 'Tipo Matricula', 'Nome do Aluno', 'Série', 'Responsável', 'Turno', 'CPF Responsável']
            for col, val in enumerate(headers_lista):
                ws_lista.write(0, col, val, fmt_header)
            ws_lista.write(0, 11, "Ação da Secretaria", fmt_header)

            cpf_ant = None
            cor_base = fmt_familia_a
            cols_export = ['Status_Prioridade', 'Dias_Pendente', 'Marca', 'Filial', 'RA', 'Tipo_Matricula', 'Aluno', 'Série', 'Responsável', 'Turno', 'CPF_Resp']

            for i, linha in enumerate(df[cols_export].itertuples(index=False)):
                row_idx = i + 1
                if linha.CPF_Resp != cpf_ant:
                    cor_base = fmt_familia_b if cor_base == fmt_familia_a else fmt_familia_a
                    cpf_ant = linha.CPF_Resp
                
                bg_status = fmt_critico if linha.Status_Prioridade == 'Crítico' else (fmt_atencao if linha.Status_Prioridade == 'Atenção' else fmt_novo)
                
                ws_lista.write(row_idx, 0, linha.Status_Prioridade, bg_status)
                ws_lista.write(row_idx, 1, linha.Dias_Pendente, cor_base)
                ws_lista.write(row_idx, 2, linha.Marca, cor_base)
                ws_lista.write(row_idx, 3, linha.Filial, cor_base)
                ws_lista.write(row_idx, 4, linha.RA, cor_base)
                ws_lista.write(row_idx, 5, linha.Tipo_Matricula, cor_base)
                ws_lista.write(row_idx, 6, linha.Aluno, cor_base)
                ws_lista.write(row_idx, 7, linha.Série, cor_base)
                ws_lista.write(row_idx, 8, linha.Responsável, cor_base)
                ws_lista.write(row_idx, 9, linha.Turno, cor_base)
                ws_lista.write(row_idx, 10, linha.CPF_Resp, cor_base)
                ws_lista.write(row_idx, 11, "", fmt_manual)

            ws_lista.autofilter(0, 0, len(df), 10)
            
            # Lista das colunas que você escreveu no Excel
            colunas_para_ajustar = [
                'Status_Prioridade', 'Dias_Pendente', 'Marca', 'Filial', 'RA', 
                'Tipo_Matricula', 'Aluno', 'Série', 'Responsável', 'Turno', 'CPF_Resp'
            ]

            for i, col_name in enumerate(colunas_para_ajustar):
                # 1. Calcula o tamanho do maior texto nesta coluna 
                max_len_dados = 0
                if not df.empty and col_name in df.columns:
                    # Converte para string e pega o tamanho máximo
                    max_len_dados = df[col_name].astype(str).map(len).max()
                
                # 2. Calcula o tamanho do Cabeçalho (ex: "Nome do Aluno")
                len_header = len(headers_lista[i])

                # 3. Define a largura: pega o maior entre (Dados vs Cabeçalho) e soma +2 de margem
                largura_final = min(max(max_len_dados, len_header) + 2, 50)

                # Aplica a largura na coluna específica
                ws_lista.set_column(i, i, largura_final)

            # Coluna L (Ação da Secretaria) deixamos fixa e larga manualmente
            ws_lista.set_column(11, 11, 40)

            # Aba 2: Resumo
            ws_dash = wb.add_worksheet('Resumo')
            ws_dash.hide_gridlines(2)

            # Define o GRID
            COL_LEFT = 1      # B
            COL_MID = 5       # F
            
            ROW_TITLE = 1
            ROW_KPI = 4
            ROW_FLOW = 10     
            ROW_TABLE = 18    
            
            # Formatações Específicas
            fmt_head_remat = wb.add_format({'bold': True, 'align': 'center', 'bg_color': c_brand, 'font_color': 'white', 'border': 1})
            fmt_head_matr = wb.add_format({'bold': True, 'align': 'center', 'bg_color': c_brand_light, 'font_color': 'white', 'border': 1})
            fmt_sub_num = wb.add_format({'bold': True, 'font_size': 22, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': c_neu_bg})
            fmt_kpi_box = wb.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'bg_color': c_neu_bg})
            fmt_kpi_num = wb.add_format({'bold': True, 'font_size': 24, 'color': c_brand, 'align': 'center', 'valign': 'vcenter', 'bg_color': c_neu_bg, 'border': 1})
            fmt_kpi_risk = wb.add_format({'bold': True, 'font_size': 24, 'color': c_neg_font, 'align': 'center', 'valign': 'vcenter', 'bg_color': c_neg_bg, 'border': 1})
            fmt_neutro = wb.add_format({'bold': True, 'color': c_neu_font, 'bg_color': c_neu_bg, 'border': 1, 'align': 'center'})
            fmt_sucesso = wb.add_format({'bold': True, 'color': c_pos_font, 'bg_color': c_pos_bg, 'border': 1, 'align': 'center'})
            fmt_perda = wb.add_format({'bold': True, 'color': c_neg_font, 'bg_color': c_neg_bg, 'border': 1, 'align': 'center'})

            # 1. Cabeçalho e KPIs
            ws_dash.merge_range(ROW_TITLE, COL_LEFT, ROW_TITLE, 8, f"Painel de Pendências - {nome_escola}", fmt_dash_title)
            ws_dash.merge_range(ROW_TITLE+1, COL_LEFT, ROW_TITLE+1, 8, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", wb.add_format({'italic': True, 'font_color': '#595959'}))

            def escrever_kpi(col, titulo, valor, formato_valor):
                ws_dash.merge_range(ROW_KPI, col, ROW_KPI, col+1, titulo, fmt_kpi_box)
                ws_dash.merge_range(ROW_KPI+1, col, ROW_KPI+3, col+1, valor, formato_valor)

            escrever_kpi(1, "TOTAL GERAL", total_pendencias, fmt_kpi_num)
            escrever_kpi(3, "REMATRÍCULA", kpi_remat, fmt_sub_num)
            escrever_kpi(5, "CAPTAÇÃO", kpi_matr, fmt_sub_num)
            style_zombie = fmt_kpi_risk if qtd_zombies > 0 else fmt_kpi_num
            escrever_kpi(7, "RISCO >90d", qtd_zombies, style_zombie)

            # 2. Fluxo 
            ws_dash.merge_range(ROW_FLOW, COL_LEFT, ROW_FLOW, COL_LEFT+4, "Fluxo de Resolução da Semana", fmt_table_header)
            
            headers_fluxo = ["Categoria", "Total", "Remat.", "Captação", "Status"]
            for i, h in enumerate(headers_fluxo):
                estilo = fmt_head_remat if h == "Remat." else (fmt_head_matr if h == "Captação" else fmt_header)
                ws_dash.write(ROW_FLOW+1, COL_LEFT+i, h, estilo)

            fluxo_dados = [
                ("Pendências Anterior", qtd_anterior, "-", "-", "Início", fmt_neutro),
                ("Novas Entradas (+)", qtd_novos, "-", "-", "Alerta", fmt_perda),
                ("Resolvidos/Saídas (-)", qtd_convertidos + qtd_desistentes, "-", "-", "Baixas", fmt_sucesso),
                ("SALDO ATUAL (=)", total_pendencias, kpi_remat, kpi_matr, "Fim", fmt_neutro),
            ]

            for i, (cat, total, r, m, status, fmt) in enumerate(fluxo_dados):
                row = ROW_FLOW + 2 + i
                ws_dash.write(row, COL_LEFT, cat, fmt_familia_a)
                ws_dash.write(row, COL_LEFT+1, total, fmt)
                ws_dash.write(row, COL_LEFT+2, r, fmt)
                ws_dash.write(row, COL_LEFT+3, m, fmt)
                ws_dash.write(row, COL_LEFT+4, status, fmt_familia_a)

            # 3. Bloco Principal 
            
            # Detalhamento por Série
            ws_dash.merge_range(ROW_TABLE, COL_LEFT, ROW_TABLE, COL_LEFT+3, "Detalhamento por Série", fmt_table_header)
            headers_serie = ["Série", "Total", "Remat.", "Matr."]
            for i, h in enumerate(headers_serie):
                ws_dash.write(ROW_TABLE+1, COL_LEFT+i, h, fmt_header)

            for idx, row in resumo_serie_pivot.iterrows():
                r = ROW_TABLE + 2 + idx
                ws_dash.write(r, COL_LEFT, row['Série'], fmt_familia_a)
                ws_dash.write(r, COL_LEFT+1, row['Total'], fmt_familia_a)
                ws_dash.write(r, COL_LEFT+2, row['REMATRÍCULA'], fmt_neutro)
                ws_dash.write(r, COL_LEFT+3, row['MATRÍCULA'], fmt_neutro)

            # Direita: Tabelas de Apoio 
            
            # Tempo de Espera
            ws_dash.merge_range(ROW_TABLE, COL_MID, ROW_TABLE, COL_MID+1, "Tempo de Espera", fmt_table_header)
            for i, row in resumo_aging.iterrows():
                ws_dash.write(ROW_TABLE+1+i, COL_MID, row['Faixa_Dias'], fmt_familia_a)
                ws_dash.write(ROW_TABLE+1+i, COL_MID+1, row['Qtd'], fmt_familia_a)

            # Prioridade 
            row_aging_end = ROW_TABLE + 1 + len(resumo_aging)
            row_prio = row_aging_end + 0  
            
            ws_dash.merge_range(row_prio, COL_MID, row_prio, COL_MID+1, "Prioridade", fmt_table_header)
            for i, row in resumo_status.iterrows():
                bg = fmt_critico if row['Status_Prioridade'] == 'Crítico' else fmt_novo
                ws_dash.write(row_prio+1+i, COL_MID, row['Status_Prioridade'], bg)
                ws_dash.write(row_prio+1+i, COL_MID+1, row['Qtd'], fmt_familia_a)

            # 4. Gráfico
            ROW_CHART = ROW_TABLE + len(resumo_serie_pivot) + 4
            chart = wb.add_chart({'type': 'column', 'subtype': 'stacked'})

            chart.add_series({
                'name': 'Rematrícula',
                'categories': ['Resumo', ROW_TABLE+2, COL_LEFT, ROW_TABLE+1+len(resumo_serie_pivot), COL_LEFT],
                'values':     ['Resumo', ROW_TABLE+2, COL_LEFT+2, ROW_TABLE+1+len(resumo_serie_pivot), COL_LEFT+2],
                'fill':       {'color': c_brand}
            })
            chart.add_series({
                'name': 'Captação',
                'categories': ['Resumo', ROW_TABLE+2, COL_LEFT, ROW_TABLE+1+len(resumo_serie_pivot), COL_LEFT],
                'values':     ['Resumo', ROW_TABLE+2, COL_LEFT+3, ROW_TABLE+1+len(resumo_serie_pivot), COL_LEFT+3],
                'fill':       {'color': c_brand_light}
            })
            
            chart.set_title({'name': 'Distribuição: Rematrícula vs Captação'})
            chart.set_legend({'position': 'bottom'})
            
            ws_dash.insert_chart(ROW_CHART, COL_LEFT, chart, {'x_scale': 2.5, 'y_scale': 1.5})

            # 5. Diagnóstico Inteligente
            ROW_INSIGHT = ROW_CHART + 22 
            
            texto = "DIAGNÓSTICO AUTOMÁTICO:\n"
            if total_pendencias > 0:
                pct = int((kpi_matr / total_pendencias) * 100)
                if pct > 40:
                    texto += f"• ALERTA: {pct}% das pendências são Captação.\n"
                else:
                    texto += f"• Predomínio de Rematrícula ({100-pct}%).\n"
            if qtd_novos > 0:
                texto += f"• +{qtd_novos} novas pendências na semana.\n"
            
            # Seleciona o ano letivo com maior qtd de alunos pendentes
            if not resumo_serie_pivot.empty:
                idx_max = resumo_serie_pivot['Total'].idxmax()
                serie_max = resumo_serie_pivot.loc[idx_max, 'Série']
                texto += f"• Série mais impactada: {serie_max}."

            ws_dash.insert_textbox(ROW_INSIGHT, COL_LEFT, texto, {
                'width': 600, 'height': 80,
                'line': {'color': c_brand}, 'fill': {'color': '#FFFFE0'},
                'font': {'name': 'Calibri', 'size': 10}
            })

            ws_dash.set_column('A:A', 2)
            ws_dash.set_column('B:G', 18)
            ws_dash.set_column('H:J', 14)

            max_tentativas = 3
            for tentativa in range(max_tentativas):
                try:
                    writer.close()
                    logging.info(f"Relatório salvo: {caminho}")
                    return True
                except PermissionError:
                    if tentativa < max_tentativas - 1:
                        time.sleep(2)
                    else:
                        logging.error(f"ERRO: Feche o arquivo '{caminho}' e tente novamente.")
                        return False

        except Exception as e:
            logging.error(f"Erro Excel: {e}", exc_info=True)
            return False
