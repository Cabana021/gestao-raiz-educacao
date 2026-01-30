import customtkinter as ctk
from PIL import Image
import os
import pandas as pd
import threading
from tkinter import messagebox
from datetime import datetime
from src.engines.funil.captacao.engine import FunnelEngine
from src.utils.report_handler import ReportHandler

# Definição de Cores Globais (Baseado no main_menu.py)
COLORS = {
    "bg_main": "#1a1a1a",  # Fundo Principal
    "bg_card": "#242424",  # Fundo dos Cards/Containers
    "bg_sidebar": "#151515",  # Fundo da Sidebar
    "bg_hover": "#2f2f2f",  # Hover genérico
    "text_white": "#FFFFFF",
    "text_gray": "#A0A0A0",
    "orange_raiz": "#F36F21",  # Destaque Laranja
    "blue_raiz": "#203764",  # Azul Escuro
    "blue_light": "#4a90e2",  # Azul Claro (Botões/Bordas)
    "border_dim": "#404040",  # Bordas sutis
    "success": "#27ae60",  # Verde para matrículas/sucesso
    "input_bg": "#2b2b2b",  # Fundo de inputs
}


class KPICard(ctk.CTkFrame):
    """
    Card de KPI no estilo Dark (Topo da tela).
    """

    def __init__(self, parent, title, value, highlight_color, icon_path=None):
        super().__init__(
            parent,
            fg_color=COLORS["bg_card"],
            corner_radius=12,
            border_width=2,
            border_color=highlight_color,
        )

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure((0, 1), weight=1)

        # --- Ícone ---
        self.icon_label = ctk.CTkLabel(self, text="")
        if icon_path and os.path.exists(icon_path):
            try:
                pil_img = Image.open(icon_path)
                ctk_img = ctk.CTkImage(
                    light_image=pil_img, dark_image=pil_img, size=(38, 38)
                )
                self.icon_label.configure(image=ctk_img)
            except Exception as e:
                print(f"Erro ícone KPI: {e}")
                self.icon_label.configure(text="📊", font=("Roboto", 24))
        else:
            self.icon_label.configure(text="📊", font=("Segoe UI Emoji", 24))

        self.icon_label.grid(row=0, column=0, rowspan=2, padx=(20, 15), pady=15)

        # --- Textos ---
        # Título
        lbl_title = ctk.CTkLabel(
            self,
            text=title.upper(),
            font=("Roboto", 11, "bold"),
            text_color=COLORS["text_gray"],
        )
        lbl_title.grid(row=0, column=1, sticky="sw", padx=(0, 15), pady=(12, 0))

        # Valor
        self.lbl_value = ctk.CTkLabel(
            self,
            text=value,
            font=("Roboto", 26, "bold"),
            text_color=COLORS["text_white"],
        )
        self.lbl_value.grid(row=1, column=1, sticky="nw", padx=(0, 15), pady=(0, 12))


class MiniStatCard(ctk.CTkFrame):
    """
    Mini Card visual para exibir métricas dentro da linha da filial.
    Ex: Cardzinho de Leads e Cardzinho de Matrículas.
    """

    def __init__(self, parent, label, value, color_highlight):
        super().__init__(
            parent,
            fg_color="#2b2b2b",
            corner_radius=6,
            border_width=1,
            border_color="#3a3a3a",
        )

        # Layout interno simples
        self.columnconfigure(0, weight=1)

        # Label (Título Pequeno)
        lbl = ctk.CTkLabel(
            self,
            text=label.upper(),
            font=("Roboto", 9, "bold"),
            text_color=COLORS["text_gray"],
        )
        lbl.pack(pady=(5, 0), padx=10, anchor="w")

        # Valor (Destaque)
        val = ctk.CTkLabel(
            self,
            text=str(value),
            font=("Roboto", 16, "bold"),
            text_color=color_highlight,
        )
        val.pack(pady=(0, 5), padx=10, anchor="w")


