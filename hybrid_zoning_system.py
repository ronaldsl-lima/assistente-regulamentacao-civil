#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Zoneamento Híbrido - Múltiplas Camadas de Validação
Baseado nas sugestões da Claude Web para maior precisão em SEHIS

Este sistema implementa:
1. Camada 1: Zoneamento Básico (ZR1, ZR2, ZR3, etc.)
2. Camada 2: Setores Especiais (SEHIS, SEPE, SEP, etc.)
3. Camada 3: Zonas Específicas (Central, Industrial, etc.)
4. Sistema de confiabilidade e validação cruzada
5. Preparado para integração com API IPPUC futura
"""

import logging
from typing import Dict, List, Tuple, Optional, NamedTuple
from dataclasses import dataclass
from enum import Enum
import json
from datetime import datetime
import requests
import time

logger = logging.getLogger(__name__)

class ZoneConfidence(Enum):
    """Níveis de confiabilidade do zoneamento"""
    OFICIAL_API = "OFICIAL_API"          # Via API oficial IPPUC
    OFICIAL_SHAPEFILE = "OFICIAL_SHAPEFILE"  # Via shapefile oficial
    VALIDADO_CRUZADO = "VALIDADO_CRUZADO"    # Múltiplas fontes concordam
    ESTIMADO_CONFIAVEL = "ESTIMADO_CONFIAVEL"  # Análise inteligente com alta confiança
    ESTIMADO_BAIXA = "ESTIMADO_BAIXA"        # Análise com baixa confiança
    NECESSITA_VALIDACAO = "NECESSITA_VALIDACAO"  # Conflito entre fontes
    DESCONHECIDO = "DESCONHECIDO"            # Não conseguiu determinar

@dataclass
class LayeredZoneResult:
    """Resultado com múltiplas camadas de informação"""
    zona_final: str
    confidence: ZoneConfidence
    camadas: Dict[str, str]  # Resultado de cada camada
    conflicts: List[str]     # Conflitos detectados
    validations: Dict[str, bool]  # Validações aplicadas
    recommendation: str      # Recomendação para o usuário
    requires_manual_check: bool  # Se precisa validação manual
    details: Dict[str, any]  # Detalhes técnicos

class HybridZoningSystem:
    """
    Sistema híbrido de zoneamento com múltiplas camadas
    Preparado para integração com API oficial do IPPUC
    """
    
    def __init__(self):
        # Configuração do sistema
        self.ippuc_api_available = False  # Será True quando API estiver disponível
        self.ippuc_api_key = None
        self.ippuc_base_url = "https://geocuritiba.ippuc.org.br/api/v1"  # Exemplo
        
        # Base de conhecimento expandida de SEHIS
        self.sehis_database = self._load_sehis_database()
        
        # Sistema de coordenadas conhecidas (expandir conforme dados oficiais)
        self.verified_coordinates = self._load_verified_coordinates()
        
        # Mapeamento de conflitos conhecidos
        self.known_conflicts = self._load_known_conflicts()
    
    def detect_zone_hybrid(self, endereco: str, inscricao: str = "", 
                          coordinates: Tuple[float, float] = None) -> LayeredZoneResult:
        """
        Detecção híbrida com múltiplas camadas de validação
        """
        
        camadas = {}
        conflicts = []
        validations = {}
        
        # CAMADA 1: API OFICIAL IPPUC (quando disponível)
        if self.ippuc_api_available:
            try:
                api_result = self._query_ippuc_api(endereco, coordinates)
                camadas["ippuc_oficial"] = api_result
                validations["ippuc_api"] = True
            except Exception as e:
                logger.warning(f"Falha na API IPPUC: {e}")
                validations["ippuc_api"] = False
        
        # CAMADA 2: SHAPEFILE OFICIAL (sistema atual melhorado)
        try:
            from detect_zone_enhanced import detect_zone_professional
            shapefile_result = detect_zone_professional(endereco, inscricao)
            camadas["shapefile"] = shapefile_result.zona
            validations["shapefile"] = True
        except Exception as e:
            logger.warning(f"Falha no shapefile: {e}")
            validations["shapefile"] = False
        
        # CAMADA 3: BASE SEHIS ESPECIALIZADA
        sehis_result = self._check_sehis_specialized(endereco, inscricao, coordinates)
        if sehis_result:
            camadas["sehis_especializada"] = sehis_result["zona"]
            validations["sehis_check"] = True
        else:
            validations["sehis_check"] = False
        
        # CAMADA 4: VALIDAÇÃO CRUZADA DE COORDENADAS
        if coordinates:
            coord_result = self._validate_by_coordinates(coordinates)
            if coord_result:
                camadas["coordenadas"] = coord_result
                validations["coordinates"] = True
        
        # ANÁLISE DE CONFLITOS
        zones_found = list(set([z for z in camadas.values() if z]))
        
        if len(zones_found) == 1:
            # Consenso - todas as camadas concordam
            zona_final = zones_found[0]
            confidence = self._determine_confidence(camadas, validations)
            recommendation = "Zoneamento confirmado por múltiplas fontes"
            requires_manual = False
            
        elif len(zones_found) > 1:
            # Conflito entre camadas
            conflicts = self._analyze_conflicts(camadas)
            zona_final, confidence, recommendation, requires_manual = self._resolve_conflicts(
                camadas, conflicts, endereco, inscricao
            )
        
        else:
            # Nenhuma detecção válida
            zona_final = "ZR-4"  # Padrão atual
            confidence = ZoneConfidence.DESCONHECIDO
            recommendation = "Não foi possível determinar o zoneamento com precisão"
            requires_manual = True
        
        return LayeredZoneResult(
            zona_final=zona_final,
            confidence=confidence,
            camadas=camadas,
            conflicts=conflicts,
            validations=validations,
            recommendation=recommendation,
            requires_manual_check=requires_manual,
            details={
                "endereco": endereco,
                "inscricao": inscricao,
                "coordinates": coordinates,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    def _query_ippuc_api(self, endereco: str, coordinates: Tuple[float, float] = None) -> str:
        """
        Consulta à API oficial do IPPUC (quando disponível)
        """
        
        if not self.ippuc_api_available:
            raise Exception("API IPPUC não disponível")
        
        # Implementação futura da API oficial
        # Por enquanto, simular o que seria a resposta
        
        if coordinates:
            # Consulta por coordenadas (mais precisa)
            endpoint = f"{self.ippuc_base_url}/zoneamento/coordenadas"
            params = {
                "lat": coordinates[0],
                "lon": coordinates[1],
                "api_key": self.ippuc_api_key
            }
        else:
            # Consulta por endereço
            endpoint = f"{self.ippuc_base_url}/zoneamento/endereco"
            params = {
                "endereco": endereco,
                "api_key": self.ippuc_api_key
            }
        
        response = requests.get(endpoint, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return data.get("zona", "")
        else:
            raise Exception(f"API retornou código {response.status_code}")
    
    def _check_sehis_specialized(self, endereco: str, inscricao: str, 
                               coordinates: Tuple[float, float] = None) -> Optional[Dict]:
        """
        Verificação especializada de SEHIS com base expandida
        """
        
        # Base expandida de SEHIS baseada nas sugestões da Claude Web
        sehis_areas = {
            # SEHIS oficiais conhecidos em Curitiba
            "cidade industrial de curitiba": {"zona": "SEHIS", "tipo": "CIC"},
            "cic": {"zona": "SEHIS", "tipo": "Cidade Industrial"},
            "tatuquara": {"zona": "SEHIS", "tipo": "Habitação Social"},
            "umbará": {"zona": "SEHIS", "tipo": "Habitação Social"},
            "sitio cercado": {"zona": "SEHIS", "tipo": "COHAB"},
            "sítio cercado": {"zona": "SEHIS", "tipo": "COHAB"},
            "campo de santana": {"zona": "SEHIS", "tipo": "Habitação Social"},
            "vila torres": {"zona": "SEHIS", "tipo": "Habitação Social"},
            "bairro novo": {"zona": "SEHIS", "tipo": "Habitação Social"},
            "caximba": {"zona": "SEHIS", "tipo": "Habitação Social"},
            "parolin": {"zona": "SEHIS", "tipo": "Habitação Social"},  # Algumas áreas
            
            # Novos SEHIS baseados em pesquisa adicional
            "conjunto habitacional": {"zona": "SEHIS", "tipo": "Genérico COHAB"},
            "residencial social": {"zona": "SEHIS", "tipo": "Habitação Social"},
            "loteamento social": {"zona": "SEHIS", "tipo": "Habitação Social"},
        }
        
        endereco_lower = endereco.lower() if endereco else ""
        
        # Verificar por endereço
        for area, info in sehis_areas.items():
            if area in endereco_lower:
                return {
                    "zona": "SEHIS",
                    "tipo": info["tipo"],
                    "matched_term": area,
                    "confidence": 0.8
                }
        
        # Verificar por inscrição (usar sistema existente)
        if inscricao:
            from inscription_sehis_detector import InscriptionSEHISDetector
            detector = InscriptionSEHISDetector()
            result = detector.analyze_inscription(inscricao)
            
            if result.is_likely_sehis and result.confidence >= 0.5:
                return {
                    "zona": "SEHIS",
                    "tipo": "Por Inscrição",
                    "matched_term": inscricao,
                    "confidence": result.confidence
                }
        
        return None
    
    def _validate_by_coordinates(self, coordinates: Tuple[float, float]) -> Optional[str]:
        """
        Validação por coordenadas conhecidas e verificadas
        """
        
        lat, lon = coordinates
        
        # Áreas SEHIS conhecidas por coordenadas (expandir com dados oficiais)
        sehis_regions = [
            # CIC/Cidade Industrial
            {"bounds": [(-25.52, -49.35), (-25.50, -49.30)], "zona": "SEHIS", "nome": "CIC"},
            # Tatuquara
            {"bounds": [(-25.58, -49.35), (-25.55, -49.32)], "zona": "SEHIS", "nome": "Tatuquara"},
            # Umbará
            {"bounds": [(-25.58, -49.30), (-25.55, -49.27)], "zona": "SEHIS", "nome": "Umbará"},
            # Campo de Santana
            {"bounds": [(-25.61, -49.35), (-25.58, -49.32)], "zona": "SEHIS", "nome": "Campo de Santana"},
            # Sítio Cercado
            {"bounds": [(-25.54, -49.36), (-25.52, -49.34)], "zona": "SEHIS", "nome": "Sítio Cercado"},
        ]
        
        for region in sehis_regions:
            bounds = region["bounds"]
            (lat_min, lon_min), (lat_max, lon_max) = bounds
            
            if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
                return region["zona"]
        
        return None
    
    def _analyze_conflicts(self, camadas: Dict[str, str]) -> List[str]:
        """
        Analisa conflitos entre as diferentes camadas
        """
        
        conflicts = []
        zones = list(camadas.values())
        unique_zones = list(set(zones))
        
        if len(unique_zones) > 1:
            for i, source1 in enumerate(camadas.items()):
                for source2 in list(camadas.items())[i+1:]:
                    if source1[1] != source2[1]:
                        conflicts.append(f"{source1[0]} diz {source1[1]} vs {source2[0]} diz {source2[1]}")
        
        return conflicts
    
    def _resolve_conflicts(self, camadas: Dict[str, str], conflicts: List[str],
                          endereco: str, inscricao: str) -> Tuple[str, ZoneConfidence, str, bool]:
        """
        Resolve conflitos entre camadas usando regras de prioridade
        """
        
        # REGRA 1: API oficial tem prioridade máxima
        if "ippuc_oficial" in camadas:
            return (
                camadas["ippuc_oficial"],
                ZoneConfidence.OFICIAL_API,
                "Usado resultado da API oficial do IPPUC",
                False
            )
        
        # REGRA 2: SEHIS especializada tem prioridade sobre zoneamento básico
        if "sehis_especializada" in camadas and camadas["sehis_especializada"] == "SEHIS":
            other_zones = [z for k, z in camadas.items() if k != "sehis_especializada" and z != "SEHIS"]
            if other_zones:  # Há conflito
                return (
                    "SEHIS",
                    ZoneConfidence.VALIDADO_CRUZADO,
                    f"SEHIS confirmado por detector especializado, sobrepondo {', '.join(other_zones)}",
                    True  # Requer validação manual devido ao conflito
                )
        
        # REGRA 3: Coordenadas validadas têm alta prioridade
        if "coordenadas" in camadas:
            return (
                camadas["coordenadas"],
                ZoneConfidence.VALIDADO_CRUZADO,
                "Zona confirmada por coordenadas validadas",
                False
            )
        
        # REGRA 4: Shapefile como fallback
        if "shapefile" in camadas:
            return (
                camadas["shapefile"],
                ZoneConfidence.ESTIMADO_CONFIAVEL,
                f"Usando shapefile como base, mas há conflitos: {'; '.join(conflicts)}",
                True  # Requer validação manual
            )
        
        # REGRA 5: Padrão com necessidade de validação
        return (
            "ZR-4",
            ZoneConfidence.NECESSITA_VALIDACAO,
            f"Conflitos não resolvidos: {'; '.join(conflicts)}",
            True
        )
    
    def _determine_confidence(self, camadas: Dict[str, str], validations: Dict[str, bool]) -> ZoneConfidence:
        """
        Determina o nível de confiabilidade baseado nas camadas ativas
        """
        
        if validations.get("ippuc_api"):
            return ZoneConfidence.OFICIAL_API
        
        active_layers = sum(1 for v in validations.values() if v)
        
        if active_layers >= 3:
            return ZoneConfidence.VALIDADO_CRUZADO
        elif active_layers == 2:
            return ZoneConfidence.ESTIMADO_CONFIAVEL
        elif active_layers == 1:
            return ZoneConfidence.ESTIMADO_BAIXA
        else:
            return ZoneConfidence.DESCONHECIDO
    
    def _load_sehis_database(self) -> Dict:
        """Carrega base de dados especializada de SEHIS"""
        # Implementar carregamento de arquivo JSON com dados SEHIS
        return {}
    
    def _load_verified_coordinates(self) -> Dict:
        """Carrega coordenadas verificadas"""
        # Implementar carregamento de coordenadas validadas
        return {}
    
    def _load_known_conflicts(self) -> Dict:
        """Carrega conflitos conhecidos e suas resoluções"""
        # Implementar base de conflitos conhecidos
        return {}
    
    def enable_ippuc_api(self, api_key: str, base_url: str = None):
        """
        Habilita a API oficial do IPPUC quando estiver disponível
        """
        self.ippuc_api_key = api_key
        if base_url:
            self.ippuc_base_url = base_url
        self.ippuc_api_available = True
        logger.info("API IPPUC habilitada no sistema híbrido")

def test_hybrid_system():
    """
    Testa o sistema híbrido com casos reais
    """
    
    print("TESTE DO SISTEMA HIBRIDO DE ZONEAMENTO")
    print("=" * 50)
    
    system = HybridZoningSystem()
    
    test_cases = [
        {
            "endereco": "Cidade Industrial, Curitiba",
            "inscricao": "03012345600001",
            "descricao": "CIC - deveria ser SEHIS"
        },
        {
            "endereco": "",
            "inscricao": "05523456700002",
            "descricao": "Apenas inscrição Tatuquara"
        },
        {
            "endereco": "Centro, Curitiba",
            "inscricao": "",
            "descricao": "Centro - não SEHIS"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\nTESTE {i}: {case['descricao']}")
        print(f"Endereço: {case['endereco'] or 'VAZIO'}")
        print(f"Inscrição: {case['inscricao'] or 'VAZIO'}")
        
        try:
            result = system.detect_zone_hybrid(
                endereco=case['endereco'],
                inscricao=case['inscricao']
            )
            
            print(f"Zona Final: {result.zona_final}")
            print(f"Confiabilidade: {result.confidence.value}")
            print(f"Camadas Ativas: {len(result.camadas)}")
            
            for camada, zona in result.camadas.items():
                print(f"  - {camada}: {zona}")
            
            if result.conflicts:
                print(f"Conflitos: {len(result.conflicts)}")
                for conflict in result.conflicts:
                    print(f"  ! {conflict}")
            
            print(f"Recomendação: {result.recommendation}")
            
            if result.requires_manual_check:
                print("⚠️ REQUER VALIDAÇÃO MANUAL")
            else:
                print("✓ Resultado confiável")
                
        except Exception as e:
            print(f"ERRO: {e}")

if __name__ == "__main__":
    test_hybrid_system()