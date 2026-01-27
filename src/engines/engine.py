import pandas as pd
import logging
from src.utils.config_manager import ConfigManager
from src.engines.pendencia.regras import ProcessadorRegras
from src.engines.pendencia.report import GeradorRelatorio

class EngineBase:
    """
    Classe base mantida para compatibilidade com o módulo de Pendência.
    Fornece métodos básicos que o código antigo espera encontrar.
    """
    def __init__(self):
        self.df = None

    def carregar_excel(self, caminho, aba=0):
        """Método utilitário genérico de leitura."""
        try:
            return pd.read_excel(caminho, sheet_name=aba)
        except Exception as e:
            logging.error(f"Erro na EngineBase ao ler Excel: {e}")
            return None

class Engine:
    """
    Nova engine moderna.
    Responsável por:
    1. Ler o Excel Bruto.
    2. Transformar dados (Pivot Table) se necessário.
    3. Orquestrar a chamada de Regras e Relatórios.
    """

    def __init__(self, arquivo_path, aba_alvo):
        self.arquivo_path = arquivo_path
        self.aba_alvo = aba_alvo 
        
        # Carrega configurações
        self.config_manager = ConfigManager()
        
        # 1. Carrega o JSON Completo
        full_config = self.config_manager.get_config() 
        
        # 2. Seleciona a seção específica com base na aba alvo
        # Ex: Se aba_alvo for "Captacao", busca a chave "captacao" no JSON
        self.business_config = full_config.get(aba_alvo.lower(), {})
        
        # Debug/Segurança: Avisa se não achou a config
        if not self.business_config:
            import logging
            logging.warning(f"Engine: Nenhuma configuração encontrada para '{aba_alvo}' (chave: '{aba_alvo.lower()}')")
        
        # Estado dos dados
        self.df_bruto = None   
        self.df_final = None   
        
        # Inicializa os especialistas passando APENAS a config do módulo
        self.regras = ProcessadorRegras(self.business_config)
        self.reporter = GeradorRelatorio(self.business_config)

    def _carregar_e_transformar(self):
        try:
            # 1. Leitura do Excel
            nome_aba_excel = self.business_config.get("aba_excel", "Planilha1")
            logging.info(f"Lendo arquivo: {self.arquivo_path} na aba '{nome_aba_excel}'")
            df = pd.read_excel(self.arquivo_path, sheet_name=nome_aba_excel)

            # 2. Limpeza Básica
            df.columns = [str(c).strip() for c in df.columns]

            # 3. Pivot se for formato longo
            if "Atributo" in df.columns and "Valor" in df.columns:
                logging.info("Detectado formato Longo. Aplicando Pivot Table...")
                cols_index = [c for c in ["Data", "Marca", "Filial"] if c in df.columns]
                if not cols_index:
                    raise ValueError("Arquivo Longo sem colunas chaves.")
                df = df.pivot_table(index=cols_index, columns="Atributo", values="Valor", aggfunc="sum", fill_value=0).reset_index()
                df.columns.name = None

            # 4. Mapeamento
            mapa_colunas = self.business_config.get("mapeamento_colunas", {})
            if mapa_colunas:
                df = df.rename(columns=mapa_colunas)

            # 5. Validação
            col_data = next((c for c in df.columns if c.upper() == 'DATA'), None)
            if not col_data:
                raise ValueError("A coluna de 'Data' não foi encontrada.")
            
            df = df.rename(columns={col_data: 'Data'})
            df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
            df = df.dropna(subset=['Data'])

            self.df_final = df
            return True

        except Exception as e:
            logging.error(f"Erro no Engine de Leitura: {e}", exc_info=True)
            raise e

    def executar_fluxo_completo(self, datas_selecionadas, caminho_saida):
        if not self._carregar_e_transformar():
            return False
        df_report, df_dash = self.regras.aplicar_regras(self.df_final, datas_selecionadas)
        return self.reporter.gerar_output(df_report, df_dash, caminho_saida)
