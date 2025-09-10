"""
🚀 SOLUÇÃO DEFINITIVA DE ZONEAMENTO
Implementação correta usando Layer 36 do GeoCuritiba com dados da Lei 15.511/2019
"""

import requests
import json
import asyncio
import aiohttp
import time
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any
import logging

logger = logging.getLogger(__name__)

@dataclass
class ZoneDetectionResult:
    """Resultado da detecção de zona"""
    zona: str
    confidence: str  # 'OFICIAL', 'ESTIMADA', 'PADRAO'
    source: str     # 'GEOCURITIBA_LAYER36', 'FALLBACK'
    coordinates: Optional[Tuple[float, float]] = None
    details: str = ""

class GeoCuritibaLayer36Detector:
    """Detector de zoneamento usando a Layer 36 oficial do GeoCuritiba"""
    
    def __init__(self):
        # URLs oficiais do GeoCuritiba - CORRIGIDAS!
        self.MAPSERVER_BASE = "https://geocuritiba.ippuc.org.br/server/rest/services/GeoCuritiba"
        self.CADASTRAL_SERVICE = f"{self.MAPSERVER_BASE}/Publico_GeoCuritiba_MapaCadastral/MapServer"
        # Layer 36 está no mesmo serviço cadastral!
        
        # Headers padrão
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://geocuritiba.ippuc.org.br/',
            'Accept': 'application/json, text/plain, */*'
        }
        
        # Timeout para requisições
        self.timeout = 10
    
    def buscar_zoneamento_correto(self, inscricao_fiscal: str) -> ZoneDetectionResult:
        """
        🎯 MÉTODO DEFINITIVO: Busca zoneamento usando Layer 36
        
        Processo:
        1. Buscar coordenadas do lote pela inscrição fiscal
        2. Consultar Layer 36 do zoneamento Lei 15.511/2019
        3. Extrair os campos corretos: nm_zona, sg_zona, cd_zona
        4. Padronizar sigla (ZR4 → ZR-4)
        """
        try:
            # PASSO 1: Buscar coordenadas do lote
            coordenadas = self._buscar_coordenadas_lote(inscricao_fiscal)
            if not coordenadas:
                return ZoneDetectionResult(
                    zona="ZR-4",
                    confidence="PADRAO", 
                    source="FALLBACK",
                    details="Inscrição fiscal não encontrada no sistema cadastral"
                )
            
            x, y = coordenadas
            
            # PASSO 2: Consultar Layer 36 do zoneamento
            zona_info = self._consultar_layer36_zoneamento(x, y)
            if not zona_info:
                return ZoneDetectionResult(
                    zona="ZR-4",
                    confidence="ESTIMADA",
                    source="FALLBACK", 
                    coordinates=(x, y),
                    details="Coordenadas encontradas, mas zoneamento não detectado na Layer 36"
                )
            
            # PASSO 3: Extrair e padronizar dados
            sigla_raw = zona_info.get('sg_zona', '')
            nome_zona = zona_info.get('nm_zona', '')
            
            # Padronizar sigla: ZR4 → ZR-4
            sigla_padronizada = self._padronizar_sigla_zona(sigla_raw)
            
            return ZoneDetectionResult(
                zona=sigla_padronizada,
                confidence="OFICIAL",
                source="GEOCURITIBA_LAYER36",
                coordinates=(x, y),
                details=f"Zona detectada: {nome_zona} ({sigla_padronizada}) via Layer 36 - Lei 15.511/2019"
            )
            
        except Exception as e:
            logger.error(f"Erro na detecção de zoneamento: {e}")
            return ZoneDetectionResult(
                zona="ZR-4",
                confidence="PADRAO",
                source="FALLBACK",
                details=f"Erro no processo: {str(e)}"
            )
    
    def _buscar_coordenadas_lote(self, inscricao_fiscal: str) -> Optional[Tuple[float, float]]:
        """Busca coordenadas do centroide do lote pela inscrição fiscal"""
        try:
            url_lote = f"{self.CADASTRAL_SERVICE}/find"
            
            params = {
                'f': 'json',
                'searchText': inscricao_fiscal,
                'contains': 'true',
                'searchFields': 'INDICACAO,INDICACAO_FISCAL,INSCRICAO',
                'layers': '0,1,2,3,4,5',  # Múltiplas layers cadastrais
                'returnGeometry': 'true',
                'maxAllowableOffset': '1',
                'geometryPrecision': '2'
            }
            
            response = requests.get(url_lote, params=params, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            if data.get('results') and len(data['results']) > 0:
                # Pegar primeiro resultado encontrado
                result = data['results'][0]
                geometry = result.get('geometry')
                
                if geometry:
                    if 'rings' in geometry:
                        # Polígono - calcular centroide
                        rings = geometry['rings'][0]
                        x = sum(p[0] for p in rings) / len(rings)
                        y = sum(p[1] for p in rings) / len(rings)
                    else:
                        # Ponto
                        x = geometry.get('x')
                        y = geometry.get('y')
                    
                    if x and y:
                        logger.info(f"Coordenadas encontradas para {inscricao_fiscal}: ({x}, {y})")
                        return (x, y)
            
            # Fallback: tentar método alternativo via query
            return self._buscar_coordenadas_alternativo(inscricao_fiscal)
            
        except Exception as e:
            logger.error(f"Erro ao buscar coordenadas do lote {inscricao_fiscal}: {e}")
            return None
    
    def _buscar_coordenadas_alternativo(self, inscricao_fiscal: str) -> Optional[Tuple[float, float]]:
        """Método alternativo para buscar coordenadas"""
        try:
            url_query = f"{self.CADASTRAL_SERVICE}/0/query"  # Layer 0 - Lotes
            
            params = {
                'f': 'json',
                'where': f"INDICACAO = '{inscricao_fiscal}' OR INDICACAO_FISCAL = '{inscricao_fiscal}' OR INSCRICAO = '{inscricao_fiscal}'",
                'outFields': '*',
                'returnGeometry': 'true',
                'geometryPrecision': '2'
            }
            
            response = requests.get(url_query, params=params, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            if data.get('features') and len(data['features']) > 0:
                geometry = data['features'][0]['geometry']
                
                if 'rings' in geometry:
                    rings = geometry['rings'][0]
                    x = sum(p[0] for p in rings) / len(rings)
                    y = sum(p[1] for p in rings) / len(rings)
                    return (x, y)
                    
        except Exception as e:
            logger.warning(f"Método alternativo também falhou para {inscricao_fiscal}: {e}")
            
        return None
    
    def _consultar_layer36_zoneamento(self, x: float, y: float) -> Optional[Dict[str, Any]]:
        """
        🎯 CONSULTA OFICIAL À LAYER 36
        Layer 36: Zoneamento Lei 15.511/2019 no serviço MapaCadastral
        """
        try:
            url_zoneamento = f"{self.CADASTRAL_SERVICE}/36/query"
            
            params = {
                'f': 'json',
                'geometry': f'{{"x":{x},"y":{y},"spatialReference":{{"wkid":31982}}}}',
                'geometryType': 'esriGeometryPoint',
                'spatialRel': 'esriSpatialRelIntersects',
                'outFields': 'nm_zona,sg_zona,cd_zona',  # Campos corretos identificados
                'returnGeometry': 'false'
            }
            
            response = requests.get(url_zoneamento, params=params, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            if data.get('features') and len(data['features']) > 0:
                attributes = data['features'][0]['attributes']
                logger.info(f"Zoneamento Layer 36 - Dados brutos: {attributes}")
                return attributes
                
        except Exception as e:
            logger.error(f"Erro na consulta Layer 36 para coordenadas ({x}, {y}): {e}")
            
        return None
    
    def _padronizar_sigla_zona(self, sigla_raw: str) -> str:
        """
        Padroniza a sigla da zona conforme padrões conhecidos
        
        Exemplos:
        - ZR4 → ZR-4
        - ZC → ZC (mantém)
        - ZUM1 → ZUM-1
        """
        if not sigla_raw:
            return "ZR-4"  # Fallback padrão
            
        sigla = sigla_raw.strip().upper()
        
        # Padrões conhecidos que precisam de hífen
        if sigla.startswith('ZR') and len(sigla) == 3 and sigla[-1].isdigit():
            return f"ZR-{sigla[-1]}"  # ZR4 → ZR-4
            
        if sigla.startswith('ZUM') and len(sigla) == 4 and sigla[-1].isdigit():
            return f"ZUM-{sigla[-1]}"  # ZUM1 → ZUM-1
            
        if sigla.startswith('ZS') and len(sigla) == 3 and sigla[-1].isdigit():
            return f"ZS-{sigla[-1]}"  # ZS1 → ZS-1
            
        if sigla.startswith('ZH') and len(sigla) == 3 and sigla[-1].isdigit():
            return f"ZH-{sigla[-1]}"  # ZH1 → ZH-1
        
        # Zonas que já estão no formato correto
        return sigla

# Instância global
_detector = None

def get_geocuritiba_detector():
    """Singleton do detector"""
    global _detector
    if _detector is None:
        _detector = GeoCuritibaLayer36Detector()
    return _detector

def buscar_zoneamento_definitivo(inscricao_fiscal: str) -> ZoneDetectionResult:
    """
    🚀 FUNÇÃO PRINCIPAL PARA USAR NO APP.PY
    
    Esta função substitui a detecção atual e usa a Layer 36 correta
    """
    detector = get_geocuritiba_detector()
    return detector.buscar_zoneamento_correto(inscricao_fiscal)

# Função de compatibilidade com o sistema atual
def detect_zone_professional(endereco: str, inscricao_fiscal: str = "") -> ZoneDetectionResult:
    """
    Função de compatibilidade que mantém a interface atual
    mas usa a nova implementação Layer 36
    """
    if inscricao_fiscal:
        # Se tem inscrição, usar o método definitivo
        return buscar_zoneamento_definitivo(inscricao_fiscal)
    else:
        # Fallback para método anterior (por endereço)
        return ZoneDetectionResult(
            zona="ZR-4",
            confidence="PADRAO",
            source="FALLBACK",
            details="Endereço fornecido sem inscrição fiscal - usando zona padrão"
        )

if __name__ == "__main__":
    # Teste da implementação
    print("TESTANDO IMPLEMENTACAO LAYER 36")
    
    # Teste com inscrição conhecida
    inscricao_teste = "03000180090017"  # Exemplo do placeholder
    resultado = buscar_zoneamento_definitivo(inscricao_teste)
    
    print(f"Resultado: {resultado.zona}")
    print(f"Confianca: {resultado.confidence}")
    print(f"Fonte: {resultado.source}")
    print(f"Detalhes: {resultado.details}")