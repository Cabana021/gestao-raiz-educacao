import customtkinter as ctk
import threading
import os
import logging
import pandas as pd
from PIL import Image
from src.utils.config_manager import load_business_config
from src.engines.pendencia.engine import PendenciaEngine
from src.engines.pendencia.report import PendenciaReporter


# --- PALETA DE CORES DARK MODERN ---
class DarkTheme:
    BG_MAIN = "#141414"  # Fundo quase preto
    BG_SIDEBAR = "#1a1a1a"  # Sidebar original
    CARD_BG = "#262626"  # Cards cinza escuro
    CARD_HOVER = "#333333"  # Cards ao passar o mouse

    TEXT_MAIN = "#FFFFFF"  # Branco puro
    TEXT_SUB = "#A0A0A0"  # Cinza claro para labels
    TEXT_MUTED = "#606060"  # Cinza escuro para detalhes

    ACCENT_BLUE = "#3B8ED0"  # Azul CustomTKinter padrão (moderno)
    ACCENT_PURPLE = "#8E44AD"  # Roxo para destaques

    # Semáforo
    SUCCESS = "#00C853"  # Verde Matrix
    WARNING = "#FFAB00"  # Âmbar
    DANGER = "#FF3D00"  # Laranja avermelhado vibrante

    BORDER = "#404040"


class ModernMetricCard(ctk.CTkFrame):
    """Card KPI Moderno com Hover e Design Limpo"""

    def __init__(
        self,
        parent,
        title,
        value,
        subtext="",
        icon_color=DarkTheme.ACCENT_BLUE,
        **kwargs,
    ):
        super().__init__(
            parent,
            fg_color=DarkTheme.CARD_BG,
            corner_radius=12,
            border_width=1,
            border_color=DarkTheme.BORDER,
            **kwargs,
        )

        self.icon_color = icon_color

        # Grid interno
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Título
        self.grid_rowconfigure(1, weight=1)  # Valor
        self.grid_rowconfigure(2, weight=0)  # Subtexto

        # 1. Cabeçalho (Barra lateral + Título)
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent", height=30)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))

        # Indicador visual (Pill shape)
        self.indicator = ctk.CTkFrame(
            self.header_frame, width=8, height=8, corner_radius=4, fg_color=icon_color
        )
        self.indicator.pack(side="left", padx=(0, 8))

        self.lbl_title = ctk.CTkLabel(
            self.header_frame,
            text=title.upper(),
            font=("Inter", 11, "bold"),
            text_color=DarkTheme.TEXT_SUB,
        )
        self.lbl_title.pack(side="left")

        # 2. Valor Principal
        self.lbl_value = ctk.CTkLabel(
            self,
            text=str(value),
            font=("Inter", 32, "bold"),
            text_color=DarkTheme.TEXT_MAIN,
            anchor="w",
        )
        self.lbl_value.grid(row=1, column=0, sticky="w", padx=15, pady=0)

        # 3. Subtexto / Comparativo
        self.lbl_sub = ctk.CTkLabel(
            self,
            text=subtext,
            font=("Inter", 11),
            text_color=DarkTheme.TEXT_MUTED,
            anchor="w",
        )
        self.lbl_sub.grid(row=2, column=0, sticky="w", padx=15, pady=(0, 15))

        # Eventos de Hover
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

        # Propagar eventos para filhos (para o hover funcionar em tudo)
        for child in self.winfo_children():
            child.bind("<Enter>", self.on_enter)
            child.bind("<Leave>", self.on_leave)
            if isinstance(child, ctk.CTkFrame):
                for grand in child.winfo_children():
                    grand.bind("<Enter>", self.on_enter)
                    grand.bind("<Leave>", self.on_leave)

    def on_enter(self, event):
        self.configure(fg_color=DarkTheme.CARD_HOVER, border_color=self.icon_color)

    def on_leave(self, event):
        self.configure(fg_color=DarkTheme.CARD_BG, border_color=DarkTheme.BORDER)

    def update_data(self, value, subtext=None):
        self.lbl_value.configure(text=str(value))
        if subtext:
            self.lbl_sub.configure(text=subtext)


