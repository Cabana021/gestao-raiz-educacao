import json
import os
import logging

# Caminho do config.json 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

# Chaves válidas de estado do usuário 
USER_STATE_KEYS = {
    "ultima_pasta_pendencia",
    "ultima_pasta_renovacao",
    "ultima_pasta_captacao",
}


def load_config():
    try:
        if not os.path.exists(CONFIG_PATH):
            logging.warning(f"Config não encontrado em: {CONFIG_PATH}. Retornando vazio.")
            return {}
            
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Erro ao carregar config.json: {e}")
        return {}

def load_business_config():
    return load_config()

def save_config(config):
    """Salva o config.json."""
    if config is None: config = {}

    # Blindagem: remove chave genérica proibida
    config.pop("ultima_pasta", None)

    # Blindagem: remove qualquer estado inesperado
    for key in list(config.keys()):
        if key.startswith("ultima_pasta_") and key not in USER_STATE_KEYS:
            config.pop(key)

    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Erro ao salvar config.json: {e}")

def get_ultima_pasta(tipo):
    """
    Retorna a última pasta usada para uma automação específica.
    tipo: 'pendencia' | 'renovacao' | 'captacao'
    """
    chave = f"ultima_pasta_{tipo}"
    config = load_config()
    return config.get(chave) or os.getcwd()

def set_ultima_pasta(tipo, caminho):
    """
    Atualiza a última pasta usada para uma automação específica.
    """
    chave = f"ultima_pasta_{tipo}"
    config = load_config()
    config[chave] = caminho
    save_config(config)

class ConfigManager:
    def __init__(self):
        # Carrega o JSON assim que a classe é instanciada
        self.full_config = load_config()

    def get_config(self, section=None):
        # Se não foi passada nenhuma seção, retorna o JSON inteiro
        if section is None:
            return self.full_config

        # Se foi passada uma seção, retorna apenas ela
        section_key = section.lower()
        return self.full_config.get(section_key, {})