class BranchRow(ctk.CTkFrame):
    """
    Linha representando uma filial (Unidade) dentro do Accordion.
    Refatorado para exibir Mini Cards ao invés de texto solto.
    """

    def __init__(self, parent, data, on_excel_click, **kwargs):
        super().__init__(
            parent,
            fg_color="#1f1f1f",  # Um pouco mais escuro para contrastar com os mini cards
            corner_radius=8,
            border_width=0,
            **kwargs,
        )
        self.data = data
        self.on_excel_click = on_excel_click

        # Layout:
        # Linha 0: Nome da Unidade + Botão Excel
        # Linha 1: Container com os Mini Cards

        self.grid_columnconfigure(0, weight=1)

        # --- HEADER DA FILIAL ---
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(8, 5))

        # Nome da Unidade
        lbl_name = ctk.CTkLabel(
            header_frame,
            text=data.get("unidade", "Filial"),
            font=("Roboto", 13, "bold"),
            text_color="#E0E0E0",
            anchor="w",
        )
        lbl_name.pack(side="left")

        # Botão Excel (Icon only)
        self._setup_excel_button(header_frame)

        # --- ÁREA DE CARDS (LEADS / MATRÍCULAS) ---
        stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        stats_frame.pack(fill="x", padx=10, pady=(0, 10))

        leads_val = int(data.get("Leads", 0))
        matr_val = int(data.get("Matricula", 0))

        # Mini Card Leads
        card_leads = MiniStatCard(stats_frame, "Leads", leads_val, COLORS["blue_light"])
        card_leads.pack(side="left", fill="x", expand=True, padx=(0, 5))

        # Mini Card Matrículas
        card_matr = MiniStatCard(stats_frame, "Matrículas", matr_val, COLORS["success"])
        card_matr.pack(side="left", fill="x", expand=True, padx=(5, 0))

        # Hover Effect no container principal
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def _setup_excel_button(self, parent_frame):
        xls_img = None
        try:
            icon_path = "assets/excel_logo.png"
            if os.path.exists(icon_path):
                xls_img = ctk.CTkImage(Image.open(icon_path), size=(16, 16))
        except:
            pass

        if xls_img:
            btn = ctk.CTkButton(
                parent_frame,
                text="",
                image=xls_img,
                width=24,
                height=24,
                fg_color="transparent",
                hover_color="#3a3a3a",
                command=lambda: self.on_excel_click(self.data),
            )
        else:
            btn = ctk.CTkButton(
                parent_frame,
                text="XLS",
                width=30,
                height=20,
                font=("Roboto", 8, "bold"),
                fg_color="#333",
                command=lambda: self.on_excel_click(self.data),
            )
        btn.pack(side="right")

    def on_enter(self, event):
        self.configure(fg_color="#262626")

    def on_leave(self, event):
        self.configure(fg_color="#1f1f1f")


