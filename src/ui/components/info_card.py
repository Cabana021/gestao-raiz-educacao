import customtkinter as ctk
from PIL import Image
import os

class KPICard(ctk.CTkFrame):
    """
    Card superior com totais globais (KPIs).
    Agora suporta ícones de imagem (PNG).
    """
    def __init__(self, parent, title, value, color="#2c3e50", icon_path=None):
        super().__init__(parent, fg_color="white", corner_radius=12)
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Ícone (Imagem ou Fallback)
        self.icon_label = ctk.CTkLabel(self, text="")
        if icon_path and os.path.exists(icon_path):
            try:
                # Carrega imagem PNG
                pil_img = Image.open(icon_path)
                # Ajuste o tamanho conforme necessário (ex: 40x40)
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(40, 40))
                self.icon_label.configure(image=ctk_img, text="")
            except Exception as e:
                print(f"Erro ao carregar icone {icon_path}: {e}")
                self.icon_label.configure(text="📊") # Fallback
        else:
             self.icon_label.configure(text="📊", font=("Segoe UI Emoji", 24))

        self.icon_label.grid(row=0, column=0, rowspan=2, padx=(20, 15), pady=15)

        # Container para Texto (Título e Valor)
        text_frame = ctk.CTkFrame(self, fg_color="transparent")
        text_frame.grid(row=0, column=1, rowspan=2, sticky="w", pady=10, padx=(0, 20))

        # Título
        lbl_title = ctk.CTkLabel(text_frame, text=title.upper(), font=("Roboto", 11, "bold"), text_color="#7f8c8d")
        lbl_title.pack(anchor="w")

        # Valor
        self.lbl_value = ctk.CTkLabel(text_frame, text=value, font=("Roboto", 24, "bold"), text_color=color)
        self.lbl_value.pack(anchor="w")


class BranchRow(ctk.CTkFrame):
    """Representa uma filial individual DENTRO do card da marca."""
    def __init__(self, parent, data, on_excel_click, **kwargs):
        super().__init__(parent, fg_color="#f8f9fa", corner_radius=8, border_width=1, border_color="#ecf0f1", **kwargs)
        self.data = data
        self.on_excel_click = on_excel_click
        
        self.grid_columnconfigure(0, weight=1)
        
        # Nome da Unidade
        lbl_name = ctk.CTkLabel(self, text=data.get('unidade', 'Filial'), 
                                font=("Roboto", 12, "bold"), text_color="#34495e", anchor="w")
        lbl_name.grid(row=0, column=0, padx=15, pady=8, sticky="ew")

        # Dados Resumidos
        stats_text = f"Leads: {int(data.get('Leads', 0))}  |  Agend: {int(data.get('Visita Agendada', 0))}"
        lbl_stats = ctk.CTkLabel(self, text=stats_text, font=("Roboto", 11), text_color="#7f8c8d")
        lbl_stats.grid(row=0, column=1, padx=10, sticky="e")

        # Destaque Matrícula
        matr_val = int(data.get('Matricula', 0))
        lbl_matr = ctk.CTkLabel(self, text=f"Matrículas: {matr_val}", font=("Roboto", 12, "bold"), text_color="#27ae60")
        lbl_matr.grid(row=0, column=2, padx=15, sticky="e")

        # Botão Excel
        self._setup_excel_button()

        # Hover Effect
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        for child in self.winfo_children():
            if isinstance(child, ctk.CTkLabel):
                child.bind("<Enter>", self.on_enter)
                child.bind("<Leave>", self.on_leave)

    def _setup_excel_button(self):
        xls_img = None
        btn_text = "XLS"
        try:
            icon_path = "assets/excel_logo.png"
            if os.path.exists(icon_path):
                xls_img = ctk.CTkImage(Image.open(icon_path), size=(16, 16))
                btn_text = ""
        except:
            pass
            
        btn = ctk.CTkButton(self, text=btn_text, image=xls_img, width=40, height=24,
                            font=("Roboto", 10, "bold"), fg_color="#e0e0e0", text_color="#333",
                            hover_color="#2ecc71", 
                            command=lambda: self.on_excel_click(self.data))
        btn.grid(row=0, column=3, padx=(5, 15), pady=5)

    def on_enter(self, event):
        self.configure(border_color="#e67e22", fg_color="#ffffff") 

    def on_leave(self, event):
        self.configure(border_color="#ecf0f1", fg_color="#f8f9fa")


class BrandAccordionCard(ctk.CTkFrame):
    """Card Pai (Marca) que expande."""
    def __init__(self, parent, brand_name, brand_totals, branch_list_data, on_export_brand, on_export_branch):
        super().__init__(parent, fg_color="white", corner_radius=10, border_width=2, border_color="#ecf0f1")
        self.branch_data = branch_list_data
        self.on_export_branch = on_export_branch
        self.is_expanded = False
        
        self.grid_columnconfigure(0, weight=1)
        
        # --- HEADER ---
        self.header = ctk.CTkFrame(self, fg_color="transparent", corner_radius=10, height=50)
        self.header.grid(row=0, column=0, sticky="ew", ipady=5)
        self.header.bind("<Button-1>", self.toggle_expand)
        
        self.lbl_arrow = ctk.CTkLabel(self.header, text="▼", font=("Arial", 12), text_color="#95a5a6")
        self.lbl_arrow.pack(side="left", padx=(15, 5))
        
        lbl_brand = ctk.CTkLabel(self.header, text=brand_name, font=("Roboto", 15, "bold"), text_color="#2c3e50")
        lbl_brand.pack(side="left", padx=5)
        
        self.lbl_arrow.bind("<Button-1>", self.toggle_expand)
        lbl_brand.bind("<Button-1>", self.toggle_expand)

        # Botão Relatório
        btn_excel_brand = ctk.CTkButton(self.header, text="Relatório Consolidado", width=140, height=28,
                                        font=("Roboto", 11, "bold"), fg_color="#e67e22", hover_color="#d35400",
                                        command=lambda: on_export_brand(brand_name, branch_list_data))
        btn_excel_brand.pack(side="right", padx=15)

        # Resumo
        summary_text = f"Total Matrículas: {int(brand_totals.get('Matricula', 0))}  |  Total Leads: {int(brand_totals.get('Leads', 0))}"
        lbl_summary = ctk.CTkLabel(self.header, text=summary_text, font=("Roboto", 12), text_color="#7f8c8d")
        lbl_summary.pack(side="right", padx=20)
        lbl_summary.bind("<Button-1>", self.toggle_expand)

        # --- CONTAINER FILHO ---
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        
        self.header.bind("<Enter>", self.on_header_enter)
        self.header.bind("<Leave>", self.on_header_leave)

    def on_header_enter(self, event):
        self.configure(border_color="#3498db")

    def on_header_leave(self, event):
        self.configure(border_color="#ecf0f1")

    def toggle_expand(self, event=None):
        if self.is_expanded:
            self.content_frame.grid_forget()
            self.lbl_arrow.configure(text="▼")
        else:
            self.build_children()
            self.content_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
            self.lbl_arrow.configure(text="▲")
        self.is_expanded = not self.is_expanded

    def build_children(self):
        if len(self.content_frame.winfo_children()) > 0: return
        
        # Cabeçalho interno
        ctk.CTkLabel(self.content_frame, text="Detalhes por Unidade:", anchor="w",
                     font=("Roboto", 10, "bold"), text_color="#bdc3c7").pack(fill="x", pady=(5, 5))

        for item in self.branch_data:
            row = BranchRow(self.content_frame, item, self.on_export_branch)
            row.pack(fill="x", pady=3)