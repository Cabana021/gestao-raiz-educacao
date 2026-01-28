import customtkinter as ctk
import os
from PIL import Image
from src.ui.screens.funil_screen import MonitoringScreen

class GradientFrame(ctk.CTkFrame):
    """Frame customizado onde o Canvas fica em background absoluto via place()."""
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
        
        if width < 1 or height < 1: return # Evita erros na inicialização

        steps = 100
        r1, g1, b1 = self.winfo_rgb(self.color1)
        r2, g2, b2 = self.winfo_rgb(self.color2)
        
        # Converter 16-bit para 8-bit
        r1, g1, b1 = r1 >> 8, g1 >> 8, b1 >> 8
        r2, g2, b2 = r2 >> 8, g2 >> 8, b2 >> 8

        for i in range(steps):
            r = int(r1 + (r2 - r1) * i / steps)
            g = int(g1 + (g2 - g1) * i / steps)
            b = int(b1 + (b2 - b1) * i / steps)
            color = f'#{r:02x}{g:02x}{b:02x}'
            
            y0 = int(i * height / steps)
            y1 = int((i + 1) * height / steps)
            
            # width + 1 garante que preencha a direita sem gaps no redimensionamento
            self.canvas.create_rectangle(0, y0, width+1, y1 + 1, fill=color, outline=color, tags="gradient")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Sistema de Monitoramento - Raiz Educação")
        self.geometry("1280x720")
        
        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("blue")
        
        try:
            icon_path = "assets/raizeducacao_logo.ico"
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except:
            pass
            
        # 1. Background (Root Container)
        self.bg_frame = GradientFrame(self, color1="#fff3e0", color2="#e3f2fd") 
        self.bg_frame.pack(fill="both", expand=True)
        
        # 2. Top Bar
        self.top_bar = ctk.CTkFrame(self.bg_frame, height=70, fg_color="transparent")
        self.top_bar.pack(side="top", fill="x", padx=20, pady=(10, 5))
        
        try:
            logo_path = "assets/raizeducacao_logo.png"
            if os.path.exists(logo_path):
                pil_img = Image.open(logo_path)
                w, h = pil_img.size
                ratio = 50 / h
                new_size = (int(w * ratio), 50)
                
                logo_img = ctk.CTkImage(pil_img, size=new_size)
                self.lbl_logo = ctk.CTkLabel(self.top_bar, text="", image=logo_img)
                self.lbl_logo.pack(side="left")
            else:
                ctk.CTkLabel(self.top_bar, text="RAIZ EDUCAÇÃO", 
                             font=("Roboto", 24, "bold"), text_color="#e67e22").pack(side="left")
        except:
            pass

        # 3. Content Wrapper
        self.content_wrapper = ctk.CTkFrame(
            self.bg_frame,
            fg_color="#f5f6fa", 
            corner_radius=15
        )
        self.content_wrapper.pack(
            side="top",
            fill="both",
            expand=True,
            padx=20,
            pady=(5, 20) # Margem inferior
        )

        # Configuração do Grid para a tela filha ocupar tudo
        self.content_wrapper.grid_rowconfigure(0, weight=1)
        self.content_wrapper.grid_columnconfigure(0, weight=1)

        self.frames = {}
        
        # Instancia a tela
        frame = MonitoringScreen(parent=self.content_wrapper, controller=self)
        self.frames["MonitoringScreen"] = frame
        frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        
        self.show_frame("MonitoringScreen")
        
    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()

if __name__ == "__main__":
    app = App()
    app.mainloop()