class BrandAccordionCard(ctk.CTkFrame):
    """
    Card da Marca (Pai) que expande para mostrar as filiais.
    """

    def __init__(
        self,
        parent,
        brand_name,
        brand_totals,
        branch_list_data,
        on_export_brand,
        on_export_branch,
    ):
        super().__init__(
            parent,
            fg_color="#242424",
            corner_radius=10,
            border_width=1,
            border_color="#333",
        )
        self.branch_data = branch_list_data
        self.on_export_branch = on_export_branch
        self.is_expanded = False

        self.grid_columnconfigure(0, weight=1)

        # --- HEADER ---
        self.header = ctk.CTkFrame(
            self, fg_color="transparent", corner_radius=10, height=50
        )
        self.header.grid(row=0, column=0, sticky="ew", ipady=8)
        self.header.bind("<Button-1>", self.toggle_expand)

        # Seta
        self.lbl_arrow = ctk.CTkLabel(
            self.header, text="▼", font=("Arial", 12), text_color=COLORS["orange_raiz"]
        )
        self.lbl_arrow.pack(side="left", padx=(15, 5))

        # Nome da Marca
        lbl_brand = ctk.CTkLabel(
            self.header,
            text=brand_name,
            font=("Roboto", 16, "bold"),
            text_color=COLORS["text_white"],
        )
        lbl_brand.pack(side="left", padx=5)

        self.lbl_arrow.bind("<Button-1>", self.toggle_expand)
        lbl_brand.bind("<Button-1>", self.toggle_expand)

        # Container Direita (Resumo + Botão Excel)
        right_container = ctk.CTkFrame(self.header, fg_color="transparent")
        right_container.pack(side="right", padx=10)
        right_container.bind("<Button-1>", self.toggle_expand)

        # Botão Relatório Consolidado (Agora apenas ícone)
        xls_icon = None
        try:
            p = "assets/excel_logo.png"
            if os.path.exists(p):
                xls_icon = ctk.CTkImage(Image.open(p), size=(20, 20))
        except:
            pass

        if xls_icon:
            btn_excel_brand = ctk.CTkButton(
                right_container,
                text="",
                image=xls_icon,
                width=30,
                height=30,
                fg_color="transparent",
                hover_color="#3a3a3a",
                command=lambda: on_export_brand(brand_name, branch_list_data),
            )
            btn_excel_brand.pack(side="right", padx=(10, 5))
        else:
            btn_excel_brand = ctk.CTkButton(
                right_container,
                text="XLS",
                width=40,
                height=25,
                fg_color=COLORS["orange_raiz"],
                command=lambda: on_export_brand(brand_name, branch_list_data),
            )
            btn_excel_brand.pack(side="right", padx=(10, 5))

        # Resumo Numérico
        summary_text = f"Matrículas: {int(brand_totals.get('Matricula', 0))}  |  Leads: {int(brand_totals.get('Leads', 0))}"
        lbl_summary = ctk.CTkLabel(
            right_container,
            text=summary_text,
            font=("Roboto", 12),
            text_color=COLORS["text_gray"],
        )
        lbl_summary.pack(side="right", padx=5)
        lbl_summary.bind("<Button-1>", self.toggle_expand)

        # --- CONTAINER FILHO ---
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")

        self.header.bind("<Enter>", self.on_header_enter)
        self.header.bind("<Leave>", self.on_header_leave)

    def on_header_enter(self, event):
        self.configure(border_color=COLORS["blue_light"])

    def on_header_leave(self, event):
        self.configure(border_color="#333")

    def toggle_expand(self, event=None):
        if self.is_expanded:
            self.content_frame.grid_forget()
            self.lbl_arrow.configure(text="▼")
        else:
            self.build_children()
            self.content_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 15))
            self.lbl_arrow.configure(text="▲")
        self.is_expanded = not self.is_expanded

    def build_children(self):
        if len(self.content_frame.winfo_children()) > 0:
            return

        # Cabeçalho interno sutil
        ctk.CTkLabel(
            self.content_frame,
            text="Detalhamento por Unidade",
            anchor="w",
            font=("Roboto", 10, "bold"),
            text_color="#555",
        ).pack(fill="x", pady=(5, 5))

        # Grid para as filiais? Ou Lista vertical
        # Lista vertical fica melhor com os cards novos
        for item in self.branch_data:
            row = BranchRow(self.content_frame, item, self.on_export_branch)
            row.pack(fill="x", pady=4)


