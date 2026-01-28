import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from engine import FunnelEngine
import pandas as pd
import threading

class MonitoringScreen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.engine = FunnelEngine()
        self.full_df = None  # Dados brutos para filtros
        
        # Configuração de Grid
        self.grid_columnconfigure(1, weight=1) # Coluna dos Cards
        self.grid_rowconfigure(1, weight=1)

        self.setup_sidebar_filters()
        self.setup_main_area()

    def setup_sidebar_filters(self):
        """Lado esquerdo com gráficos e filtros de marca"""
        self.sidebar = ctk.CTkFrame(self, width=350)
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=10, pady=10)
        
        ctk.CTkLabel(self.sidebar, text="ANÁLISE DE PIPELINE", font=("Roboto", 16, "bold")).pack(pady=10)
        
        # Filtros
        self.combo_marca = ctk.CTkComboBox(self.sidebar, values=["Todas"], command=self.apply_filters)
        self.combo_marca.pack(pady=5, padx=20, fill="x")
        
        self.combo_unidade = ctk.CTkComboBox(self.sidebar, values=["Todas"], command=self.apply_filters)
        self.combo_unidade.pack(pady=5, padx=20, fill="x")

        # Container para os Gráficos
        self.chart_container = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.chart_container.pack(fill="both", expand=True, pady=10)

    def setup_main_area(self):
        """Área superior de botões e área de scroll de cards"""
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=1, sticky="ew", padx=10, pady=(10, 0))
        
        self.btn_consult = ctk.CTkButton(header, text="Consultar DB", command=self.start_consultation_thread)
        self.btn_consult.pack(side="left", padx=5)

        self.scroll_frame = ctk.CTkScrollableFrame(self, label_text="Unidades Filtradas")
        self.scroll_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)

    def start_consultation_thread(self):
        """Cria uma thread para buscar os dados sem travar a UI."""
        self.btn_consult.configure(state="disabled", text="Buscando...")
        thread = threading.Thread(target=self.run_query, daemon=True)
        thread.start()

    def run_query(self):
        """Executa a consulta pesada (chamada pelo thread)."""
        try:
            df = self.engine.generate_full_report()
            # Retorna para a thread principal para atualizar a tela
            self.after(0, self.update_ui_with_data, df)
        except Exception as e:
            print(f"Erro na consulta: {e}")
            self.after(0, lambda: self.btn_consult.configure(state="normal", text="Consultar DB"))

    def update_ui_with_data(self, df):
        """Recebe os dados e atualiza os componentes da tela."""
        if df is not None and not df.empty:
            self.full_df = df
            
            # Atualiza lista de Marcas
            marcas = ["Todas"] + sorted(list(df['unidade'].apply(self.engine.extract_marca).unique()))
            self.combo_marca.configure(values=marcas)
            
            # Atualiza lista de Unidades
            unidades = ["Todas"] + sorted(df['unidade'].unique().tolist())
            self.combo_unidade.configure(values=unidades)

            self.apply_filters()
        
        self.btn_consult.configure(state="normal", text="Consultar DB")

    def plot_funnels(self, data):
        """Gera os dois gráficos empilhados"""
        for widget in self.chart_container.winfo_children():
            widget.destroy()

        # Ajuste de cores para o tema escuro do CTK
        plt.style.use('dark_background')
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(4, 8), tight_layout=True)
        fig.patch.set_facecolor('#2b2b2b') 

        # 1. Gráfico Acumulado (Volume)
        etapas = ["Leads", "Contatos", "Agend.", "Visitas", "Matric."]
        # Verificação de segurança para chaves existentes
        valores = [
            data.get('Leads', 0), 
            data.get('Contato Produtivo', 0), 
            data.get('Visita Agendada', 0), 
            data.get('Visita Realizada', 0), 
            data.get('Matricula', 0)
        ]
        
        ax1.barh(etapas, valores, color='#2980b9')
        ax1.set_title("Volume Acumulado", color="white", fontsize=10)
        ax1.tick_params(axis='both', labelsize=8)

        # 2. Gráfico de Cohort (Estoque Atual)
        cohort_labels = ["Lead", "Agend", "Visita", "Negoc"]
        cohort_vals = [
            data.get('Inertes em Lead', 0), 
            data.get('Aguardando Agendamento', 0), 
            data.get('Aguardando Visita', 0), 
            data.get('Em Negociação', 0)
        ]
        
        if sum(cohort_vals) > 0:
            ax2.pie(cohort_vals, labels=cohort_labels, autopct='%1.1f%%', textprops={'size': 8})
            ax2.set_title("Onde os Leads estão parados", color="white", fontsize=10)
        else:
            ax2.text(0.5, 0.5, "Sem dados de Cohort", ha='center', va='center')

        canvas = FigureCanvasTkAgg(fig, master=self.chart_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def apply_filters(self, _=None):
        """Filtra o DataFrame e atualiza cards e gráficos"""
        if self.full_df is None: return

        df = self.full_df.copy()
        marca = self.combo_marca.get()
        unid = self.combo_unidade.get()

        if marca != "Todas":
            df = df[df['unidade'].apply(lambda x: self.engine.extract_marca(x)) == marca]
        
        if unid != "Todas":
            df = df[df['unidade'] == unid]

        # Soma os dados para o gráfico lateral
        total_filtrado = df.select_dtypes(include='number').sum()
        self.plot_funnels(total_filtrado)
        
        self.render_cards(df)

    def render_cards(self, df):
        """Renderiza a lista de unidades no scroll frame."""
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        for _, row in df.iterrows():
            card = ctk.CTkFrame(self.scroll_frame, fg_color="#f0f0f0")
            card.pack(fill="x", padx=10, pady=5)
            
            lbl_unidade = ctk.CTkLabel(card, text=row['unidade'], font=("Roboto", 13, "bold"), text_color="black")
            lbl_unidade.pack(side="left", padx=15, pady=10)

            lbl_matricula = ctk.CTkLabel(card, text=f"Matrículas: {row['Matricula']}", text_color="#1a5276")
            lbl_matricula.pack(side="right", padx=15)