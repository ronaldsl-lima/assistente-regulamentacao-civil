#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema Aprimorado com Priorização do Shapefile Oficial
Combina detector oficial + sistema existente
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from detect_zone_enhanced import detect_zone_professional
from official_zone_detector_fixed import detect_zone_official
from simple_ippuc_scraper import SimpleIPPUCScraper

logger = logging.getLogger(__name__)

@dataclass
class EnhancedZoneResult:
    """Resultado aprimorado com shapefile oficial"""
    zona: str
    confidence: str
    source: str
    coordinates: Optional[Tuple[float, float]] = None
    details: str = ""
    official_zone: Optional[str] = None
    official_name: Optional[str] = None
    web_scraper_zone: Optional[str] = None
    local_zone: Optional[str] = None
    consolidation_method: str = ""
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class EnhancedOfficialSystem:
    """
    Sistema que prioriza dados oficiais do shapefile
    """
    
    def __init__(self):
        self.web_scraper = SimpleIPPUCScraper()
        logger.info("Sistema oficial aprimorado inicializado")
    
    def detect_zone_enhanced_official(self, endereco: str, inscricao: str = "") -> EnhancedZoneResult:
        """
        Detecção com priorização do shapefile oficial
        """
        
        logger.info(f"Detecção aprimorada: {endereco} / {inscricao}")
        
        # Resultados de diferentes fontes
        official_result = None
        web_result = None
        local_result = None
        coordinates = None
        
        # 1. Sistema local para obter coordenadas
        try:
            local_result = detect_zone_professional(endereco, inscricao)
            if hasattr(local_result, 'coordinates') and local_result.coordinates:
                coordinates = local_result.coordinates
                logger.info(f"Coordenadas obtidas: {coordinates}")
        except Exception as e:
            logger.error(f"Erro no sistema local: {e}")
        
        # 2. Se temos coordenadas, usar shapefile oficial
        if coordinates:
            try:
                lat, lon = coordinates
                official_result = detect_zone_official(lat, lon)
                logger.info(f"Shapefile oficial: {official_result.zona if official_result else 'Não encontrado'}")
            except Exception as e:
                logger.error(f"Erro no shapefile oficial: {e}")
        
        # 3. Web scraper por inscrição
        if inscricao:
            try:
                web_result = self.web_scraper.query_inscription(inscricao)
                logger.info(f"Web scraper: {web_result.zona if web_result else 'Não encontrado'}")
            except Exception as e:
                logger.error(f"Erro no web scraper: {e}")
        
        # 4. Consolidar resultados com prioridade
        return self._consolidate_results(
            official_result, web_result, local_result, 
            coordinates, endereco, inscricao
        )
    
    def _consolidate_results(self, official_result, web_result, local_result, 
                           coordinates, endereco, inscricao) -> EnhancedZoneResult:
        """
        Consolida resultados priorizando dados oficiais
        """
        
        # Extrair zonas de cada fonte
        official_zone = official_result.zona if official_result else None
        official_name = official_result.nm_zona if official_result else None
        web_zone = web_result.zona if web_result else None
        local_zone = local_result.zona if local_result else None
        
        # Lógica de priorização
        zona_final = None
        confidence = "DESCONHECIDO"
        source = "ERRO"
        consolidation_method = ""
        details = ""
        
        # PRIORIDADE 1: Shapefile oficial
        if official_zone and official_zone not in ['INDETERMINADO', 'NULL']:
            zona_final = official_zone
            confidence = "OFICIAL_SHAPEFILE"
            source = "ZONEAMENTO_OFICIAL.shp"
            consolidation_method = "SHAPEFILE_OFICIAL"
            details = f"Zona oficial: {official_name} ({official_zone})"
            
            # Se SEHIS no oficial, manter
            if official_zone == 'SEHIS':
                details += " - SEHIS confirmado oficialmente"
            
        # PRIORIDADE 2: Web scraper (se SEHIS ou se oficial não disponível)
        elif web_zone and web_zone not in ['NÃO_IDENTIFICADO', 'NULL']:
            zona_final = web_zone
            confidence = "OFICIAL_WEB"
            source = "GeoCuritiba Web + Pattern Analysis"
            consolidation_method = "WEB_SCRAPER"
            details = f"Zona via web scraper: {web_zone}"
            
            # SEHIS tem prioridade especial
            if web_zone == 'SEHIS':
                confidence = "SEHIS_CONFIRMADO"
                details += " - SEHIS detectado via inscrição"
        
        # PRIORIDADE 3: Sistema local
        elif local_zone and local_zone not in ['INDETERMINADO', 'ZR-4']:  # Evitar ZR-4 genérico
            zona_final = local_zone
            confidence = "ESTIMADO_LOCAL"
            source = "Sistema híbrido local"
            consolidation_method = "SISTEMA_LOCAL"
            details = f"Zona estimada localmente: {local_zone}"
        
        # FALLBACK: ZR-4 padrão apenas se nada mais funcionar
        else:
            zona_final = "ZR-4"
            confidence = "PADRAO"
            source = "Fallback padrão"
            consolidation_method = "FALLBACK"
            details = "Zona padrão aplicada - verificação manual recomendada"
        
        # CORREÇÃO ESPECIAL: Se web scraper detectou SEHIS, sempre priorizar
        if web_zone == 'SEHIS' and zona_final != 'SEHIS':
            logger.info(f"CORREÇÃO SEHIS: {zona_final} -> SEHIS (web scraper)")
            zona_final = 'SEHIS'
            confidence = "SEHIS_CORRIGIDO"
            consolidation_method = "CORRECAO_SEHIS"
            details = f"Corrigido para SEHIS baseado em análise de inscrição"
        
        # VALIDAÇÃO: Se oficial e web concordam
        if official_zone and web_zone and official_zone == web_zone:
            confidence = "DUPLA_CONFIRMACAO"
            consolidation_method = "CONSENSO_OFICIAL_WEB"
            details += f" - Confirmado por múltiplas fontes oficiais"
        
        return EnhancedZoneResult(
            zona=zona_final,
            confidence=confidence,
            source=source,
            coordinates=coordinates,
            details=details,
            official_zone=official_zone,
            official_name=official_name,
            web_scraper_zone=web_zone,
            local_zone=local_zone,
            consolidation_method=consolidation_method
        )

