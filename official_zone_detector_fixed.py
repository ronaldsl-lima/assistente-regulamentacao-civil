#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Detector Oficial de Zoneamento - Versão Corrigida
Baseado no shapefile oficial ZONEAMENTO_OFICIAL.shp
"""

import geopandas as gpd
from shapely.geometry import Point
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Tuple
import pandas as pd

logger = logging.getLogger(__name__)

@dataclass
class OfficialZoneResult:
    """Resultado da detecção oficial"""
    zona: str
    confidence: str = "OFICIAL_SHAPEFILE_NOVO"
    source: str = "ZONEAMENTO_OFICIAL.shp" 
    coordinates: Optional[Tuple[float, float]] = None
    details: str = ""
    raw_data: dict = None
    nm_zona: str = ""
    legislacao: str = ""

class OfficialZoneDetector:
    """
    Detector oficial usando o novo shapefile com sistema de coordenadas correto
    """
    
    def __init__(self):
        self.shapefile_path = Path("mapas/ZONEAMENTO_OFICIAL.shp")
        self.gdf = None
        self._load_shapefile()
    
    def _load_shapefile(self):
        """Carrega o shapefile oficial e converte para WGS84"""
        try:
            if self.shapefile_path.exists():
                # Carregar shapefile original
                self.gdf = gpd.read_file(self.shapefile_path)
                
                # Converter para WGS84 (lat/lon) se necessário
                if self.gdf.crs != 'EPSG:4326':
                    print(f"Convertendo coordenadas de {self.gdf.crs} para EPSG:4326")
                    self.gdf = self.gdf.to_crs('EPSG:4326')
                
                logger.info(f"Shapefile oficial carregado: {len(self.gdf)} zonas")
                
                # Debug: mostrar colunas disponíveis
                print(f"DEBUG: Colunas do shapefile: {list(self.gdf.columns)}")
                print(f"DEBUG: Exemplos de zonas:")
                if 'SG_ZONA' in self.gdf.columns:
                    print(f"- SG_ZONA (siglas): {self.gdf['SG_ZONA'].value_counts().head()}")
                if 'NM_ZONA' in self.gdf.columns:
                    print(f"- NM_ZONA (nomes): {self.gdf['NM_ZONA'].value_counts().head()}")
                
            else:
                logger.warning("Shapefile oficial não encontrado")
        except Exception as e:
            logger.error(f"Erro ao carregar shapefile oficial: {e}")
            print(f"ERRO ao carregar shapefile: {e}")
    
    def detect_zone_by_coordinates(self, lat: float, lon: float) -> Optional[OfficialZoneResult]:
        """
        Detecta zona por coordenadas usando dados oficiais
        """
        
        if self.gdf is None:
            return None
        
        try:
            point = Point(lon, lat)  # Note: lon, lat para Point
            
            # Encontrar zona que contém o ponto
            matches = self.gdf[self.gdf.geometry.contains(point)]
            
            if len(matches) > 0:
                match = matches.iloc[0]
                
                # Extrair informações da zona
                zona_sigla = str(match.get('SG_ZONA', 'INDETERMINADO'))
                zona_nome = str(match.get('NM_ZONA', ''))
                legislacao = str(match.get('LEGISLACAO', ''))
                
                # Limpar e padronizar zona
                if zona_sigla and zona_sigla.upper() not in ['NULL', 'NONE', 'NAN']:
                    zona = zona_sigla.upper().strip()
                else:
                    zona = "INDETERMINADO"
                
                # Dados brutos para debug
                raw_data = {
                    'SG_ZONA': zona_sigla,
                    'NM_ZONA': zona_nome,
                    'LEGISLACAO': legislacao,
                    'NM_GRUPO': match.get('NM_GRUPO', ''),
                    'TEMA': match.get('TEMA', '')
                }
                
                return OfficialZoneResult(
                    zona=zona,
                    coordinates=(lat, lon),
                    details=f"Detecção oficial: {zona_nome} ({zona_sigla})",
                    raw_data=raw_data,
                    nm_zona=zona_nome,
                    legislacao=legislacao
                )
        
        except Exception as e:
            logger.error(f"Erro na detecção por coordenadas: {e}")
            print(f"DEBUG: Erro na detecção: {e}")
        
        return None
    
    def get_all_zones(self) -> dict:
        """
        Retorna todas as zonas disponíveis
        """
        
        if self.gdf is None:
            return {}
        
        zones = {}
        try:
            if 'SG_ZONA' in self.gdf.columns:
                for idx, row in self.gdf.iterrows():
                    sigla = str(row.get('SG_ZONA', ''))
                    nome = str(row.get('NM_ZONA', ''))
                    if sigla and sigla.upper() not in ['NULL', 'NONE', 'NAN']:
                        zones[sigla.upper()] = {
                            'nome': nome,
                            'legislacao': str(row.get('LEGISLACAO', '')),
                            'grupo': str(row.get('NM_GRUPO', ''))
                        }
        except Exception as e:
            logger.error(f"Erro ao obter zonas: {e}")
        
        return zones

# Instância global
official_detector = None

def get_official_detector():
    """
    Obtém instância do detector oficial (singleton)
    """
    global official_detector
    if official_detector is None:
        official_detector = OfficialZoneDetector()
    return official_detector

def detect_zone_official(lat: float, lon: float) -> Optional[OfficialZoneResult]:
    """
    Função principal de detecção oficial
    """
    detector = get_official_detector()
    return detector.detect_zone_by_coordinates(lat, lon)

def get_official_zones() -> dict:
    """
    Obtém lista de todas as zonas oficiais
    """
    detector = get_official_detector()
    return detector.get_all_zones()

def test_official_detector():
    """
    Teste do detector oficial
    """
    
    print("TESTE DO DETECTOR OFICIAL")
    print("=" * 40)
    
    detector = get_official_detector()
    
    if detector.gdf is None:
        print("ERRO: Shapefile não carregado")
        return
    
    # Mostrar estatísticas gerais
    print(f"Total de zonas: {len(detector.gdf)}")
    print(f"Sistema de coordenadas: {detector.gdf.crs}")
    
    # Listar zonas únicas
    if 'SG_ZONA' in detector.gdf.columns:
        zonas_unicas = detector.gdf['SG_ZONA'].value_counts()
        print(f"\nZonas encontradas ({len(zonas_unicas)}):")
        for zona, count in zonas_unicas.head(10).items():
            print(f"  {zona}: {count} areas")
    
    # Testar pontos conhecidos (coordenadas aproximadas de Curitiba)
    test_points = [
        (-25.4284, -49.2733, "Centro de Curitiba"),
        (-25.4387, -49.2871, "CIC/Cidade Industrial"),
        (-25.4950, -49.3017, "Bairro Hauer"),
        (-25.5642, -49.3335, "Tatuquara")
    ]
    
    print(f"\nTeste de pontos:")
    for lat, lon, desc in test_points:
        print(f"\n{desc} ({lat}, {lon}):")
        result = detect_zone_official(lat, lon)
        
        if result:
            print(f"  OK Zona: {result.zona}")
            print(f"  OK Nome: {result.nm_zona}")
            print(f"  OK Legislacao: {result.legislacao}")
        else:
            print(f"  ERRO Nenhuma zona encontrada")
    
    print(f"\nTeste concluido!")

if __name__ == "__main__":
    test_official_detector()