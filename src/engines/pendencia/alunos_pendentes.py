import os
import logging
from src.utils.config_manager import load_business_config
from src.engines.pendencia.engine import PendenciaEngine 
from src.engines.pendencia.regras import ProcessadorRegras 
from src.engines.pendencia.report import PendenciaReporter

class EnginePendencia:
    def __init__(self, arquivo_path=None):
        # Carrega configuração (cores, caminhos)
        self.config = load_business_config()
        
        # Definição de caminhos de saída (onde os Excels serão salvos)
        caminho_relativo = self.config.get('caminhos', {}).get('historico_pendencia')
        if not caminho_relativo:
             caminho_relativo = "historico_dados_local/Pendentes"

        if os.path.isabs(caminho_relativo):
            self.pasta_historico = caminho_relativo
        else:
            self.pasta_historico = os.path.join(os.getcwd(), caminho_relativo)
            
        os.makedirs(self.pasta_historico, exist_ok=True)
        
        # Inicialização dos Módulos da Nova Arquitetura
        # 3. Instanciando a classe correta do Engine
        self.loader = PendenciaEngine()    
        
        # 4. Instanciando a classe correta de Regras (ProcessadorRegras)
        # Passamos self.config pois o __init__ do ProcessadorRegras aceita config
        self.regras = ProcessadorRegras(self.config)     
        
        self.reporter = PendenciaReporter(self.config, self.pasta_historico) 
        
        self.df_final = None

    def executar(self):
        """
        Método único que roda todo o processo: Extração -> Transformação -> Carga (Relatório)
        """
        logging.info("Orchestrator: Iniciando carga SQL (PendenciaEngine)...")
        
        # 1. Extração SQL
        df_bruto = self.loader.get_pendentes()
        set_matriculados = self.loader.get_matriculados_ra()
        
        if df_bruto is None:
            logging.error("Orchestrator: Falha crítica na carga de dados SQL.")
            return False

        logging.info("Orchestrator: Dados carregados. Iniciando regras de negócio e cruzamento...")
        
        # 2. Aplicação de Regras
        # 5. Correção: O método no regras.py é 'aplicar_regras', não 'preparar_dados'
        self.df_final = self.regras.aplicar_regras(df_bruto, set_matriculados)
        
        qtd_pendentes = len(self.df_final) if self.df_final is not None else 0
        logging.info(f"Orchestrator: Processamento concluído. Total de pendências reais: {qtd_pendentes}")

        # 3. Geração de Relatórios
        if self.df_final is not None and not self.df_final.empty:
            logging.info("Orchestrator: Gerando relatórios Excel por marca...")
            
            # Aqui passamos o objeto 'self.regras' inteiro, pois ele contém 
            # o atributo 'ras_matriculados_atuais' necessário para o report calcular conversão
            self.reporter.gerar_por_marca(
                df_atual=self.df_final, 
                pasta_destino=self.pasta_historico, 
                business_obj=self.regras 
            )
            return True
        else:
            logging.warning("Orchestrator: Nenhum dado pendente para gerar relatório.")
            return True

# Bloco de execução direta (caso rode python alunos_pendentes.py)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    engine = EnginePendencia()
    engine.executar()
