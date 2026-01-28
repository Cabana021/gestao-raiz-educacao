import customtkinter as ctk
import os
from src.ui.screens.funil_screen import MonitoringScreen

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Sistema de Monitoramento - Raiz Educação")
        self.geometry("1100x750")
        
        # Configuração de Ícone da Janela
        try:
            icon_path = "assets/raizeducacao_logo.ico"
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception as e:
            print(f"Erro ao carregar ícone: {e}")
            
        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("blue")
        
        # Container Principal
        self.container = ctk.CTkFrame(self)
        self.container.pack(side="top", fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)
        
        self.frames = {}
        
        # Carrega a tela de Monitoramento
        frame = MonitoringScreen(parent=self.container, controller=self)
        self.frames["MonitoringScreen"] = frame
        frame.grid(row=0, column=0, sticky="nsew")
        
        self.show_frame("MonitoringScreen")
        
    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()