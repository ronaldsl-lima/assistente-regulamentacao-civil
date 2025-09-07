import pandas as pd
import sqlite3
import json
import os
from pathlib import Path

class ZoneamentoIntegrator:
    """Integrador de dados de zoneamento de Curitiba ao sistema"""
    
    def __init__(self, excel_path=None, db_path="zoneamento_curitiba.db"):
        self.excel_path = excel_path or r"C:\Users\User\Downloads\zoneamento_curitiba.xlsx"
        self.db_path = db_path
        self.zones_data = {}
        
    def load_excel_data(self):
        """Carrega dados do Excel de zoneamento"""
        try:
            df = pd.read_excel(self.excel_path)
            print(f"Carregados {len(df)} registros de zoneamento")
            return df
        except Exception as e:
            print(f"Erro ao carregar Excel: {e}")
            return None
    
    def clean_and_structure_data(self, df):
        """Limpa e estrutura os dados para uso no sistema"""
        zones_dict = {}
        
        for _, row in df.iterrows():
            zona = str(row['Zona/Subzona']).strip()
            
            # Estrutura os dados da zona
            zone_data = {
                'nome': zona,
                'coeficiente_aproveitamento': self._clean_value(row.get('CA (Coef. Aproveit.)')),
                'altura_pavimentos': self._clean_value(row.get('Altura/Pav.')),
                'taxa_ocupacao': self._clean_value(row.get('Taxa Ocupação (TO)')),
                'taxa_permeavel': self._clean_value(row.get('Taxa Permeável (TP)')),
                'recuo_frontal': self._clean_value(row.get('Recuo Frontal')),
                'afastamento_divisas': self._clean_value(row.get('Afastamento Divisas')),
                'lote_padrao': self._clean_value(row.get('Lote Padrão')),
                'porte_m2': self._clean_value(row.get('Porte (m²)')),
                'usos_permitidos': self._clean_value(row.get('Usos Permitidos / Observações')),
                'notas_tecnicas': self._clean_value(row.get('Notas Técnicas Gerais'))
            }
            
            zones_dict[zona] = zone_data
            
        self.zones_data = zones_dict
        print(f"Processadas {len(zones_dict)} zonas")
        return zones_dict
    
    def _clean_value(self, value):
        """Limpa valores das células"""
        if pd.isna(value):
            return None
        return str(value).strip()
    
    def create_database(self):
        """Cria banco de dados SQLite com os dados de zoneamento"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Criar tabela
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS zoneamento (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                zona TEXT UNIQUE NOT NULL,
                coeficiente_aproveitamento TEXT,
                altura_pavimentos TEXT,
                taxa_ocupacao TEXT,
                taxa_permeavel TEXT,
                recuo_frontal TEXT,
                afastamento_divisas TEXT,
                lote_padrao TEXT,
                porte_m2 TEXT,
                usos_permitidos TEXT,
                notas_tecnicas TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Inserir dados
        for zona, data in self.zones_data.items():
            cursor.execute('''
                INSERT OR REPLACE INTO zoneamento 
                (zona, coeficiente_aproveitamento, altura_pavimentos, taxa_ocupacao, 
                 taxa_permeavel, recuo_frontal, afastamento_divisas, lote_padrao, 
                 porte_m2, usos_permitidos, notas_tecnicas)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                zona,
                data.get('coeficiente_aproveitamento'),
                data.get('altura_pavimentos'),
                data.get('taxa_ocupacao'),
                data.get('taxa_permeavel'),
                data.get('recuo_frontal'),
                data.get('afastamento_divisas'),
                data.get('lote_padrao'),
                data.get('porte_m2'),
                data.get('usos_permitidos'),
                data.get('notas_tecnicas')
            ))
        
        conn.commit()
        conn.close()
        print(f"Banco criado: {self.db_path}")
    
    def get_zone_parameters(self, zona):
        """Retorna parâmetros de uma zona específica"""
        return self.zones_data.get(zona, {})
    
    def export_to_json(self, output_path="zoneamento_curitiba.json"):
        """Exporta dados para JSON"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.zones_data, f, ensure_ascii=False, indent=2)
        print(f"Dados exportados para: {output_path}")
    
    def run_integration(self):
        """Executa todo o processo de integração"""
        print("Iniciando integracao de dados de zoneamento...")
        
        # 1. Carregar dados do Excel
        df = self.load_excel_data()
        if df is None:
            return False
        
        # 2. Processar dados
        self.clean_and_structure_data(df)
        
        # 3. Criar banco de dados
        self.create_database()
        
        # 4. Exportar JSON
        self.export_to_json()
        
        print("Integracao concluida!")
        return True

def enhanced_zone_lookup(zona_detectada):
    """Função melhorada para buscar parâmetros de zona"""
    integrator = ZoneamentoIntegrator()
    
    # Carregar dados se não estiver carregado
    if not integrator.zones_data:
        df = integrator.load_excel_data()
        if df is not None:
            integrator.clean_and_structure_data(df)
    
    # Buscar parâmetros da zona
    params = integrator.get_zone_parameters(zona_detectada)
    
    if params:
        return {
            'zona_encontrada': True,
            'zona': zona_detectada,
            'parametros': params
        }
    else:
        return {
            'zona_encontrada': False,
            'zona': zona_detectada,
            'mensagem': 'Zona não encontrada na base de dados'
        }

if __name__ == "__main__":
    integrator = ZoneamentoIntegrator()
    success = integrator.run_integration()
    
    if success:
        # Teste com algumas zonas
        test_zones = ['ZR-1', 'ZR-2', 'ZR-3']
        print("\nTestando lookup de zonas:")
        for zona in test_zones:
            result = enhanced_zone_lookup(zona)
            print(f"\n{zona}:")
            if result['zona_encontrada']:
                params = result['parametros']
                print(f"  CA: {params.get('coeficiente_aproveitamento', 'N/A')}")
                print(f"  TO: {params.get('taxa_ocupacao', 'N/A')}")
                print(f"  Altura: {params.get('altura_pavimentos', 'N/A')}")
            else:
                print(f"  {result['mensagem']}")