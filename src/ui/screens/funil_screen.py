import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from engine import FunnelEngine
import pandas as pd
import threading

class MonitoringScreen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent", corner_radius=15) 
        self.engine = FunnelEngine()
        self.full_df = None
        self.controller = controller

        # Layout Principal (Grid) 
        # Coluna 0: Sidebar (Fixo)
        # Coluna 1: Conteúdo (Expansível)
        self.grid_columnconfigure(0, weight=0, minsize=320) 
        self.grid_columnconfigure(1, weight=1)
        
        # Linha 0: Header (Botão) 
        # Linha 1: ScrollFrame
        self.grid_rowconfigure(0, weight=0) 
        self.grid_rowconfigure(1, weight=1)

        self.setup_sidebar_filters()
        self.setup_main_area()

    def setup_sidebar_filters(self):
        self.sidebar = ctk.CTkFrame(self, fg_color="#ffffff", corner_radius=15)
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 10), pady=0)
        
        # Título Sidebar
        lbl_title = ctk.CTkLabel(self.sidebar, text="ANÁLISE DE PIPELINE", 
                                 text_color="#2c3e50", font=("Roboto", 16, "bold"))
        lbl_title.pack(pady=(25, 15))
        
        # Filtros
        self.combo_marca = ctk.CTkComboBox(self.sidebar, values=["Todas"], command=self.apply_filters,
                                           fg_color="#ecf0f1", text_color="#2c3e50", 
                                           button_color="#2980b9", button_hover_color="#3498db",
                                           dropdown_fg_color="#ffffff", dropdown_text_color="#2c3e50",
                                           width=280)
        self.combo_marca.pack(pady=5, padx=20)
        
        self.combo_unidade = ctk.CTkComboBox(self.sidebar, values=["Todas"], command=self.apply_filters,
                                             fg_color="#ecf0f1", text_color="#2c3e50", 
                                             button_color="#2980b9", button_hover_color="#3498db",
                                             dropdown_fg_color="#ffffff", dropdown_text_color="#2c3e50",
                                             width=280)
        self.combo_unidade.pack(pady=5, padx=20)

        # Container dos Gráficos (Expande para preencher o resto da sidebar)
        self.chart_container = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.chart_container.pack(fill="both", expand=True, pady=(20, 10), padx=10)

    def setup_main_area(self):
        # Header (Botão Consultar) 
        header = ctk.CTkFrame(self, fg_color="transparent", height=50)
        header.grid(row=0, column=1, sticky="ew", padx=0, pady=(15, 10))
        header.pack_propagate(False) 
        
        self.btn_consult = ctk.CTkButton(header, text="Consultar DB", 
                                         font=("Roboto", 12, "bold"),
                                         fg_color="#e67e22", hover_color="#d35400",
                                         height=36, width=150,
                                         command=self.start_consultation_thread)
        self.btn_consult.pack(side="right", padx=10)

        # Área Scrollável 
        self.scroll_frame = ctk.CTkScrollableFrame(self, label_text="Unidades Filtradas", 
                                                   label_text_color="#2c3e50",
                                                   label_font=("Roboto", 14, "bold"),
                                                   fg_color="transparent") 
        self.scroll_frame.grid(row=1, column=1, sticky="nsew", padx=0, pady=(0, 10))
        
        # Ajuste de velocidade do scroll se necessário
        # self.scroll_frame._scrollbar.configure(width=16) 

    def start_consultation_thread(self):
        self.btn_consult.configure(state="disabled", text="Processando...")
        thread = threading.Thread(target=self.run_query, daemon=True)
        thread.start()

    def run_query(self):
        try:
            # Assumindo que engine já trata conexão
            df = self.engine.generate_full_report()
            self.after(0, self.update_ui_with_data, df)
        except Exception as e:
            print(f"Erro na consulta: {e}")
            self.after(0, lambda: self.btn_consult.configure(state="normal", text="Consultar DB"))

    def update_ui_with_data(self, df):
        if df is not None and not df.empty:
            self.full_df = df
            
            # Atualiza combos (Lógica segura para pandas)
            try:
                marcas_list = df['unidade'].apply(self.engine.extract_marca).unique().tolist()
                marcas = ["Todas"] + sorted([str(x) for x in marcas_list])
            except:
                marcas = ["Todas"]

            try:
                unid_list = df['unidade'].unique().tolist()
                unidades = ["Todas"] + sorted([str(x) for x in unid_list])
            except:
                unidades = ["Todas"]

            self.combo_marca.configure(values=marcas)
            self.combo_marca.set("Todas")
            
            self.combo_unidade.configure(values=unidades)
            self.combo_unidade.set("Todas")
            
            self.apply_filters()
        else:
            print("Nenhum dado retornado.")
        
        self.btn_consult.configure(state="normal", text="Consultar DB")

    def plot_funnels(self, data):
        plt.close('all') 
        for widget in self.chart_container.winfo_children():
            widget.destroy()

        plt.style.use('default') 
        
        # DPI ajustado para telas comuns
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(3.2, 5.5), dpi=100)
        fig.patch.set_facecolor('none') 
        fig.patch.set_alpha(0.0)

        text_color = "#2c3e50"
        bar_color = "#2980b9"

        # Gráfico 1: Barras 
        etapas = ["Leads", "Contatos", "Agend.", "Visitas", "Matric."]
        valores = [
            data.get('Leads', 0), 
            data.get('Contato Produtivo', 0), 
            data.get('Visita Agendada', 0), 
            data.get('Visita Realizada', 0), 
            data.get('Matricula', 0)
        ]
        
        bars = ax1.barh(etapas, valores, color=bar_color, height=0.6)
        ax1.invert_yaxis()
        
        ax1.set_title("Volume Acumulado", color=text_color, fontsize=10, fontweight='bold', pad=10)
        ax1.tick_params(axis='y', colors=text_color, labelsize=8)
        ax1.tick_params(axis='x', colors=text_color, labelsize=7)
        
        for spine in ax1.spines.values():
            spine.set_visible(False)
            
        ax1.bar_label(bars, fmt='{:,.0f}', padding=3, color=text_color, fontsize=7, fontweight='bold')

        # Gráfico 2: Donut 
        cohort_labels = ["Lead", "Agend", "Visita", "Negoc"]
        cohort_vals = [
            data.get('Inertes em Lead', 0), 
            data.get('Aguardando Agendamento', 0), 
            data.get('Aguardando Visita', 0), 
            data.get('Em Negociação', 0)
        ]
        colors_pie = ['#bdc3c7', '#f1c40f', '#e67e22', '#3498db']
        
        if sum(cohort_vals) > 0:
            wedges, texts, autotexts = ax2.pie(cohort_vals, labels=cohort_labels, autopct='%1.0f%%', 
                                              startangle=90, colors=colors_pie, pctdistance=0.80,
                                              textprops={'color': text_color, 'fontsize': 8})
            
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_weight('bold')
                autotext.set_fontsize(7)

            centre_circle = plt.Circle((0,0), 0.65, fc='white')
            fig.gca().add_artist(centre_circle)
            ax2.set_title("Status Atual", color=text_color, fontsize=10, fontweight='bold', pad=10)
        else:
            ax2.text(0.5, 0.5, "Sem dados", ha='center', va='center', color=text_color)
            ax2.axis('off')

        plt.subplots_adjust(left=0.20, right=0.95, top=0.92, bottom=0.05, hspace=0.3)
        
        ax1.set_facecolor('none')
        ax2.set_facecolor('none')

        canvas = FigureCanvasTkAgg(fig, master=self.chart_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        canvas.get_tk_widget().configure(bg='#ffffff', highlightthickness=0)

    def apply_filters(self, _=None):
        if self.full_df is None: return
        df = self.full_df.copy()
        
        marca = self.combo_marca.get()
        unid = self.combo_unidade.get()

        if marca != "Todas":
            df = df[df['unidade'].apply(lambda x: self.engine.extract_marca(x)) == marca]
        if unid != "Todas":
            df = df[df['unidade'] == unid]

        # Correção segura para soma de numéricos
        numeric_cols = df.select_dtypes(include='number').columns
        total_filtrado = df[numeric_cols].sum().to_dict()
        
        self.plot_funnels(total_filtrado)
        self.render_cards(df)

    def render_cards(self, df):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
            
        # Imports locais mantidos conforme original
        from src.ui.components.info_card import InfoCard
        from src.utils.report_handler import ReportHandler
        
        def export_single(data_row):
             safe_name = str(data_row.get('unidade', 'relatorio')).replace(" ", "_")
             ReportHandler.gerar_excel_individual(data_row, f"Relatorio_{safe_name}.xlsx")

        for _, row in df.iterrows():
            card_data = row.to_dict()
            card = InfoCard(self.scroll_frame, data=card_data, on_excel_click=export_single)
            card.pack(fill="x", padx=5, pady=5)
