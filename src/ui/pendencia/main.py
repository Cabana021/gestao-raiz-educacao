import customtkinter as ctk
import os
from PIL import Image

# --- Configurações da Janela Principal ---
self.title("Sistema de Monitoramento - Raiz Educação")
self.geometry("1000x700")

# Tema e Aparência
ctk.set_appearance_mode("Light") # Modo claro para melhor contraste com os cartões coloridos
ctk.set_default_color_theme("blue")

# Inicializa o Gerenciador de Banco de Dados
self.db_manager = DatabaseManager()

# Configuração do Layout Principal (Grid)
self.grid_rowconfigure(1, weight=1) # A linha do conteúdo (scroll) expande
self.grid_columnconfigure(0, weight=1)

# Inicializa a Interface
self.setup_header()
self.setup_content_area()

def setup_header(self):
    """Cria a barra superior com Botão e Logo."""
    self.header_frame = ctk.CTkFrame(self, height=80, fg_color="transparent")
    self.header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=10)
    self.header_frame.grid_columnconfigure(1, weight=1) # Espaço central expande

    # --- Botão Consultar (Centralizado/Esquerda) ---
    self.btn_consult = ctk.CTkButton(
        self.header_frame,
        text="Consultar Banco de Dados",
        command=self.start_consultation,
        height=45,
        width=200,
        font=("Roboto", 16, "bold"),
        fg_color="#2ecc71", # Verde para ação positiva
        hover_color="#27ae60",
        corner_radius=8
    )
    self.btn_consult.grid(row=0, column=0, padx=10, sticky="w")

    # --- Indicador de Carregamento (Inicialmente Oculto) ---
    self.lbl_loading = ctk.CTkLabel(
        self.header_frame,
        text="Carregando dados...",
        text_color="#e67e22",
        font=("Roboto", 14, "italic")
    )

    # --- Logo da Empresa (Direita) ---
    try:
        image_path = "assets/raizeducacao_logo.png"
        if os.path.exists(image_path):
            pil_image = Image.open(image_path)
            # Mantendo proporção: ajustamos largura fixa, altura automática
            base_width = 150
            w_percent = (base_width / float(pil_image.size[0]))
            h_size = int((float(pil_image.size[1]) * float(w_percent)))
            
            logo_img = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(base_width, h_size))
            
            self.lbl_logo = ctk.CTkLabel(self.header_frame, text="", image=logo_img)
            self.lbl_logo.grid(row=0, column=2, padx=10, sticky="e")
        else:
            self.lbl_logo = ctk.CTkLabel(self.header_frame, text="[LOGO RAIZ EDUCAÇÃO]", font=("Arial", 16, "bold"))
            self.lbl_logo.grid(row=0, column=2, padx=10, sticky="e")
    except Exception as e:
        print(f"Erro ao carregar logo: {e}")
        self.lbl_logo = ctk.CTkLabel(self.header_frame, text="RAIZ EDUCAÇÃO")
        self.lbl_logo.grid(row=0, column=2, padx=10, sticky="e")

def setup_content_area(self):
    """Cria a área rolável onde os cards aparecerão."""
    self.scroll_frame = ctk.CTkScrollableFrame(
        self, 
        label_text="Filiais e Marcas",
        label_font=("Roboto", 16, "bold")
    )
    self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
    
    # Configuração responsiva do grid interno do ScrollFrame
    # Vamos usar 2 colunas de cards por padrão
    self.scroll_frame.grid_columnconfigure(0, weight=1)
    self.scroll_frame.grid_columnconfigure(1, weight=1)