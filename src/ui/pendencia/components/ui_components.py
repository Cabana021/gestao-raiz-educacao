import customtkinter as ctk

class InfoCard(ctk.CTkFrame):
    """
    Componente visual que representa um Card de Informação.
    Herda de CTkFrame para permitir estilização e layout flexível.
    """
    
    def __init__(self, parent, data, index, **kwargs):
        super().__init__(parent, **kwargs)
        
        # --- Definição de Cores ---
        # Laranja (Aprox. Pumpkin) e Azul (Aprox. Belize Hole)
        COLOR_ORANGE = "#d35400" 
        COLOR_BLUE = "#2980b9"
        TEXT_COLOR = "#FFFFFF"
        
        # --- Lógica de Intercalação ---
        # Se o índice for par: Laranja. Se ímpar: Azul.
        card_color = COLOR_ORANGE if index % 2 == 0 else COLOR_BLUE
        
        # Configuração do Frame (Borda leve e cor de fundo)
        self.configure(
            fg_color=card_color,
            corner_radius=15,
            border_width=2,
            border_color="#ecf0f1"
        )
        
        # Configuração de Grid Interno do Card
        self.grid_columnconfigure(1, weight=1) # Coluna de valores expande
        
        # --- Cabeçalho: Marca e Filial ---
        header_text = f"{data['marca']}\n{data['filial']}"
        self.lbl_header = ctk.CTkLabel(
            self, 
            text=header_text, 
            text_color=TEXT_COLOR,
            font=("Roboto", 18, "bold"),
            justify="left"
        )
        self.lbl_header.grid(row=0, column=0, columnspan=2, padx=15, pady=(15, 10), sticky="w")
        
        # --- Campos de Dados ---
        # Helper function para criar linhas
        self._create_row("Total de Alunos:", data['total_alunos'], 1)
        self._create_row("Turmas Envolvidas:", data['turmas_envolvidas'], 2)
        
        # Separador visual simples (Espaçamento)
        
        # --- Campos de Prioridade (Destaque Visual) ---
        # Prioridade Crítica ganha destaque se valor > 0
        crit_color = "#f1c40f" if data['prioridade_critica'] > 0 else TEXT_COLOR # Amarelo se tiver crítico
        crit_font = ("Roboto", 14, "bold") if data['prioridade_critica'] > 0 else ("Roboto", 14)
        
        self._create_row("Prioridade Crítica:", data['prioridade_critica'], 3, value_color=crit_color, value_font=crit_font)
        self._create_row("Atenção / Médio:", data['atencao_medio'], 4)
        self._create_row("Pendências Novas:", data['pendencias_novas'], 5)
        
        # Padding inferior
        self.lbl_spacer = ctk.CTkLabel(self, text="", height=10)
        self.lbl_spacer.grid(row=6, column=0)

    def _create_row(self, label_text, value, row_idx, value_color="white", value_font=("Roboto", 14)):
        """Cria uma linha padronizada de Label + Valor"""
        
        lbl = ctk.CTkLabel(
            self, 
            text=label_text, 
            text_color="#ecf0f1", # Branco levemente off-white para o label
            font=("Roboto", 12)
        )
        lbl.grid(row=row_idx, column=0, padx=15, pady=2, sticky="w")
        
        val = ctk.CTkLabel(
            self, 
            text=str(value), 
            text_color=value_color,
            font=value_font
        )
        val.grid(row=row_idx, column=1, padx=15, pady=2, sticky="e")
