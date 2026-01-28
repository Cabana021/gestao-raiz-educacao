import customtkinter as ctk
from PIL import Image
import os

class InfoCard(ctk.CTkFrame):
    def __init__(self, parent, data, on_excel_click, **kwargs):
        super().__init__(parent, **kwargs)
        self.data = data
        self.on_excel_click = on_excel_click
        
        # Configuração Visual Light
        self.default_border = "#bdc3c7"
        self.hover_orange = "#e67e22"
        self.hover_blue = "#3498db"
        
        # Fundo claro, texto escuro
        self.configure(fg_color="#ffffff", corner_radius=15, border_width=2, border_color=self.default_border)
        
        # Bind de eventos para efeito Hover
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        
        # Grid Interno
        self.grid_columnconfigure(1, weight=1)
        
        # Cabeçalho: Nome da Unidade/Marca (Texto Escuro)
        header_text = f"{data.get('unidade', 'N/A')}"
        
        # Define cor do cabeçalho baseado na marca (apenas texto)
        marca_lower = str(data.get('unidade', '')).lower()
        if "total" in marca_lower:
            header_color = "#2c3e50"
        elif "escola a" in marca_lower:
            header_color = "#d35400"
        elif "escola b" in marca_lower:
            header_color = "#2980b9"
        else:
            header_color = "#7f8c8d"

        self.lbl_header = ctk.CTkLabel(
            self, text=header_text, text_color=header_color,
            font=("Roboto", 16, "bold"), justify="left"
        )
        self.lbl_header.grid(row=0, column=0, columnspan=2, padx=15, pady=(15, 5), sticky="w")
        
        # Propaga o hover para o label também
        self.lbl_header.bind("<Enter>", self.on_enter)
        self.lbl_header.bind("<Leave>", self.on_leave)

        # Botão Excel
        try:
            icon_path = "assets/excel_logo.png"
            if os.path.exists(icon_path):
                xls_img = ctk.CTkImage(Image.open(icon_path), size=(20, 20))
                btn_text = ""
            else:
                xls_img = None
                btn_text = "XLS"
                
            self.btn_xls = ctk.CTkButton(
                self, text=btn_text, image=xls_img, width=30, height=30,
                fg_color="#27ae60", hover_color="#2ecc71",
                command=lambda: self.on_excel_click(self.data)
            )
            self.btn_xls.grid(row=0, column=2, padx=10, pady=10, sticky="ne")
        except:
            pass

        # Linhas de Dados
        self._create_row("Leads:", data.get('Leads', 0), 1)
        self._create_row("Contatos Produtivos:", data.get('Contato Produtivo', 0), 2)
        self._create_row("Visitas Agendadas:", data.get('Visita Agendada', 0), 3)
        self._create_row("Visitas Realizadas:", data.get('Visita Realizada', 0), 4)
        
        # Matrículas (Destaque)
        self._create_row("Matrículas:", data.get('Matricula', 0), 5, is_bold=True)
        
        # Padding inferior
        ctk.CTkLabel(self, text="", height=5).grid(row=6, column=0)

    def _create_row(self, label_text, value, row_idx, is_bold=False):
        font_style = ("Roboto", 14, "bold") if is_bold else ("Roboto", 13)
        # Se for bold (Matrícula), usa azul escuro, senão cinza escuro
        val_color = "#2c3e50" if is_bold else "#505050"
        lbl_color = "#7f8c8d" # Cinza para o label
        
        lbl = ctk.CTkLabel(self, text=label_text, text_color=lbl_color, font=("Roboto", 12))
        lbl.grid(row=row_idx, column=0, padx=15, pady=2, sticky="w")
        
        # Propaga Hover
        lbl.bind("<Enter>", self.on_enter)
        lbl.bind("<Leave>", self.on_leave)

        try:
            val_str = f"{int(value):,}".replace(",", ".")
        except:
            val_str = str(value)
            
        val = ctk.CTkLabel(self, text=val_str, text_color=val_color, font=font_style)
        val.grid(row=row_idx, column=1, columnspan=2, padx=15, pady=2, sticky="e")
        
        # Propaga Hover
        val.bind("<Enter>", self.on_enter)
        val.bind("<Leave>", self.on_leave)

    def on_enter(self, event):
        # Lógica simples: alterna entre laranja e azul baseado no ID ou aleatório, 
        # ou fixa uma cor. Aqui farei uma mescla: se for par azul, impar laranja (exemplo)
        # Para simplificar e ficar bonito visualmente: Laranja ao passar o mouse.
        self.configure(border_color=self.hover_orange)

    def on_leave(self, event):
        self.configure(border_color=self.default_border)