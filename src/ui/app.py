import customtkinter as ctk
import os
from PIL import Image
from src.ui.screens.funil_screen import MonitoringScreen

class GradientFrame(ctk.CTkFrame):
    def __init__(self, parent, color1, color2, **kwargs):
        super().__init__(parent, **kwargs)
        self.color1 = color1
        self.color2 = color2
        self.canvas = ctk.CTkCanvas(self, highlightthickness=0)
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.bind("<Configure>", self._draw_gradient)

    def _draw_gradient(self, event=None):
        self.canvas.delete("gradient")
        width = self.winfo_width()
        height = self.winfo_height()
        if width < 1 or height < 1: return
        
        # Simples gradiente vertical
        r1, g1, b1 = self.winfo_rgb(self.color1)
        r2, g2, b2 = self.winfo_rgb(self.color2)
        r1, g1, b1 = r1 >> 8, g1 >> 8, b1 >> 8
        r2, g2, b2 = r2 >> 8, g2 >> 8, b2 >> 8
        
        limit = height
        for i in range(limit):
            nr = int(r1 + (r2 - r1) * i / limit)
            ng = int(g1 + (g2 - g1) * i / limit)
            nb = int(b1 + (b2 - b1) * i / limit)
            color = f'#{nr:02x}{ng:02x}{nb:02x}'
            self.canvas.create_line(0, i, width, i, fill=color)

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Raiz Educação - Sistema de Monitoramento")
        self.geometry("1366x768")
        ctk.set_appearance_mode("Light")
        
        # --- BACKGROUND ---
        # Usando cores da Raiz (Laranja suave e Azul suave)
        self.bg_frame = GradientFrame(self, color1="#ffffff", color2="#ecf0f1")
        self.bg_frame.pack(fill="both", expand=True)

        # --- TOP BAR (Transparente e Clean) ---
        self.top_bar = ctk.CTkFrame(self.bg_frame, height=60, fg_color="transparent")
        self.top_bar.pack(side="top", fill="x", padx=30, pady=(15, 5))
        
        # Logo Logic
        logo_path = "assets/raizeducacao_logo.png"
        if os.path.exists(logo_path):
            pil_img = Image.open(logo_path)
            # Mantém aspect ratio fixando altura em 40px
            ratio = 40 / pil_img.height
            new_w = int(pil_img.width * ratio)
            logo_img = ctk.CTkImage(light_image=pil_img, size=(new_w, 40))
            
            # Label sem texto, apenas imagem, bg transparente
            lbl_logo = ctk.CTkLabel(self.top_bar, text="", image=logo_img)
            lbl_logo.pack(side="left")
        else:
            # Fallback textual estiloso
            ctk.CTkLabel(self.top_bar, text="RAIZ", font=("Roboto", 24, "bold"), text_color="#e67e22").pack(side="left")
            ctk.CTkLabel(self.top_bar, text="EDUCAÇÃO", font=("Roboto", 24), text_color="#2c3e50").pack(side="left", padx=5)

        # Informações de Usuário/Data no canto direito (Opcional, dá um toque profissional)
        ctk.CTkLabel(self.top_bar, text="Dashboard Executivo", font=("Roboto", 12), text_color="#7f8c8d").pack(side="right")

        # --- CONTENT WRAPPER ---
        # Frame branco flutuante com sombra suave (simulada)
        self.content_wrapper = ctk.CTkFrame(self.bg_frame, fg_color="#f4f6f8", corner_radius=20)
        self.content_wrapper.pack(fill="both", expand=True, padx=30, pady=(10, 30))
        
        # Grid layout para telas
        self.content_wrapper.grid_rowconfigure(0, weight=1)
        self.content_wrapper.grid_columnconfigure(0, weight=1)

        self.frames = {}
        frame = MonitoringScreen(parent=self.content_wrapper, controller=self)
        self.frames["MonitoringScreen"] = frame
        frame.grid(row=0, column=0, sticky="nsew")
        
        frame.tkraise()

if __name__ == "__main__":
    app = App()
    app.mainloop()