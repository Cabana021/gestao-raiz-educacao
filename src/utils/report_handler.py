import pandas as pd
import os
import logging
import re
from datetime import datetime

# Configuração de Log básico para debug
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GeradorRelatorio:
    """
    Classe responsável pela formatação complexa do Excel (Cores, Ordenação, Gráficos).
    Baseada no código original do report.py.
    """
    def __init__(self, business_config, aba_alvo):
        self.business_config = business_config
        self.aba_alvo = aba_alvo

    @staticmethod
    def extrair_raiz_metrica(nome_coluna):
        """Extrai o nome base da métrica removendo datas e sufixos de variação."""
        return re.split(r' \(| Var| Delta', nome_coluna)[0].strip()

    @staticmethod
    def extrair_data_coluna(nome_coluna):
        """Extrai objeto datetime de uma string de coluna (DD/MM ou DD/MM/AAAA)."""
        m = re.search(r'(\d{2}/\d{2}(?:/\d{4})?)', nome_coluna)
        if not m: return None
        
        data_str = m.group(1)
        try:
            if len(data_str) == 5:  # formato DD/MM
                dt = datetime.strptime(data_str, "%d/%m").replace(year=datetime.now().year)
                # Se a data for futura (ex: Dezembro) e estamos em Janeiro, ajusta ano anterior
                if dt > datetime.now() and dt.month > 9:
                    dt = dt.replace(year=dt.year - 1)
                return dt
            return datetime.strptime(data_str, "%d/%m/%Y")
        except:
            return None

    def gerar_output(self, df_analitico, df_dashboard, output_path):
        """Gera o Excel formatado."""
        logging.info(f"Criando relatório formatado em: {output_path}")

        config_report = self.business_config.copy()
        
        # Define título do dashboard se não existir
        nome_display = "Captação" if self.aba_alvo == "Captacao" else "Renovação"
        config_report.setdefault('titulos', {})['dashboard'] = f"Painel de {nome_display}"

        try:
            writer = pd.ExcelWriter(output_path, engine='xlsxwriter')
            wb = writer.book
            ws_name = 'Analise'

            # 1. Definição da Ordem das Colunas
            colunas_fixas = ["unidade", "Marca", "Filial"] # Ajustado para incluir 'unidade' que vem do engine
            
            ordem_taxas = [
                "% Lead -> Prod",        
                "% Prod -> Agend",       
                "% Agend -> Visita",     
                "% Visita -> Matrícula", 
                "% Agend vs Lead",       
                "% Conversão Final",     
                "% Visita vs Lead",      
                "% Meta Atingida"        
            ]

            ordem_inteiros = [
                # Captação
                "Leads", 
                "Contato Produtivo", 
                "Visita Agendada", 
                "Visita Realizada", 
                "Matrícula", "Matrículas", # Aceita singular ou plural
                # Renovação
                "Elegíveis",
                "Renovados",
                "Tentativa Contato",
                "Não Renovado"
            ]

            def get_sort_key(nome_coluna):
                # Prioridade 1: Colunas Fixas
                if nome_coluna in colunas_fixas:
                    return (-1, colunas_fixas.index(nome_coluna) if nome_coluna in colunas_fixas else 99, datetime.min, 0)

                raiz = self.extrair_raiz_metrica(nome_coluna)
                eh_variacao = 1 if ("Var" in nome_coluna or "Delta" in nome_coluna) else 0
                
                if eh_variacao:
                    data = datetime.max
                else:
                    data = self.extrair_data_coluna(nome_coluna) or datetime.max

                # Prioridade 2: Taxas
                for i, taxa in enumerate(ordem_taxas):
                    if raiz.startswith(taxa) or taxa in raiz:
                        return (0, i, data, eh_variacao)

                # Prioridade 3: Inteiros (Leads, Matriculas, etc)
                for i, inteiro in enumerate(ordem_inteiros):
                    if raiz == inteiro:
                        return (1, i, data, eh_variacao)

                # Resto
                return (2, 999, data, eh_variacao)

            def ordenar_colunas_cluster(df):
                cols = df.columns.tolist()
                cols_ordenadas = sorted(cols, key=get_sort_key)
                return df[cols_ordenadas]

            # Renomeia colunas de Variações Delta (se houver)
            novos_nomes = {}
            for col in df_analitico.columns:
                if "Delta" not in col: continue
                raiz = self.extrair_raiz_metrica(col)
                # Lógica simplificada de delta se não houver histórico completo
                novos_nomes[col] = f"{raiz} Delta"

            df_analitico.rename(columns=novos_nomes, inplace=True)
            
            # Aplica a ordenação
            df_analitico = ordenar_colunas_cluster(df_analitico)

            # 2. Escrita no Excel
            df_analitico.to_excel(writer, sheet_name=ws_name, index=False)
            ws = writer.sheets[ws_name]

            # Estilos
            style_colors = config_report.get('cores_excel', {})
            regras = config_report.get('regras_negocio', {})
            
            limite_positivo = regras.get('crescimento_minimo', 0.02)
            limite_negativo = regras.get('queda_critica', -0.02)

            # Formatos Excel
            fmt_header = wb.add_format({
                'bold': True, 'bg_color': '#203764', 'font_color': 'white',
                'border': 1, 'align': 'center', 'valign': 'vcenter'
            })
            fmt_num = wb.add_format({'num_format': '#,##0', 'border': 1, 'align': 'center'})
            fmt_pct = wb.add_format({'num_format': '0.0%', 'border': 1, 'align': 'center'})
            fmt_var_pct = wb.add_format({
                'num_format': '0.0%', 'border': 1, 'align': 'center', 'bold': True
            })
            fmt_var_num = wb.add_format({ 
                'num_format': '0.0', 'border': 1, 'align': 'center', 'bold': True
            })
            
            # Cores (Semáforo)
            fmt_green = wb.add_format({'bg_color': style_colors.get('positivo_bg', '#C6EFCE'), 'font_color': style_colors.get('positivo_font', '#006100')})
            fmt_red = wb.add_format({'bg_color': style_colors.get('negativo_bg', '#FFC7CE'), 'font_color': style_colors.get('negativo_font', '#9C0006')})
            fmt_yellow = wb.add_format({'bg_color': style_colors.get('alerta_bg', '#FFEB9C'), 'font_color': style_colors.get('alerta_font', '#9C5700')})

            ws.set_row(0, 30)
            last_row = len(df_analitico) + 1 # +1 por causa do header
        
            # 3. Loop de formatação de colunas
            for idx, col in enumerate(df_analitico.columns):
                ws.write(0, idx, col, fmt_header)
                largura = max(len(str(col)) + 2, 15)

                if "Var%" in col or "Delta" in col:
                    is_pct = "Var%" in col
                    ws.set_column(idx, idx, largura, fmt_var_pct if is_pct else fmt_var_num)

                    if is_pct:
                        ws.conditional_format(1, idx, last_row, idx, {'type': 'cell', 'criteria': '>', 'value': limite_positivo, 'format': fmt_green})
                        ws.conditional_format(1, idx, last_row, idx, {'type': 'cell', 'criteria': '<', 'value': limite_negativo, 'format': fmt_red})
                        ws.conditional_format(1, idx, last_row, idx, {'type': 'cell', 'criteria': 'between', 'minimum': limite_negativo, 'maximum': limite_positivo, 'format': fmt_yellow})
                    else:
                        ws.conditional_format(1, idx, last_row, idx, {'type': 'cell', 'criteria': '>', 'value': 0, 'format': fmt_green})
                        ws.conditional_format(1, idx, last_row, idx, {'type': 'cell', 'criteria': '<', 'value': 0, 'format': fmt_red})

                elif "%" in col or "Taxa" in col:
                    ws.set_column(idx, idx, largura, fmt_pct)
                    ws.conditional_format(1, idx, last_row, idx, {
                        'type': 'data_bar', 'bar_color': '#B1D6BC', 'bar_solid': True,
                        'min_type': 'num', 'min_value': 0, 'max_type': 'num', 'max_value': 1
                    })

                elif col not in colunas_fixas:
                    ws.set_column(idx, idx, largura, fmt_num)
                else:
                    ws.set_column(idx, idx, largura)

            ws.freeze_panes(1, 1)
            
            # Gera Dashboard (Aba Gráfica)
            self._criar_dashboard(writer, wb, df_dashboard, config_report)

            writer.close()
            logging.info("Relatório Excel gerado com sucesso.")
            
            # Tenta abrir o arquivo automaticamente
            try:
                os.startfile(output_path)
            except:
                pass
            return True

        except Exception as e:
            logging.error(f"Erro ao gerar relatório Excel: {e}", exc_info=True)
            return False

    def _criar_dashboard(self, writer, wb, df_marcas, config):
        """Método privado para criar a aba de dashboard visual."""
        nome_aba_dados = 'Dados_Graficos'
        # Limpeza de colunas indesejadas
        cols_limpas = [c for c in df_marcas.columns if "Unnamed" not in c and c != "unidade"]
        # Mantém a coluna unidade se ela for a identificadora
        if "unidade" in df_marcas.columns:
            cols_limpas.insert(0, "unidade")
            
        df_clean = df_marcas[cols_limpas].copy()
        
        # Se existir coluna 'unidade', renomear para 'Marca' para o gráfico entender
        if "unidade" in df_clean.columns:
            df_clean.rename(columns={"unidade": "Marca"}, inplace=True)

        df_clean.to_excel(writer, sheet_name=nome_aba_dados, index=False)

        ws_dash = wb.add_worksheet('Dashboard')
        ws_dash.hide_gridlines(2)

        fmt_title = wb.add_format({
            'bold': True, 'font_size': 22, 'font_color': '#203764', 'font_name': 'Segoe UI'
        })

        titulo_dash = config.get('titulos', {}).get('dashboard', "Dashboard")
        ws_dash.write('B2', titulo_dash, fmt_title)

        num_marcas = len(df_clean)
        if num_marcas == 0: return

        chart_width = 1000
        chart_height = max(350, 120 + (num_marcas * 50))
        gap_rows = int(chart_height / 18) + 4
        start_row = 4

        cols_para_plotar = [c for c in df_clean.columns if c != "Marca" and "Var%" not in c and c not in ["Filial"]]
        kpis_unicos = sorted(list(set(c.split(" (")[0] for c in cols_para_plotar)))
        
        # Ordem de plotagem
        ordem_graficos = [
            "Leads", "Contato Produtivo", "Visita Agendada", "Visita Realizada", "Matrícula"
        ]
        
        # Função auxiliar para ordenar KPIs
        def sort_kpis(k):
            for i, o in enumerate(ordem_graficos):
                if k.startswith(o): return i
            return 999

        kpis_unicos.sort(key=sort_kpis)

        for idx, kpi in enumerate(kpis_unicos):
            chart = wb.add_chart({'type': 'bar'})
            cols_kpi = [c for c in cols_para_plotar if c.startswith(kpi)] 

            if not cols_kpi: continue
            
            # Formatação do eixo
            is_pct = any(x in kpi for x in ['%', 'Taxa', 'Conv'])
            mask_eixo = '0%' if is_pct else '#,##0'

            # Referência aos dados: [sheetname, first_row, first_col, last_row, last_col]
            # A coluna 0 é a Categoria (Marca)
            cat_formula = [nome_aba_dados, 1, 0, num_marcas, 0]

            for nome_coluna in cols_kpi:
                try:
                    col_idx = df_clean.columns.get_loc(nome_coluna)
                    legenda = nome_coluna
                    
                    chart.add_series({
                        'name': legenda,
                        'categories': cat_formula,
                        'values': [nome_aba_dados, 1, col_idx, num_marcas, col_idx],
                        'fill': {'color': '#203764'},
                        'overlap': -20, 'gap': 50,
                        'data_labels': {
                            'value': True, 'num_format': mask_eixo,
                            'font': {'bold': True, 'color': '#404040', 'size': 9, 'name': 'Segoe UI'},
                            'position': 'outside_end'
                        }
                    })
                except:
                    continue

            chart.set_title({'name': kpi})
            chart.set_legend({'position': 'top'})
            chart.set_chartarea({'border': {'none': True}})
            chart.set_size({'width': chart_width, 'height': chart_height})

            ws_dash.insert_chart(f'B{start_row + (idx * gap_rows)}', chart)


