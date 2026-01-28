import json
import os

class NormalizationManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NormalizationManager, cls).__new__(cls)
            cls._instance.load_data()
        return cls._instance

    def load_data(self):
        try:
            # Ajuste o caminho conforme sua estrutura de pastas
            with open('normalization.json', 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        except Exception as e:
            print(f"Erro ao carregar normalization.json: {e}")
            self.data = {}

    def get_active_brands(self):
        """Retorna lista de marcas ativas, excluindo 'OUTROS' e ordenando."""
        brands = [k for k in self.data.keys() if k != "OUTROS"]
        return sorted(brands)

    def get_units_for_brand(self, brand_name):
        """Retorna lista de nomes oficiais das unidades para uma marca."""
        if brand_name == "Todas":
            all_units = []
            for brand, info in self.data.items():
                if brand != "OUTROS":
                    all_units.extend([u['nome_oficial'] for u in info.get('unidades', [])])
            return sorted(all_units)
        
        if brand_name in self.data:
            units = [u['nome_oficial'] for u in self.data[brand_name].get('unidades', [])]
            return sorted(units)
        return []

    def get_brand_from_unit(self, unit_name):
        """Descobre a marca baseada no nome da unidade (Reverse Lookup)."""
        for brand, info in self.data.items():
            for unit in info.get('unidades', []):
                # Verifica nome oficial ou aliases
                if unit['nome_oficial'] == unit_name or unit_name in unit.get('aliases', []):
                    return brand
        return "OUTROS"
