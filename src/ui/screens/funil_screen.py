import customtkinter as ctk
from PIL import Image
import os
import pandas as pd
from datetime import datetime
from engine import FunnelEngine 
from src.ui.components.info_card import KPICard, BrandAccordionCard
from src.utils.report_handler import ReportHandler

class MonitoringScreen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#f5f6fa")
        self.controller = controller
        
        # Inicializa SEU Motor (que já conecta no DB e carrega JSONs)
        self.engine = FunnelEngine() 
        
        self.df = None
        
        # Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.setup_sidebar()
        self.setup_main_area()
        
        # Carrega dados
        self.run_query()

    def setup_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, fg_color="#ffffff", corner_radius=0, width=280)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # LOGO
        self.logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.logo_frame.pack(pady=(30, 20), padx=20, fill="x")
        try:
            logo_path = "assets/logo.png"
            if os.path.exists(logo_path):
                pil_logo = Image.open(logo_path)
                w, h = pil_logo.size
                ratio = h / w
                new_w = 200
                new_h = int(new_w * ratio)
                logo_img = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(new_w, new_h))
                ctk.CTkLabel(self.logo_frame, image=logo_img, text="").pack(anchor="w")
            else:
                ctk.CTkLabel(self.logo_frame, text="DASHBOARD", font=("Arial", 20, "bold")).pack(anchor="w")
        except:
            pass

        ctk.CTkFrame(self.sidebar, height=2, fg_color="#f1f2f6").pack(fill="x", padx=20, pady=10)

        # FILTROS
        ctk.CTkLabel(self.sidebar, text="FILTROS", font=("Roboto", 14, "bold"), text_color="#95a5a6").pack(anchor="w", padx=20, pady=(10, 5))

        # Data
        self.date_var = ctk.StringVar(value=datetime.now().strftime("%d/%m/%Y"))
        self.entry_date = ctk.CTkEntry(self.sidebar, textvariable=self.date_var, placeholder_text="DD/MM/AAAA")
        self.entry_date.pack(padx=20, pady=5, fill="x")

        # Marca
        self.marca_var = ctk.StringVar(value="Todas as Marcas")
        self.cmb_marca = ctk.CTkComboBox(self.sidebar, variable=self.marca_var, command=self.on_brand_change)
        self.cmb_marca.pack(padx=20, pady=10, fill="x")

        # Filial
        self.filial_var = ctk.StringVar(value="Todas as Filiais")
        self.cmb_filial = ctk.CTkComboBox(self.sidebar, variable=self.filial_var)
        self.cmb_filial.pack(padx=20, pady=10, fill="x")

        # Botão Atualizar
        self.btn_refresh = ctk.CTkButton(self.sidebar, text="Aplicar Filtros", fg_color="#2980b9", 
                                         height=40, font=("Roboto", 12, "bold"),
                                         command=self.run_query)
        self.btn_refresh.pack(padx=20, pady=30, fill="x")

        self.populate_filters()

    def populate_filters(self):
        """Usa o unit_map do FunnelEngine para preencher os combos."""
        try:
            # Pega as chaves do dicionário de normalização do seu Engine
            brands = sorted(list(self.engine.unit_map.keys()))
            unique_brands = ["Todas as Marcas"] + brands
            
            self.cmb_marca.configure(values=unique_brands)
            self.cmb_marca.set("Todas as Marcas")
            self.cmb_filial.configure(values=["Todas as Filiais"])
        except Exception as e:
            print(f"Erro filtros: {e}")

    def on_brand_change(self, choice):
        if choice == "Todas as Marcas":
            self.cmb_filial.configure(values=["Todas as Filiais"])
            self.cmb_filial.set("Todas as Filiais")
            return

        # Pega as filiais daquela marca específica direto do JSON carregado no Engine
        try:
            brand_info = self.engine.unit_map.get(choice, {})
            units_list = brand_info.get("unidades", [])
            
            # Extrai apenas os nomes oficiais
            unit_names = [u["nome_oficial"] for u in units_list]
            relevant_units = ["Todas as Filiais"] + sorted(unit_names)
            
            self.cmb_filial.configure(values=relevant_units)
            self.cmb_filial.set("Todas as Filiais")
        except:
            pass

    def setup_main_area(self):
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)
        self.main_frame.grid_rowconfigure(2, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        ctk.CTkLabel(header, text="Dashboard Comercial", font=("Roboto", 28, "bold"), text_color="#2c3e50").pack(side="left")
        ctk.CTkLabel(header, text="Visão consolidada de Leads e Matrículas", font=("Roboto", 14), text_color="#7f8c8d").pack(side="left", padx=15, pady=(10, 0))

        # KPIs
        self.kpi_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.kpi_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        for i in range(4): self.kpi_frame.grid_columnconfigure(i, weight=1)

        # Cards (Scroll)
        self.scroll_cards = ctk.CTkScrollableFrame(self.main_frame, fg_color="transparent")
        self.scroll_cards.grid(row=2, column=0, sticky="nsew")

    def run_query(self):
        """Chama seu FunnelEngine para processar tudo."""
        # A data é lida da interface, mas como o engine não foi alterado, 
        # não passamos o argumento para evitar o erro TypeError.
        # date_filter = self.entry_date.get() 
        
        # CORREÇÃO: Chamada sem argumentos para compatibilidade com o engine atual
        self.df = self.engine.generate_full_report()

        self.update_kpis()
        self.render_accordion_cards()

    def update_kpis(self):
        for w in self.kpi_frame.winfo_children(): w.destroy()

        if self.df is None or self.df.empty: return

        # Totais simples do DataFrame retornado pelo Engine
        total_leads = int(self.df['Leads'].sum())
        total_agend = int(self.df['Visita Agendada'].sum())
        total_visit = int(self.df['Visita Realizada'].sum())
        total_matri = int(self.df['Matricula'].sum())

        kpi_configs = [
            ("Leads", total_leads, "#3498db", "assets/leads_logo.png"),
            ("Agendamentos", total_agend, "#e67e22", "assets/agendamento_logo.png"),
            ("Visitas", total_visit, "#9b59b6", "assets/visita_realizada_logo.png"),
            ("Matrículas", total_matri, "#27ae60", "assets/matricula_logo.png"),
        ]

        for i, (title, val, color, icon) in enumerate(kpi_configs):
            card = KPICard(self.kpi_frame, title, str(val), color, icon)
            card.grid(row=0, column=i, padx=10, sticky="ew")

    def render_accordion_cards(self):
        for w in self.scroll_cards.winfo_children(): w.destroy()

        if self.df is None or self.df.empty:
            ctk.CTkLabel(self.scroll_cards, text="Nenhum dado encontrado.", text_color="#7f8c8d").pack(pady=20)
            return

        # --- FILTRAGEM VISUAL ---
        # O Engine traz tudo, a UI filtra o que mostra
        filtered_df = self.df.copy()
        
        selected_brand = self.marca_var.get()
        selected_branch = self.filial_var.get()

        if selected_brand != "Todas as Marcas":
            # Usa a função do Engine para descobrir a marca de cada linha
            filtered_df['temp_marca'] = filtered_df['unidade'].apply(self.engine.extract_marca)
            filtered_df = filtered_df[filtered_df['temp_marca'] == selected_brand]
        
        if selected_branch != "Todas as Filiais":
            filtered_df = filtered_df[filtered_df['unidade'] == selected_branch]

        if filtered_df.empty:
            ctk.CTkLabel(self.scroll_cards, text="Sem dados para este filtro.", text_color="#7f8c8d").pack(pady=20)
            return

        # --- AGRUPAMENTO ---
        grouped_data = {}
        records = filtered_df.to_dict('records')
        
        for row in records:
            brand = self.engine.extract_marca(row['unidade'])
            
            # Filtro opcional de "OUTROS"
            if brand == "OUTROS": continue 

            if brand not in grouped_data: grouped_data[brand] = []
            grouped_data[brand].append(row)

        for brand in sorted(grouped_data.keys()):
            rows = grouped_data[brand]
            
            brand_totals = {
                'Matricula': sum(r.get('Matricula', 0) for r in rows),
                'Leads': sum(r.get('Leads', 0) for r in rows)
            }
            
            card = BrandAccordionCard(
                self.scroll_cards, 
                brand_name=brand, 
                brand_totals=brand_totals,
                branch_list_data=rows,
                on_export_brand=self.export_brand,
                on_export_branch=self.export_branch
            )
            card.pack(fill="x", pady=6, padx=5)

    def export_branch(self, data):
        safe_name = str(data.get('unidade', 'relatorio')).replace(" ", "_")
        ReportHandler.gerar_excel_individual(data, f"Relatorio_{safe_name}.xlsx")
        
    def export_brand(self, brand_name, data_list):
        df_brand = pd.DataFrame(data_list)
        safe_name = brand_name.replace(" ", "_")
        ReportHandler.gerar_excel_consolidado(df_brand, f"Consolidado_{safe_name}.xlsx")