def test_enhanced_official_system():
    """
    Teste do sistema aprimorado
    """
    
    print("TESTE DO SISTEMA OFICIAL APRIMORADO")
    print("=" * 50)
    
    system = EnhancedOfficialSystem()
    
    test_cases = [
        ("", "03012345600001", "CIC - Apenas inscrição (caso do engenheiro)"),
        ("Tatuquara, Curitiba", "05523456700002", "Tatuquara - SEHIS conhecido"),
        ("Centro, Curitiba", "", "Centro - Apenas endereço"),
        ("CIC, Curitiba", "03012345600001", "CIC - Endereço + inscrição"),
    ]
    
    for endereco, inscricao, desc in test_cases:
        print(f"\nTeste: {desc}")
        print(f"  Endereço: {endereco or 'VAZIO'}")
        print(f"  Inscrição: {inscricao or 'VAZIA'}")
        
        try:
            result = system.detect_zone_enhanced_official(endereco, inscricao)
            
            print(f"  ZONA FINAL: {result.zona}")
            print(f"  CONFIANÇA: {result.confidence}")
            print(f"  FONTE: {result.source}")
            print(f"  MÉTODO: {result.consolidation_method}")
            print(f"  DETALHES: {result.details}")
            
            if result.official_zone:
                print(f"  OFICIAL: {result.official_zone} ({result.official_name})")
            if result.web_scraper_zone:
                print(f"  WEB: {result.web_scraper_zone}")
            if result.local_zone:
                print(f"  LOCAL: {result.local_zone}")
            
            print("  SUCESSO")
            
        except Exception as e:
            print(f"  ERRO: {e}")
    
    print(f"\nTeste concluído!")

if __name__ == "__main__":
    test_enhanced_official_system()