class ReportHandler:
    """
    Classe Wrapper (Ponte) para conectar a UI do Sistema ao GeradorRelatorio complexo.
    """
    @staticmethod
    def gerar_excel_consolidado(df_dados, nome_arquivo="Relatorio_Geral.xlsx"):
        """
        Recebe o DataFrame direto do Engine, configura as regras de negócio
        e chama o gerador de relatório.
        """
        if df_dados is None or df_dados.empty:
            logging.warning("Tentativa de gerar Excel com DataFrame vazio.")
            return False
            
        # Configuração padrão (Hardcoded aqui para facilitar, já que não temos config externa)
        business_config = {
            "cores_excel": {
                "positivo_bg": "#C6EFCE", "positivo_font": "#006100",
                "negativo_bg": "#FFC7CE", "negativo_font": "#9C0006",
                "alerta_bg": "#FFEB9C", "alerta_font": "#9C5700"
            },
            "regras_negocio": {"crescimento_minimo": 0.02, "queda_critica": -0.02},
            "titulos": {"dashboard": "Painel de Monitoramento 2026"}
        }

        # Prepara o DataFrame para exportação
        df_export = df_dados.copy()
        
        # Instancia a classe que faz o trabalho pesado
        gerador = GeradorRelatorio(business_config, aba_alvo="Captacao")
        
        # Gera o arquivo (Analítico e Dashboard usam a mesma base neste caso)
        return gerador.gerar_output(df_export, df_export, nome_arquivo)

    @staticmethod
    def gerar_excel_individual(dados_dict, nome_arquivo):
        """
        Gera relatório para uma única linha (Filial/Marca) a partir de um dicionário.
        Usado pelo botão 'XLS' do card individual.
        """
        if not dados_dict:
            return False
            
        # Converte o dicionário único de volta para DataFrame
        df_unico = pd.DataFrame([dados_dict])
        
        return ReportHandler.gerar_excel_consolidado(df_unico, nome_arquivo)