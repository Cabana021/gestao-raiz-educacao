import customtkinter as ctk
from PIL import Image
import os

class InfoCard(ctk.CTkFrame):
    def __init__(self, parent, data, on_excel_click, **kwargs):
        super().__init__(parent, **kwargs)
        self.data = data
        self.on_excel_click = on_excel_click # Callback function
        
        # Definição de Cores por Marca 
        marca_lower = str(data.get('unidade', '')).lower()
        
        if "total" in marca_lower:
            card_color = "#2c3e50" # Cinza Escuro (Destaque Total)
            border_col = "#f1c40f"
        elif "escola a" in marca_lower:
            card_color = "#d35400" # Laranja (Pumpkin)
            border_col = "#e67e22"
        elif "escola b" in marca_lower:
            card_color = "#2980b9" # Azul (Belize)
            border_col = "#3498db"
        else:
            card_color = "#7f8c8d" # Cinza Genérico
            border_col = "#bdc3c7"
            
        self.configure(fg_color=card_color, corner_radius=15, border_width=2, border_color=border_col)
        
        # Grid Interno
        self.grid_columnconfigure(1, weight=1)
        
        # Cabeçalho: Nome da Unidade/Marca 
        header_text = f"{data.get('unidade', 'N/A')}"
        self.lbl_header = ctk.CTkLabel(
            self, text=header_text, text_color="white",
            font=("Roboto", 18, "bold"), justify="left"
        )
        self.lbl_header.grid(row=0, column=0, columnspan=2, padx=15, pady=(15, 5), sticky="w")
        
        # Botão Excel 
        try:
            # Tenta carregar icone, se não tiver, usa texto "XLS"
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
            pass # Ignora erro de imagem

        # Linhas de Dados 
        self._create_row("Leads:", data.get('Leads', 0), 1)
        self._create_row("Contatos Produtivos:", data.get('Contato Produtivo', 0), 2)
        self._create_row("Visitas Agendadas:", data.get('Visita Agendada', 0), 3)
        self._create_row("Visitas Realizadas:", data.get('Visita Realizada', 0), 4)
        
        # Matrículas 
        self._create_row("Matrículas:", data.get('Matricula', 0), 5, is_bold=True)
        
        # Padding inferior
        ctk.CTkLabel(self, text="", height=10).grid(row=6, column=0)

    def _create_row(self, label_text, value, row_idx, is_bold=False):
        font_style = ("Roboto", 14, "bold") if is_bold else ("Roboto", 13)
        val_color = "#f1c40f" if is_bold else "white"
        
        lbl = ctk.CTkLabel(self, text=label_text, text_color="#ecf0f1", font=("Roboto", 12))
        lbl.grid(row=row_idx, column=0, padx=15, pady=2, sticky="w")
        
        # Formatação de milhar se for número
        try:
            val_str = f"{int(value):,}".replace(",", ".")
        except:
            val_str = str(value)
            
        val = ctk.CTkLabel(self, text=val_str, text_color=val_color, font=font_style)
        val.grid(row=row_idx, column=1, columnspan=2, padx=15, pady=2, sticky="e")