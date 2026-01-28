import customtkinter as ctk
from PIL import Image
import os
import threading
import pandas as pd
from tkinter import messagebox
from src.ui.components.info_card import InfoCard
from engine import FunnelEngine # Seu engine.py
from src.utils.report_handler import ReportHandler # O adaptador do report.py

class MonitoringScreen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.engine = FunnelEngine() # Instancia o motor de dados
        self.current_data = None     # Guarda os dados carregados
        
        # Layout
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.setup_header()
        self.setup_scroll_area()
        
    def setup_header(self):
        header_frame = ctk.CTkFrame(self, height=80, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=15)
        header_frame.grid_columnconfigure(2, weight=1)

        # Botões Principais
        self.btn_consult = ctk.CTkButton(
            header_frame, text="Consultar Banco de Dados",
            command=self.start_consultation_thread,
            height=40, font=("Roboto", 14, "bold"),
            fg_color="#2980b9", hover_color="#2573a7"
        )
        self.btn_consult.grid(row=0, column=0, padx=(0, 10), sticky="w")
        
        self.btn_excel_all = ctk.CTkButton(
            header_frame, text="Gerar Relatório Geral",
            command=self.export_full_excel,
            height=40, font=("Roboto", 14, "bold"),
            fg_color="#27ae60", hover_color="#219150"
        )
        self.btn_excel_all.grid(row=0, column=1, padx=10, sticky="w")
        
        # Status Label
        self.lbl_status = ctk.CTkLabel(header_frame, text="", text_color="gray")
        self.lbl_status.grid(row=1, column=0, columnspan=2, sticky="w")

        # LOGO (Direita)
        try:
            logo_path = "assets/raizeducacao_logo.png"
            if os.path.exists(logo_path):
                pil_img = Image.open(logo_path)
                # Redimensiona mantendo proporção
                w, h = pil_img.size
                ratio = 50 / h
                new_w = int(w * ratio)
                
                logo_img = ctk.CTkImage(pil_img, size=(new_w, 50))
                self.lbl_logo = ctk.CTkLabel(header_frame, text="", image=logo_img)
            else:
                self.lbl_logo = ctk.CTkLabel(header_frame, text="RAIZ EDUCAÇÃO", font=("Arial", 20, "bold"))
                
            self.lbl_logo.grid(row=0, column=3, sticky="e")
        except Exception as e:
            print(f"Erro logo: {e}")

    def setup_scroll_area(self):
        self.scroll_frame = ctk.CTkScrollableFrame(
            self, label_text="Painel de Unidades", 
            label_font=("Roboto", 16, "bold"), fg_color="transparent"
        )
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.scroll_frame.grid_columnconfigure(0, weight=1)
        self.scroll_frame.grid_columnconfigure(1, weight=1)

    # --- Lógica de Dados (Threading para não travar a UI) ---
    def start_consultation_thread(self):
        self.btn_consult.configure(state="disabled", text="Consultando...")
        self.lbl_status.configure(text="Conectando ao banco de dados...", text_color="#e67e22")
        
        thread = threading.Thread(target=self.run_consultation)
        thread.start()

    def run_consultation(self):
        try:
            # Chama o método do seu engine.py
            df = self.engine.generate_full_report()
            
            # Atualiza UI na thread principal
            self.after(0, lambda: self.update_ui_with_data(df))
        except Exception as e:
            print(f"Erro Engine: {e}")
            self.after(0, lambda: self.show_error(str(e)))

    def update_ui_with_data(self, df):
        # Reabilita botão
        self.btn_consult.configure(state="normal", text="Consultar Banco de Dados")
        self.lbl_status.configure(text="Dados atualizados com sucesso.", text_color="green")
        
        if df is None or df.empty:
            self.lbl_status.configure(text="Nenhum dado encontrado.", text_color="red")
            return

        # --- Cálculo do TOTAL ---
        cols_sum = ["Leads", "Contato Produtivo", "Visita Agendada", "Visita Realizada", "Matricula"]
        total_row = df[cols_sum].sum()
        total_data = total_row.to_dict()
        total_data["unidade"] = "TOTAL GERAL"
        
        # Converte o DF original para lista de dicts
        records = df.to_dict('records')
        
        # Insere o TOTAL como primeiro item da lista
        full_data = [total_data] + records
        self.current_data = pd.DataFrame(full_data) # Salva para exportação

        # Limpa tela anterior
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        # Renderiza Cards
        for i, item in enumerate(full_data):
            # O card TOTAL (índice 0) deve ocupar as duas colunas ou ter destaque
            card = InfoCard(self.scroll_frame, data=item, on_excel_click=self.export_single_excel)
            
            if i == 0: # Card Total
                card.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
            else:
                row = (i + 1) // 2
                col = (i + 1) % 2
                card.grid(row=row, column=col, padx=10, pady=10, sticky="ew")

    # --- Exportação Excel ---
    def export_full_excel(self):
        if self.current_data is None: return
        self.lbl_status.configure(text="Gerando Excel Geral...", text_color="blue")
        
        success = ReportHandler.gerar_excel_consolidado(self.current_data, "Relatorio_Geral.xlsx")
        if success:
            messagebox.showinfo("Sucesso", "Relatório Geral gerado com sucesso!")
            self.lbl_status.configure(text="")

    def export_single_excel(self, card_data):
        name = card_data.get('unidade', 'Unidade')
        filename = f"Relatorio_{name}.xlsx".replace(" ", "_")
        
        success = ReportHandler.gerar_excel_individual(card_data, filename)
        if success:
             messagebox.showinfo("Sucesso", f"Relatório de {name} gerado!")

    def show_error(self, msg):
        self.btn_consult.configure(state="normal", text="Consultar Banco de Dados")
        self.lbl_status.configure(text=f"Erro: {msg}", text_color="red")