import customtkinter as ctk
import threading
import time
import os
import logging
from datetime import datetime
from src.utils.config_manager import load_business_config

# --- CORREÇÃO 1: Importações Atualizadas ---
from src.engines.pendencia.engine import PendenciaEngine
from src.engines.pendencia.regras import ProcessadorRegras
from src.engines.pendencia.report import PendenciaReporter

# --- Configuração Visual (Cores) ---
class Colors:
    PRIMARY_BLUE = "#203764"
    ACCENT_ORANGE = "#F36F21"
    BACKGROUND = "#F5F6FA"
    CARD_BG = "#FFFFFF"
    TEXT_DARK = "#2D3436"
    TEXT_LIGHT = "#636E72"
    SUCCESS = "#00B894"
    WARNING = "#FDCB6E"
    DANGER = "#D63031"

class MetricCard(ctk.CTkFrame):
    """Componente visual para os KPIs"""
    def __init__(self, parent, title, value, icon_color=Colors.PRIMARY_BLUE, **kwargs):
        super().__init__(parent, fg_color=Colors.CARD_BG, corner_radius=10, border_width=1, border_color="#E0E0E0", **kwargs)
        self.status_strip = ctk.CTkFrame(self, width=5, fg_color=icon_color, corner_radius=0)
        self.status_strip.pack(side="left", fill="y", padx=(0, 10))
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        self.lbl_title = ctk.CTkLabel(content_frame, text=title.upper(), font=("Roboto Medium", 11), text_color=Colors.TEXT_LIGHT, anchor="w")
        self.lbl_title.pack(fill="x")
        self.lbl_value = ctk.CTkLabel(content_frame, text=str(value), font=("Roboto", 28, "bold"), text_color=Colors.TEXT_DARK, anchor="w")
        self.lbl_value.pack(fill="x", pady=(5, 0))

    def update_value(self, new_value):
        self.lbl_value.configure(text=str(new_value))

