import customtkinter as ctk
from PIL import Image
import os


class MainMenu(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#1a1a1a")
        self.controller = controller

        # Cores
        self.colors = {
            "blue_raiz": "#203764",
            "blue_light": "#4a90e2",
            "orange_raiz": "#F36F21",
            # Cores de Interface
            "text_white": "#FFFFFF",
            "text_gray": "#A0A0A0",
            # Cores do Card
            "card_bg": "#242424",
            "card_hover": "#2f2f2f",
            "card_border_dim": "#404040",
        }

        # Grid Principal
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # 1. Header
        self.setup_header()

        # 2. Área dos cards
        self.setup_cards_area()

    def setup_header(self):
        """Organiza a Logo e o Título principal"""
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=1, column=0, sticky="ew", pady=(0, 40))
        self.header_frame.grid_columnconfigure(0, weight=1)

        # Carregamento da Logo
        logo_path = os.path.join("assets", "raizeducacao_logo.png")

        try:
            if os.path.exists(logo_path):
                pil_img = Image.open(logo_path)
                # Mantendo proporção correta
                h = 90
                w = int(h * (pil_img.width / pil_img.height))

                logo_ctk = ctk.CTkImage(
                    light_image=pil_img, dark_image=pil_img, size=(w, h)
                )
                ctk.CTkLabel(self.header_frame, text="", image=logo_ctk).grid(
                    row=0, column=0, pady=(0, 15)
                )
            else:
                raise FileNotFoundError
        except:
            ctk.CTkLabel(
                self.header_frame,
                text="RAIZ EDUCAÇÃO",
                font=("Roboto", 32, "bold"),
                text_color=self.colors["orange_raiz"],
            ).grid(row=0, column=0, pady=(0, 15))

        # Textos
        ctk.CTkLabel(
            self.header_frame,
            text="Gestão Raiz Educação",
            font=("Roboto Medium", 26),
            text_color=self.colors["text_white"],
        ).grid(row=1, column=0)

        ctk.CTkLabel(
            self.header_frame,
            text="Selecione o módulo de automação",
            font=("Roboto", 14),
            text_color=self.colors["text_gray"],
        ).grid(row=2, column=0, pady=(5, 0))

    def setup_cards_area(self):
        """Container e Definição dos Cards"""
        self.cards_container = ctk.CTkFrame(self, fg_color="transparent")
        self.cards_container.grid(row=2, column=0, pady=10)

        # Card 1: Funil de Vendas
        self.create_module_card(
            parent=self.cards_container,
            col=0,
            title="FUNIL DE VENDAS",
            desc="Monitoramento de Leads,\nAgendamentos e Matrículas.",
            icon_filename="leads_logo.png",
            border_color=self.colors["blue_light"],
            target_screen="MonitoringScreen",
        )

        # Card 2: Pendências
        self.create_module_card(
            parent=self.cards_container,
            col=1,
            title="PENDÊNCIAS",
            desc="Gestão de tarefas e\nvalidações pendentes.",
            icon_filename="alunos_logo.png",
            border_color=self.colors["orange_raiz"],
            target_screen="PendenciasScreen",
        )

    def load_icon(self, filename):
        """Helper seguro para carregar ícones PNG"""
        icon_path = os.path.join("assets", filename)
        try:
            if os.path.exists(icon_path):
                img = Image.open(icon_path)
                # Tamanho padrão do ícone: 48x48
                return ctk.CTkImage(light_image=img, dark_image=img, size=(48, 48))
        except Exception as e:
            print(f"Erro ao carregar ícone {filename}: {e}")
        return None

    def create_module_card(
        self, parent, col, title, desc, icon_filename, border_color, target_screen
    ):
        """Cria card com imagem real e hover sutil"""

        # 1. Carregar Ícone
        icon_image = self.load_icon(icon_filename)

        # 2. Configurar Texto
        # Apenas título e descrição aqui, o ícone vai via propriedade 'image'
        text_content = f"\n{title}\n\n{desc}"

        # 3. Criar Botão
        card_btn = ctk.CTkButton(
            parent,
            text=text_content,
            image=icon_image,  # Imagem carregada
            compound="top",  # Imagem acima do texto
            font=("Roboto", 15),
            text_color=self.colors["text_white"],
            # Hover
            fg_color=self.colors["card_bg"],  # Cor base (Dark Gray)
            hover_color=self.colors["card_hover"],  # Cor hover (Light Gray - sutil)
            # Identidade visual via Borda
            border_width=2,
            border_color=border_color,
            corner_radius=15,
            width=320,
            height=220,
            command=lambda: self.controller.show_frame(target_screen),
        )

        card_btn.grid(row=0, column=col, padx=25, pady=10)