class MonitoringScreen(ctk.CTkFrame):
    """
    Tela Principal Refatorada.
    """

    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=COLORS["bg_main"])
        self.controller = controller

        # Inicializa o Motor
        self.engine = FunnelEngine()
        self.df = None

        # Layout principal
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.setup_sidebar()
        self.setup_main_area()

        # Carrega dados iniciais
        self.run_query()

    def setup_sidebar(self):
        """Sidebar lateral escura com filtros"""
        self.sidebar = ctk.CTkFrame(
            self, fg_color=COLORS["bg_sidebar"], corner_radius=0, width=280
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        back_icon = None
        try:
            icon_p = "left_arrow_icon.png"
            if os.path.exists(icon_p):
                back_icon = ctk.CTkImage(Image.open(icon_p), size=(24, 24))
        except:
            pass

        if back_icon:
            btn_back = ctk.CTkButton(
                self.sidebar,
                text="",
                image=back_icon,
                width=40,
                height=40,
                corner_radius=20,  # Redondo
                fg_color="transparent",
                hover_color=COLORS["bg_hover"],
                command=lambda: self.controller.show_frame("MainMenu"),
            )
            btn_back.pack(anchor="w", pady=(20, 10), padx=15)
        else:
            # Fallback
            btn_back = ctk.CTkButton(
                self.sidebar,
                text="← Voltar",
                command=lambda: self.controller.show_frame("MainMenu"),
            )
            btn_back.pack(pady=(20, 10), padx=20)

        # LOGO
        self.logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.logo_frame.pack(pady=(10, 20), padx=20, fill="x")
        try:
            logo_path = "assets/raizeducacao_logo.png"
            if os.path.exists(logo_path):
                pil_logo = Image.open(logo_path)
                w, h = pil_logo.size
                ratio = h / w
                new_w = 180
                new_h = int(new_w * ratio)
                logo_img = ctk.CTkImage(
                    light_image=pil_logo, dark_image=pil_logo, size=(new_w, new_h)
                )
                ctk.CTkLabel(self.logo_frame, image=logo_img, text="").pack(
                    anchor="center"
                )
            else:
                ctk.CTkLabel(
                    self.logo_frame,
                    text="RAIZ EDUCAÇÃO",
                    font=("Roboto", 20, "bold"),
                    text_color=COLORS["orange_raiz"],
                ).pack(anchor="w")
        except:
            pass

        ctk.CTkFrame(self.sidebar, height=2, fg_color=COLORS["border_dim"]).pack(
            fill="x", padx=20, pady=10
        )

        # FILTROS
        ctk.CTkLabel(
            self.sidebar,
            text="FILTROS",
            font=("Roboto", 14, "bold"),
            text_color=COLORS["orange_raiz"],
        ).pack(anchor="w", padx=20, pady=(10, 5))

        # Estilo Comum para Inputs
        input_style = {
            "fg_color": COLORS["input_bg"],
            "border_color": COLORS["border_dim"],
            "text_color": COLORS["text_white"],
            "dropdown_fg_color": COLORS["input_bg"],
            "dropdown_text_color": COLORS["text_white"],
        }

        # Data
        self.date_var = ctk.StringVar(value=datetime.now().strftime("%d/%m/%Y"))
        self.entry_date = ctk.CTkEntry(
            self.sidebar,
            textvariable=self.date_var,
            placeholder_text="DD/MM/AAAA",
            fg_color=COLORS["input_bg"],
            border_color=COLORS["border_dim"],
            text_color="white",
        )
        self.entry_date.pack(padx=20, pady=5, fill="x")

        # Marca
        self.marca_var = ctk.StringVar(value="Todas as Marcas")
        self.cmb_marca = ctk.CTkComboBox(
            self.sidebar,
            variable=self.marca_var,
            command=self.on_brand_change,
            **input_style,
        )
        self.cmb_marca.pack(padx=20, pady=10, fill="x")

        # Filial
        self.filial_var = ctk.StringVar(value="Todas as Filiais")
        self.cmb_filial = ctk.CTkComboBox(
            self.sidebar, variable=self.filial_var, **input_style
        )
        self.cmb_filial.pack(padx=20, pady=10, fill="x")

        # Botão Atualizar
        self.btn_refresh = ctk.CTkButton(
            self.sidebar,
            text="APLICAR FILTROS",
            fg_color=COLORS["blue_light"],
            hover_color="#357abd",
            height=40,
            font=("Roboto", 12, "bold"),
            command=self.run_query,
        )
        self.btn_refresh.pack(padx=20, pady=30, fill="x")

        self.populate_filters()

    def setup_main_area(self):
        """Área central com KPIs e lista"""
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)
        self.main_frame.grid_rowconfigure(2, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # --- HEADER ---
        header = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 20))

        # Títulos
        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left")
        ctk.CTkLabel(
            title_box,
            text="Dashboard Comercial",
            font=("Roboto", 28, "bold"),
            text_color=COLORS["text_white"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_box,
            text="Visão consolidada de Leads e Matrículas",
            font=("Roboto", 14),
            text_color=COLORS["text_gray"],
        ).pack(anchor="w", pady=(5, 0))

        # Botão de Exportar Tudo (Canto Superior Direito)
        self.btn_export_all = None
        try:
            xl_icon_path = "assets/excel_logo.png"
            if os.path.exists(xl_icon_path):
                img_xls = ctk.CTkImage(Image.open(xl_icon_path), size=(28, 28))

                self.btn_export_all = ctk.CTkButton(
                    header,
                    text="",
                    image=img_xls,
                    width=40,
                    height=40,
                    fg_color="transparent",
                    hover_color=COLORS["bg_hover"],
                    command=self.exportar_tudo_thread,
                )
                self.btn_export_all.pack(side="right", anchor="center")
            else:
                self.btn_export_all = ctk.CTkButton(
                    header,
                    text="Exportar Geral",
                    fg_color=COLORS["success"],
                    height=30,
                    command=self.exportar_tudo_thread,
                )
                self.btn_export_all.pack(side="right")
        except Exception as e:
            print(f"Erro btn export: {e}")

        # --- KPI CONTAINER ---
        self.kpi_wrapper = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.kpi_wrapper.grid(row=1, column=0, sticky="ew", pady=(0, 25))
        self.kpi_wrapper.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # --- LISTAGEM (Scroll) ---
        self.scroll_cards = ctk.CTkScrollableFrame(
            self.main_frame, fg_color="transparent"
        )
        self.scroll_cards.grid(row=2, column=0, sticky="nsew")

    # --- Lógica de Negócio (Inalterada) ---

    def populate_filters(self):
        try:
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

        try:
            brand_info = self.engine.unit_map.get(choice, {})
            units_list = brand_info.get("unidades", [])
            unit_names = [u["nome_oficial"] for u in units_list]
            relevant_units = ["Todas as Filiais"] + sorted(unit_names)
            self.cmb_filial.configure(values=relevant_units)
            self.cmb_filial.set("Todas as Filiais")
        except:
            pass

    def run_query(self):
        threading.Thread(target=self._run_query_thread).start()

    def _run_query_thread(self):
        try:
            self.df = self.engine.generate_full_report()
            self.after(0, self.update_ui_after_query)
        except Exception as e:
            print(f"Erro query: {e}")

    def update_ui_after_query(self):
        self.update_kpis()
        self.render_accordion_cards()

    def update_kpis(self):
        for w in self.kpi_wrapper.winfo_children():
            w.destroy()

        if self.df is None or self.df.empty:
            return

        total_leads = int(self.df["Leads"].sum())
        total_agend = int(self.df["Visita Agendada"].sum())
        total_visit = int(self.df["Visita Realizada"].sum())
        total_matri = int(self.df["Matricula"].sum())

        kpi_configs = [
            ("Leads", total_leads, COLORS["blue_light"], "assets/leads_logo.png"),
            (
                "Agendamentos",
                total_agend,
                COLORS["orange_raiz"],
                "assets/agendamento_logo.png",
            ),
            ("Visitas", total_visit, "#9b59b6", "assets/visita_realizada_logo.png"),
            ("Matrículas", total_matri, COLORS["success"], "assets/matricula_logo.png"),
        ]

        for i, (title, val, color, icon) in enumerate(kpi_configs):
            card = KPICard(self.kpi_wrapper, title, str(val), color, icon)
            card.grid(row=0, column=i, padx=10, sticky="ew")

    def render_accordion_cards(self):
        for w in self.scroll_cards.winfo_children():
            w.destroy()

        if self.df is None or self.df.empty:
            ctk.CTkLabel(
                self.scroll_cards,
                text="Nenhum dado encontrado.",
                text_color=COLORS["text_gray"],
            ).pack(pady=20)
            return

        filtered_df = self.df.copy()
        selected_brand = self.marca_var.get()
        selected_branch = self.filial_var.get()

        if selected_brand != "Todas as Marcas":
            filtered_df["temp_marca"] = filtered_df["unidade"].apply(
                self.engine.extract_marca
            )
            filtered_df = filtered_df[filtered_df["temp_marca"] == selected_brand]

        if selected_branch != "Todas as Filiais":
            filtered_df = filtered_df[filtered_df["unidade"] == selected_branch]

        if filtered_df.empty:
            ctk.CTkLabel(
                self.scroll_cards,
                text="Sem dados para este filtro.",
                text_color=COLORS["text_gray"],
            ).pack(pady=20)
            return

        grouped_data = {}
        records = filtered_df.to_dict("records")

        for row in records:
            brand = self.engine.extract_marca(row["unidade"])
            if brand == "OUTROS":
                continue
            if brand not in grouped_data:
                grouped_data[brand] = []
            grouped_data[brand].append(row)

        for brand in sorted(grouped_data.keys()):
            rows = grouped_data[brand]
            brand_totals = {
                "Matricula": sum(r.get("Matricula", 0) for r in rows),
                "Leads": sum(r.get("Leads", 0) for r in rows),
            }

            card = BrandAccordionCard(
                self.scroll_cards,
                brand_name=brand,
                brand_totals=brand_totals,
                branch_list_data=rows,
                on_export_brand=self.export_brand,
                on_export_branch=self.export_branch,
            )
            card.pack(fill="x", pady=6, padx=5)

    def exportar_tudo_thread(self):
        if self.df is None or self.df.empty:
            messagebox.showwarning("Aviso", "Não há dados carregados para exportar.")
            return

        if self.btn_export_all:
            self.btn_export_all.configure(state="disabled")

        threading.Thread(target=self._processar_exportacao_geral).start()

    def _processar_exportacao_geral(self):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            nome_arquivo = f"Relatorio_Consolidado_Geral_{timestamp}.xlsx"
            caminho = os.path.abspath(nome_arquivo)

            sucesso = ReportHandler.gerar_excel_consolidado(self.df, caminho)
            self.after(0, lambda: self._finalizar_exportacao(sucesso, caminho))
        except Exception as e:
            print(f"Erro exportacao: {e}")
            self.after(0, lambda: self._finalizar_exportacao(False, str(e)))

    def _finalizar_exportacao(self, sucesso, msg):
        if self.btn_export_all:
            self.btn_export_all.configure(state="normal")

        if sucesso:
            messagebox.showinfo("Sucesso", f"Relatório salvo em:\n{msg}")
        else:
            messagebox.showerror("Erro", f"Falha ao gerar relatório: {msg}")

    def export_branch(self, data):
        safe_name = str(data.get("unidade", "relatorio")).replace(" ", "_")
        ReportHandler.gerar_excel_individual(data, f"Relatorio_{safe_name}.xlsx")

    def export_brand(self, brand_name, data_list):
        df_brand = pd.DataFrame(data_list)
        safe_name = brand_name.replace(" ", "_")
        ReportHandler.gerar_excel_consolidado(df_brand, f"Consolidado_{safe_name}.xlsx")