class PendenciasScreen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=Colors.BACKGROUND, corner_radius=0)
        self.controller = controller # Referência ao App principal
        
        # 1. Inicialização das Engines (Backend)
        self._init_backend()
        
        # 2. Construção do Layout
        self._setup_layout()
        
        # Estado dos Dados (Para guardar entre o Atualizar e o Exportar)
        self.df_atual = None
        self.dados_carregados = False

    def _init_backend(self):
        """Prepara as classes de lógica, mas NÃO carrega dados pesados ainda."""
        self.config = load_business_config()
        
        # Configura caminhos
        caminho_relativo = self.config.get('caminhos', {}).get('historico_pendencia', "historico_dados_local/Pendentes")
        
        if os.path.isabs(caminho_relativo):
            self.pasta_historico = caminho_relativo
        else:
            self.pasta_historico = os.path.join(os.getcwd(), caminho_relativo)
            
        os.makedirs(self.pasta_historico, exist_ok=True)

        # --- CORREÇÃO 2: Instanciação das Classes Corretas ---
        self.loader = PendenciaEngine()          # Nome atualizado
        self.regras = ProcessadorRegras(self.config) # Nome atualizado (passando config)
        self.reporter = PendenciaReporter(self.config, self.pasta_historico)

    def _setup_layout(self):
        # Grid Principal
        self.grid_columnconfigure(0, weight=1) # Coluna da esquerda (conteúdo)
        self.grid_columnconfigure(1, weight=0) # Coluna da direita (Painel de Ação)
        self.grid_rowconfigure(0, weight=1)

        # --- Área de Conteúdo (Esquerda) ---
        self.main_content = ctk.CTkFrame(self, fg_color="transparent")
        self.main_content.grid(row=0, column=0, sticky="nsew", padx=30, pady=30)
        
        # Título
        lbl_title = ctk.CTkLabel(self.main_content, text="Monitoramento de Pendências", font=("Roboto", 24, "bold"), text_color=Colors.PRIMARY_BLUE)
        lbl_title.pack(anchor="w")
        lbl_sub = ctk.CTkLabel(self.main_content, text="Visão em tempo real do CRM e Secretaria", font=("Roboto", 12), text_color=Colors.TEXT_LIGHT)
        lbl_sub.pack(anchor="w", pady=(0, 20))

        # Grid de Cards
        self.cards_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.cards_frame.pack(fill="x", expand=False)
        self.cards_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Cards Linha 1
        self.card_total = MetricCard(self.cards_frame, "Total Pendências", "---", Colors.PRIMARY_BLUE)
        self.card_total.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        self.card_critico = MetricCard(self.cards_frame, "Crítico (>90d)", "---", Colors.DANGER)
        self.card_critico.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.card_novos = MetricCard(self.cards_frame, "Novos (<7d)", "---", Colors.SUCCESS)
        self.card_novos.grid(row=0, column=2, padx=10, pady=10, sticky="ew")

        # Cards Linha 2
        self.card_remat = MetricCard(self.cards_frame, "Rematrícula", "---", Colors.ACCENT_ORANGE)
        self.card_remat.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        self.card_capt = MetricCard(self.cards_frame, "Captação", "---", Colors.ACCENT_ORANGE)
        self.card_capt.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        # --- Painel de Ação (Direita) ---
        self.action_panel = ctk.CTkFrame(self, fg_color="white", width=250, corner_radius=0)
        self.action_panel.grid(row=0, column=1, sticky="nsew")
        
        ctk.CTkLabel(self.action_panel, text="Ações", font=("Roboto", 16, "bold"), text_color=Colors.PRIMARY_BLUE).pack(pady=(30, 20))

        self.btn_update = ctk.CTkButton(self.action_panel, text="BUSCAR DADOS (SQL)", height=50, fg_color=Colors.PRIMARY_BLUE, command=self.acao_atualizar_dados)
        self.btn_update.pack(padx=20, pady=10, fill="x")

        self.btn_export = ctk.CTkButton(self.action_panel, text="GERAR EXCEL", height=50, fg_color=Colors.ACCENT_ORANGE, state="disabled", command=self.acao_exportar_excel)
        self.btn_export.pack(padx=20, pady=10, fill="x")

        self.lbl_status = ctk.CTkLabel(self.action_panel, text="Aguardando comando...", text_color="gray", font=("Roboto", 11), wraplength=200)
        self.lbl_status.pack(side="bottom", pady=30)

    # --- Lógica Conectada ---

    def acao_atualizar_dados(self):
        self.btn_update.configure(state="disabled")
        self.lbl_status.configure(text="Conectando ao Banco de Dados...", text_color=Colors.ACCENT_ORANGE)
        threading.Thread(target=self._worker_atualizar).start()

    def _worker_atualizar(self):
        try:
            # 1. Extração
            df_bruto = self.loader.get_pendentes()
            set_matriculados = self.loader.get_matriculados_ra()
            
            if df_bruto is None or df_bruto.empty:
                raise Exception("Nenhum dado retornado do SQL.")

            # 2. Regras de Negócio (Enriquecimento)
            # --- CORREÇÃO 3: Método correto 'aplicar_regras' ---
            self.df_atual = self.regras.aplicar_regras(df_bruto, set_matriculados)
            
            # 3. Cálculos para UI
            kpis = {
                'total': len(self.df_atual),
                'critico': len(self.df_atual[self.df_atual['Status_Prioridade'] == 'Crítico']),
                'novos': len(self.df_atual[self.df_atual['Dias_Pendente'] <= 7]),
                'remat': len(self.df_atual[self.df_atual['Tipo_Matricula'].str.contains('REMATRÍCULA', case=False, na=False)]),
                'capt': len(self.df_atual[self.df_atual['Tipo_Matricula'].str.contains('MATRÍCULA', case=False, na=False)])
            }

            # Atualiza UI na Thread Principal
            self.after(0, lambda: self._finalizar_atualizacao(kpis, sucesso=True))

        except Exception as e:
            logging.error(f"Erro UI Update: {e}")
            self.after(0, lambda: self._finalizar_atualizacao(msg=str(e), sucesso=False))

    def _finalizar_atualizacao(self, kpis=None, msg="", sucesso=False):
        self.btn_update.configure(state="normal")
        
        if sucesso:
            # Atualiza os Cards
            self.card_total.update_value(kpis['total'])
            self.card_critico.update_value(kpis['critico'])
            self.card_novos.update_value(kpis['novos'])
            self.card_remat.update_value(kpis['remat'])
            self.card_capt.update_value(kpis['capt'])
            
            self.lbl_status.configure(text="Dados Atualizados!", text_color=Colors.SUCCESS)
            self.btn_export.configure(state="normal") # Habilita o botão exportar
            self.dados_carregados = True
        else:
            self.lbl_status.configure(text=f"Erro: {msg}", text_color=Colors.DANGER)

    def acao_exportar_excel(self):
        if not self.dados_carregados or self.df_atual is None:
            return

        self.btn_export.configure(state="disabled", text="Gerando...")
        self.lbl_status.configure(text="Gerando relatórios Excel...", text_color=Colors.PRIMARY_BLUE)
        threading.Thread(target=self._worker_exportar).start()

    def _worker_exportar(self):
        try:
            self.reporter.gerar_por_marca(
                df_atual=self.df_atual,
                pasta_destino=self.pasta_historico,
                business_obj=self.regras 
            )
            self.after(0, lambda: self._finalizar_exportacao(True))
        except Exception as e:
            logging.error(f"Erro Export: {e}")
            self.after(0, lambda: self._finalizar_exportacao(False))

    def _finalizar_exportacao(self, sucesso):
        self.btn_export.configure(state="normal", text="GERAR EXCEL")
        if sucesso:
            self.lbl_status.configure(text=f"Relatórios salvos em:\n{os.path.basename(self.pasta_historico)}", text_color=Colors.SUCCESS)
        else:
            self.lbl_status.configure(text="Erro ao gerar Excel.", text_color=Colors.DANGER)