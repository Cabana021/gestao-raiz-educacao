import customtkinter as ctk
from PIL import Image
import os

class MainMenu(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#ecf0f1") # Fundo cinza bem claro
        self.controller = controller

        # Layout Grid para centralizar tudo
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1) # Espaço topo
        self.grid_rowconfigure(3, weight=1) # Espaço base

        # --- 1. LOGO NO TOPO ---
        self.logo_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.logo_frame.grid(row=0, column=0, columnspan=2, sticky="s", pady=(40, 50))
        
        try:
            logo_path = "assets/raizeducacao_logo.png"
            if os.path.exists(logo_path):
                pil_img = Image.open(logo_path)
                # Ajuste de tamanho da logo principal
                logo_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(300, 75))
                ctk.CTkLabel(self.logo_frame, image=logo_img, text="").pack()
            else:
                # Fallback se não tiver imagem
                ctk.CTkLabel(self.logo_frame, text="RAIZ EDUCAÇÃO", 
                             font=("Roboto", 40, "bold"), text_color="#203764").pack()
        except:
            pass

        ctk.CTkLabel(self.logo_frame, text="Selecione o módulo de automação", 
                     font=("Roboto", 16), text_color="#7f8c8d").pack(pady=(10, 0))

        # --- 2. CARDS DE NAVEGAÇÃO ---
        
        # Definição dos cards
        self.create_module_card(
            row=1, col=0, 
            title="FUNIL DE VENDAS", 
            desc="Monitoramento de Leads, Agendamentos e Matrículas.",
            color="#203764", # Azul Raiz
            target_screen="MonitoringScreen",
            icon_emoji="📊"
        )

        self.create_module_card(
            row=1, col=1, 
            title="PENDÊNCIAS", 
            desc="Gestão de tarefas e validações pendentes.",
            color="#F36F21", # Laranja Raiz
            target_screen="PendenciasScreen",
            icon_emoji="📝"
        )

    def create_module_card(self, row, col, title, desc, color, target_screen, icon_emoji):
        """Cria um botão grande estilo Card"""
        
        card = ctk.CTkButton(
            self,
            text=f"{icon_emoji}\n\n{title}\n\n{desc}",
            font=("Roboto", 16, "bold"),
            fg_color="white",
            text_color=color,
            hover_color="#dfe6e9",
            border_width=2,
            border_color=color,
            corner_radius=15,
            width=350,
            height=250,
            command=lambda: self.controller.show_frame(target_screen)
        )
        
        # Ajuste fino da fonte da descrição (hack para multi-line button styling simples)
        # O CTkButton não suporta estilos mistos nativamente no texto, 
        # então usamos espaçamento e quebras de linha para simular.
        
        card.grid(row=row, column=col, padx=20, pady=20)