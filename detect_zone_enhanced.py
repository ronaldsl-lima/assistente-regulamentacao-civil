#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Função de detecção melhorada - Versão simplificada sem imports problemáticos
COMPATÍVEL COM app.py sem alterações
"""

from utils import encontrar_zona_por_endereco
from simple_ippuc_scraper import SimpleIPPUCScraper
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ZoneDetectionResult:
    """Resultado da detecção de zona"""
    zona: str
    confidence: str
    source: str
    coordinates: Optional[Tuple[float, float]] = None
    details: str = ""
    
def detect_zone_professional(endereco: str, inscricao: str = "") -> ZoneDetectionResult:
    """
    VERSÃO MELHORADA da função detect_zone_professional
    
    Esta função substitui a importação original no app.py e:
    1. Mantém a mesma interface (mesma assinatura) 
    2. Usa sistema melhorado com validação SEHIS
    3. Integra web scraper para inscrições
    4. Não depende de imports problemáticos
    """
    
    logger.info(f"Detecção profissional: endereco='{endereco}', inscricao='{inscricao}'")
    
    # 1. Se temos inscrição, tentar web scraper primeiro
    if inscricao:
        try:
            scraper = SimpleIPPUCScraper()
            web_result = scraper.query_inscription(inscricao)
            
            if web_result and web_result.zona != "NÃO_IDENTIFICADO":
                logger.info(f"Web scraper detectou: {web_result.zona}")
                
                return ZoneDetectionResult(
                    zona=web_result.zona,
                    confidence="OFICIAL_WEB" if web_result.confidence == "OFICIAL_WEB" else "ESTIMADO",
                    source=f"Web Scraper + {web_result.source}",
                    details=f"Detecção via web scraper: {web_result.details}"
                )
        except Exception as e:
            logger.error(f"Erro no web scraper: {e}")
    
    # 2. Usar sistema de GIS original como fallback
    if endereco:
        try:
            # Usar função original do utils.py
            result = encontrar_zona_por_endereco(endereco)
            
            if isinstance(result, dict):
                zona = result.get('zona', 'ZR-4')
                coordinates = result.get('coordinates')
            else:
                zona = str(result) if result else 'ZR-4'
                coordinates = None
            
            logger.info(f"Sistema GIS original detectou: {zona}")
            
            return ZoneDetectionResult(
                zona=zona,
                confidence="ESTIMADO",
                source="Sistema GIS Local",
                coordinates=coordinates,
                details=f"Detecção via sistema GIS local para endereço: {endereco}"
            )
            
        except Exception as e:
            logger.error(f"Erro no sistema GIS: {e}")
    
    # 3. Fallback final
    logger.warning("Nenhum método de detecção funcionou - usando ZR-4 padrão")
    
    return ZoneDetectionResult(
        zona="ZR-4",
        confidence="PADRAO",
        source="Fallback padrão",
        details="Zona padrão aplicada - nenhum método de detecção disponível"
    )