class PendenciasScreen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=DarkTheme.BG_MAIN, corner_radius=0)
        self.controller = controller

        self._init_backend()
        self._setup_layout()

        self.df_atual = None
        self.dados_carregados = False

    def _init_backend(self):
        self.config = load_business_config()
        # Configuração de caminhos (mantida do original)
        caminho_relativo = self.config.get("caminhos", {}).get(
            "historico_pendencia", "historico_dados_local/Pendentes"
        )
        self.pasta_historico = (
            os.path.abspath(caminho_relativo)
            if not os.path.isabs(caminho_relativo)
            else caminho_relativo
        )
        os.makedirs(self.pasta_historico, exist_ok=True)

        self.loader = PendenciaEngine()
        self.reporter = PendenciaReporter(self.config, self.pasta_historico)

    def _setup_layout(self):
        # Grid Principal: Sidebar Fixa (280px) | Conteúdo Fluido
        self.grid_columnconfigure(0, weight=0, minsize=280)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # === 1. SIDEBAR (Preservada Integramente) ===
        self.setup_sidebar()

        # === 2. ÁREA DE CONTEÚDO ===
        self.content_area = ctk.CTkFrame(self, fg_color="transparent")
        self.content_area.grid(row=0, column=1, sticky="nsew", padx=40, pady=40)

        # Layout Interno do Conteúdo
        self.content_area.grid_columnconfigure(0, weight=1)
        self.content_area.grid_rowconfigure(
            1, weight=1
        )  # Espaço para cards expandir ou tabela futura

        # A. Header
        self._setup_header()

        # B. Grid de KPIs
        self._setup_kpi_grid()

        # C. Actions Footer
        self._setup_footer()

    def _setup_header(self):
        header_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 30))

        title = ctk.CTkLabel(
            header_frame,
            text="Painel de Pendências",
            font=("Inter", 28, "bold"),
            text_color=DarkTheme.TEXT_MAIN,
        )
        title.pack(anchor="w")

        subtitle = ctk.CTkLabel(
            header_frame,
            text="Monitoramento em tempo real de inconsistências entre CRM e Secretaria Acadêmica.",
            font=("Inter", 14),
            text_color=DarkTheme.TEXT_SUB,
        )
        subtitle.pack(anchor="w")

    def _setup_kpi_grid(self):
        # Container Grid
        self.cards_container = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.cards_container.pack(fill="x", pady=(0, 20))

        # Configuração 4 colunas
        for i in range(4):
            self.cards_container.grid_columnconfigure(i, weight=1)

        # --- LINHA 1: Visão Geral ---
        self.card_total = ModernMetricCard(
            self.cards_container,
            "Total Pendentes",
            "---",
            "Alunos irregulares",
            icon_color=DarkTheme.ACCENT_BLUE,
        )
        self.card_total.grid(row=0, column=0, padx=(0, 10), pady=10, sticky="ew")

        self.card_critico = ModernMetricCard(
            self.cards_container,
            "Risco Crítico",
            "---",
            "> 90 dias sem resolução",
            icon_color=DarkTheme.DANGER,
        )
        self.card_critico.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.card_novos = ModernMetricCard(
            self.cards_container,
            "Novos Leads",
            "---",
            "Gerados na última semana",
            icon_color=DarkTheme.SUCCESS,
        )
        self.card_novos.grid(row=0, column=2, padx=10, pady=10, sticky="ew")

        self.card_filial_top = ModernMetricCard(
            self.cards_container,
            "Maior Ofensor",
            "---",
            "Filial com mais casos",
            icon_color=DarkTheme.WARNING,
        )
        self.card_filial_top.grid(row=0, column=3, padx=(10, 0), pady=10, sticky="ew")

        # --- LINHA 2: Detalhamento (Opcional, mas útil) ---
        # Adicionei uma segunda linha para aproveitar o espaço
        self.card_curso_top = ModernMetricCard(
            self.cards_container,
            "Curso Crítico",
            "---",
            "Curso com mais pendências",
            icon_color=DarkTheme.ACCENT_PURPLE,
        )
        self.card_curso_top.grid(
            row=1, column=0, columnspan=2, padx=(0, 10), pady=10, sticky="ew"
        )

        self.card_remat = ModernMetricCard(
            self.cards_container,
            "Rematrículas",
            "---",
            "Alunos veteranos pendentes",
            icon_color=DarkTheme.TEXT_SUB,
        )
        self.card_remat.grid(
            row=1, column=2, columnspan=2, padx=(10, 0), pady=10, sticky="ew"
        )

    def _setup_footer(self):
        self.footer = ctk.CTkFrame(self.content_area, fg_color="transparent", height=60)
        self.footer.pack(fill="x", side="bottom", pady=20)

        # Status Label
        self.lbl_status = ctk.CTkLabel(
            self.footer,
            text="Aguardando sincronização...",
            font=("Inter", 12),
            text_color=DarkTheme.TEXT_MUTED,
        )
        self.lbl_status.pack(side="left")

        # Carrega o ícone de Excel
        self.excel_icon = None
        try:
            # Tenta carregar o ícone se existir
            if os.path.exists("assets/excel_logo.png"):
                self.excel_icon = ctk.CTkImage(
                    Image.open("assets/excel_logo.png"), size=(20, 20)
                )
        except Exception as e:
            logging.warning(f"Ícone Excel não encontrado: {e}")

        # Botões
        self.btn_update = ctk.CTkButton(
            self.footer,
            text="ATUALIZAR DADOS",
            font=("Inter", 12, "bold"),
            fg_color=DarkTheme.ACCENT_BLUE,
            hover_color="#2a6da6",
            height=40,
            width=160,
            corner_radius=8,
            command=self.acao_atualizar_dados,
        )
        self.btn_update.pack(side="right", padx=(15, 0))

        self.btn_export = ctk.CTkButton(
            self.footer,
            text=" EXCEL" if self.excel_icon else "BAIXAR RELATÓRIO",
            image=self.excel_icon,
            font=("Inter", 12, "bold"),
            fg_color=DarkTheme.SUCCESS,  # Verde Excel
            hover_color="#1e7e34",  # Verde Escuro Excel
            text_color="white",
            height=40,
            width=140 if self.excel_icon else 160,
            corner_radius=8,
            state="disabled",
            compound="left",  # Ícone à esquerda
            command=self.acao_exportar_excel,
        )
        self.btn_export.pack(side="right")

    # --- LÓGICA DE NEGÓCIO ---

    def acao_atualizar_dados(self):
        self.btn_update.configure(state="disabled", text="CARREGANDO...")
        self.lbl_status.configure(
            text="Consultando ERP e validando matrículas...",
            text_color=DarkTheme.ACCENT_BLUE,
        )
        threading.Thread(target=self._worker_atualizar).start()

    def _worker_atualizar(self):
        try:
            # O Engine agora faz todo o trabalho pesado de cruzamento SQL
            df = self.loader.get_pendentes()

            if df is None or df.empty:
                self.after(
                    0,
                    lambda: self._finalizar_atualizacao(
                        sucesso=False, msg="Nenhuma pendência encontrada."
                    ),
                )
                return

            self.df_atual = df

            # Cálculos de KPI em Memória (Pandas)
            kpis = {
                "total": len(df),
                "critico": len(df[df["SLA_Status"] == "Crítico"]),
                "novos": len(df[df["SLA_Status"] == "Novo"]),
                # Top Filial
                "top_filial": df["Filial_Tratada"].mode()[0] if not df.empty else "N/A",
                "top_filial_qtd": (
                    df["Filial_Tratada"].value_counts().iloc[0] if not df.empty else 0
                ),
                # Top Curso
                "top_curso": df["Curso"].mode()[0] if not df.empty else "N/A",
                # Rematrícula (Assumindo string 'REMAT' na coluna Tipo Matrícula se existir, ou lógica de status)
                "remat": len(
                    df[df["Status_CRM"].str.contains("REMATRÍCULA", na=False)]
                ),
            }

            self.after(0, lambda: self._finalizar_atualizacao(sucesso=True, kpis=kpis))

        except Exception as e:
            logging.error(f"Erro UI: {e}")
            self.after(
                0, lambda: self._finalizar_atualizacao(sucesso=False, msg=str(e))
            )

    def _finalizar_atualizacao(self, sucesso, kpis=None, msg=""):
        self.btn_update.configure(state="normal", text="ATUALIZAR DADOS")

        if sucesso and kpis:
            self.card_total.update_data(kpis["total"], "Alunos irregulares")
            self.card_critico.update_data(kpis["critico"], "Casos urgentes")
            self.card_novos.update_data(kpis["novos"], "Novas entradas")
            self.card_filial_top.update_data(
                kpis["top_filial"][:15] + "...", f"{kpis['top_filial_qtd']} casos"
            )
            self.card_curso_top.update_data(
                kpis["top_curso"][:20] + "...", "Maior incidência"
            )
            self.card_remat.update_data(kpis["remat"], "Veteranos")

            self.lbl_status.configure(
                text=f"Última atualização: {pd.Timestamp.now().strftime('%H:%M:%S')}",
                text_color=DarkTheme.SUCCESS,
            )
            self.btn_export.configure(state="normal")
            self.dados_carregados = True
        else:
            self.lbl_status.configure(text=f"Erro: {msg}", text_color=DarkTheme.DANGER)

    def acao_exportar_excel(self):
        if not self.dados_carregados:
            return
        self.btn_export.configure(state="disabled")
        self.lbl_status.configure(
            text="Gerando arquivo Excel detalhado...", text_color=DarkTheme.ACCENT_BLUE
        )
        threading.Thread(target=self._worker_exportar).start()

    def _worker_exportar(self):
        try:
            # Chamada mantida, assumindo que o Reporter suporta o DF
            self.reporter.gerar_por_marca(
                df_atual=self.df_atual,
                pasta_destino=self.pasta_historico,
                business_obj=None,  # Removido processador de regras pois a lógica está no SQL agora
            )
            self.after(
                0,
                lambda: self.lbl_status.configure(
                    text="Exportação concluída com sucesso!",
                    text_color=DarkTheme.SUCCESS,
                ),
            )
        except Exception as e:
            self.after(
                0,
                lambda: self.lbl_status.configure(
                    text=f"Erro na exportação: {str(e)}", text_color=DarkTheme.DANGER
                ),
            )
        finally:
            self.after(0, lambda: self.btn_export.configure(state="normal"))

    # === SIDEBAR ORIGINAL (Código preservado para manter funcionalidade) ===
    def setup_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self, fg_color=DarkTheme.BG_SIDEBAR, corner_radius=0, width=280
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # 1. Botão Voltar (Seta)
        back_icon = None
        try:
            icon_p = "assets/left_arrow_icon.png"
            if os.path.exists(icon_p):
                back_icon = ctk.CTkImage(Image.open(icon_p), size=(24, 24))
        except:
            pass

        cmd_back = lambda: self.controller.show_frame("MainMenu")

        if back_icon:
            ctk.CTkButton(
                self.sidebar,
                text="",
                image=back_icon,
                width=40,
                height=40,
                corner_radius=20,
                fg_color="transparent",
                hover_color="#333333",
                command=cmd_back,
            ).pack(anchor="w", pady=(20, 10), padx=15)
        else:
            ctk.CTkButton(
                self.sidebar,
                text="← Voltar",
                width=100,
                fg_color="transparent",
                border_width=1,
                border_color=DarkTheme.BORDER,
                text_color="gray",
                command=cmd_back,
            ).pack(anchor="w", pady=(20, 10), padx=20)

        # 2. Logo
        self.logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.logo_frame.pack(pady=(10, 20), padx=20, fill="x")
        ctk.CTkLabel(
            self.logo_frame,
            text="RAIZ EDUCAÇÃO",
            font=("Roboto", 20, "bold"),
            text_color=DarkTheme.WARNING,
        ).pack(anchor="w")

        ctk.CTkFrame(self.sidebar, height=1, fg_color=DarkTheme.BORDER).pack(
            fill="x", padx=20, pady=10
        )

        # Texto Informativo
        ctk.CTkLabel(
            self.sidebar,
            text="INFORMAÇÕES",
            font=("Roboto", 14, "bold"),
            text_color=DarkTheme.WARNING,
        ).pack(anchor="w", padx=20, pady=10)
        info_text = "Esta tela exibe inconsistências entre o CRM e a Matriz Curricular.\n\nRegra:\nStatus ≠ Matriculado E não possui Validação 'S' na grade."
        ctk.CTkLabel(
            self.sidebar,
            text=info_text,
            font=("Roboto", 12),
            text_color="gray",
            justify="left",
            wraplength=240,
        ).pack(anchor="w", padx=20)
