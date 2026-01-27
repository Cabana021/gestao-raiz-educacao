import os
import logging
from src.utils.config_manager import load_business_config
from src.engines.pendencia.engine import PendenciaLoader
from src.engines.pendencia.regras import PendenciaBusiness
from src.engines.pendencia.report import PendenciaReporter

class EnginePendencia:
    def __init__(self, arquivo_path=None):
        self.config = load_business_config()
        
        # Definição de caminhos
        caminho_relativo = self.config.get('caminhos', {}).get('historico_pendencia')
        if not caminho_relativo:
             caminho_relativo = "historico_dados_local/Pendentes"

        if os.path.isabs(caminho_relativo):
            self.pasta_historico = caminho_relativo
        else:
            self.pasta_historico = os.path.join(os.getcwd(), caminho_relativo)
            
        os.makedirs(self.pasta_historico, exist_ok=True)
        
        # Inicialização dos módulos
        self.loader = PendenciaLoader(config_dict=self.config)
        self.regras = PendenciaBusiness()
        self.reporter = PendenciaReporter(self.config, self.pasta_historico)
        self.df_final = None

    def carregar_e_transformar(self):
        logging.info("Orchestrator: Iniciando carga SQL...")
        df_bruto = self.loader.carregar_dados()
        
        if df_bruto is None:
            logging.error("Orchestrator: Falha na carga de dados SQL.")
            return False

        logging.info("Orchestrator: Dados carregados. Iniciando regras de negócio...")
        self.df_final = self.regras.aplicar_regras(df_bruto)
        
        logging.info(f"Orchestrator: Processamento concluído. Total de pendências reais: {len(self.df_final) if self.df_final is not None else 0}")
        return True

    def gerar_output(self, pasta_destino):
        if self.df_final is not None and not self.df_final.empty:
            self.reporter.gerar_por_marca(
                df_atual=self.df_final, 
                pasta_destino=pasta_destino, 
                business_obj=self.regras
            )
        else:
            logging.warning("Orchestrator: Nenhum dado para gerar relatório.")