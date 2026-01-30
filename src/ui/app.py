import customtkinter as ctk
import os
from PIL import Image
from src.ui.screens.main_menu import MainMenu
from src.ui.screens.funil_screen import MonitoringScreen
from src.ui.screens.pendentes_screen import PendenciasScreen


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Raiz Educação - Sistema de Monitoramento")
        self.geometry("1280x720")
        ctk.set_appearance_mode("Light")

        # Tenta carregar o ícone da janela (.ico)
        try:
            icon_path = "assets/icon.ico"
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception as e:
            print(f"Aviso: Ícone não carregado. {e}")

        # Configuração do Grid Principal (Tela Cheia)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Container Principal onde as telas serão empilhadas
        self.container = ctk.CTkFrame(self, fg_color="#ecf0f1")
        self.container.grid(row=0, column=0, sticky="nsew")

        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        # Dicionário para armazenar as instâncias das telas
        self.frames = {}

        # Lista de classes de telas a serem instanciadas
        for F in (MainMenu, MonitoringScreen, PendenciasScreen):
            page_name = F.__name__
            frame = F(parent=self.container, controller=self)
            self.frames[page_name] = frame

            # Coloca todas as telas na mesma posição (empilhadas)
            frame.grid(row=0, column=0, sticky="nsew")

        # Inicia mostrando o Menu Principal
        self.show_frame("MainMenu")

    def show_frame(self, page_name):
        """Traz a tela solicitada para o topo da pilha visual"""
        frame = self.frames[page_name]
        frame.tkraise()

    def go_home(self):
        """Retorna para o menu principal"""
        self.show_frame("MainMenu")


if __name__ == "__main__":
    app = App()
    app.mainloop()
