#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple IPPUC Scraper - Versão sem Selenium
Usando apenas requests para consultas HTTP
"""

import requests
import time
import json
import logging
import re
from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime
import sqlite3

logger = logging.getLogger(__name__)

@dataclass
class SimpleIPPUCResult:
    """Resultado da consulta IPPUC simplificada"""
    inscricao: str
    zona: str
    confidence: str = "ESTIMADO_WEB"
    source: str = "ippuc_simple_scraper"
    details: str = ""
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class SimpleIPPUCScraper:
    """
    Scraper simplificado para IPPUC GeoCuritiba
    Focado em funcionalidade sem dependências complexas
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://geocuritiba.ippuc.org.br"
        self.cache_db = "simple_ippuc_cache.db"
        
        # Headers realistas
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9',
            'Connection': 'keep-alive'
        })
        
        self._init_cache()
    
    def _init_cache(self):
        """Inicializa cache SQLite"""
        try:
            with sqlite3.connect(self.cache_db) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS simple_cache (
                        inscricao TEXT PRIMARY KEY,
                        zona TEXT,
                        details TEXT,
                        timestamp DATETIME
                    )
                """)
        except Exception as e:
            logger.error(f"Erro ao inicializar cache: {e}")
    
    def query_inscription(self, inscricao: str) -> Optional[SimpleIPPUCResult]:
        """
        Consulta inscrição usando múltiplas estratégias
        """
        
        # Verificar cache primeiro
        cached = self._get_from_cache(inscricao)
        if cached:
            return cached
        
        # Estratégia 1: Tentar página de confrontantes
        result = self._try_confrontantes_page(inscricao)
        if result:
            self._save_to_cache(result)
            return result
        
        # Estratégia 2: Tentar possíveis APIs
        result = self._try_api_endpoints(inscricao)
        if result:
            self._save_to_cache(result)
            return result
        
        # Estratégia 3: Análise por padrões da inscrição
        result = self._analyze_inscription_pattern(inscricao)
        if result:
            self._save_to_cache(result)
            return result
        
        return None
    
    def _try_confrontantes_page(self, inscricao: str) -> Optional[SimpleIPPUCResult]:
        """
        Tenta acessar página de confrontantes
        """
        
        try:
            logger.info(f"Tentando acessar confrontantes para {inscricao}")
            
            # Tentar diferentes URLs
            urls = [
                f"{self.base_url}/confrontantes/?inscricao={inscricao}",
                f"{self.base_url}/confrontantes/index.php?inscricao={inscricao}",
                f"{self.base_url}/confrontantes/search.php?q={inscricao}"
            ]
            
            for url in urls:
                try:
                    response = self.session.get(url, timeout=10)
                    if response.status_code == 200:
                        # Analisar conteúdo da página
                        zona = self._extract_zone_from_html(response.text)
                        if zona and zona != "NÃO_IDENTIFICADO":
                            return SimpleIPPUCResult(
                                inscricao=inscricao,
                                zona=zona,
                                details=f"Extraído da página: {url}",
                                source="ippuc_web_page"
                            )
                except requests.RequestException:
                    continue
        
        except Exception as e:
            logger.error(f"Erro ao acessar confrontantes: {e}")
        
        return None
    
    def _try_api_endpoints(self, inscricao: str) -> Optional[SimpleIPPUCResult]:
        """
        Tenta possíveis endpoints de API
        """
        
        api_endpoints = [
            f"{self.base_url}/api/inscricao/{inscricao}",
            f"{self.base_url}/api/zoneamento?inscricao={inscricao}",
            f"{self.base_url}/services/geocode?inscricao={inscricao}",
            f"{self.base_url}/ws/inscricao/{inscricao}.json"
        ]
        
        for endpoint in api_endpoints:
            try:
                response = self.session.get(endpoint, timeout=5)
                if response.status_code == 200:
                    # Tentar parse JSON
                    try:
                        data = response.json()
                        zona = self._extract_zone_from_json(data)
                        if zona:
                            return SimpleIPPUCResult(
                                inscricao=inscricao,
                                zona=zona,
                                details=f"API: {endpoint}",
                                source="ippuc_api_endpoint"
                            )
                    except json.JSONDecodeError:
                        # Talvez seja HTML
                        zona = self._extract_zone_from_html(response.text)
                        if zona and zona != "NÃO_IDENTIFICADO":
                            return SimpleIPPUCResult(
                                inscricao=inscricao,
                                zona=zona,
                                details=f"HTML API: {endpoint}",
                                source="ippuc_html_api"
                            )
            except requests.RequestException:
                continue
        
        return None
    
    def _analyze_inscription_pattern(self, inscricao: str) -> Optional[SimpleIPPUCResult]:
        """
        Analisa padrões da inscrição para inferir SEHIS
        """
        
        if len(inscricao) < 3:
            return None
        
        # Padrões conhecidos de distritos SEHIS em Curitiba
        sehis_districts = {
            "030": "CIC/Cidade Industrial",
            "031": "CIC/Cidade Industrial Ext",
            "055": "Tatuquara", 
            "058": "Umbará",
            "060": "Campo de Santana",
            "045": "Sítio Cercado",
            "070": "Fazendinha",
            "075": "Caximba",
            "77": "Distrito SEHIS - Código 77"  # NOVO: Baseado na inscrição 77.2.0065.0096.00-9
        }
        
        # Extrair código do distrito - tentar 2 e 3 dígitos
        district_code_2 = inscricao[:2]  # Códigos de 2 dígitos como "77"
        district_code_3 = inscricao[:3]  # Códigos de 3 dígitos como "030"
        
        # Verificar códigos de 2 dígitos primeiro
        if district_code_2 in sehis_districts:
            return SimpleIPPUCResult(
                inscricao=inscricao,
                zona="SEHIS",
                details=f"Distrito SEHIS detectado: {sehis_districts[district_code_2]} (código {district_code_2})",
                source="pattern_analysis",
                confidence="ESTIMADO_CONFIAVEL"
            )
        
        # Depois verificar códigos de 3 dígitos
        elif district_code_3 in sehis_districts:
            return SimpleIPPUCResult(
                inscricao=inscricao,
                zona="SEHIS",
                details=f"Distrito SEHIS detectado: {sehis_districts[district_code_3]} (código {district_code_3})",
                source="pattern_analysis",
                confidence="ESTIMADO_CONFIAVEL"
            )
        
        # Padrões de zona central (ZR-4)
        central_districts = ["001", "002", "003", "010", "011"]
        if district_code in central_districts:
            return SimpleIPPUCResult(
                inscricao=inscricao,
                zona="ZR-4",
                details=f"Distrito central detectado (código {district_code})",
                source="pattern_analysis",
                confidence="ESTIMADO_BAIXA"
            )
        
        return None
    
    def _extract_zone_from_html(self, html: str) -> Optional[str]:
        """
        Extrai zona de conteúdo HTML
        """
        
        # Padrões de busca para zonas
        patterns = [
            r'zona[:\s]*([A-Z0-9\-]+)',
            r'zoneamento[:\s]*([A-Z0-9\-]+)',
            r'ZR[\-\s]*(\d+)',
            r'SEHIS',
            r'ZC[\-\s]*\d*',
            r'ZOS[\-\s]*\d*'
        ]
        
        html_upper = html.upper()
        
        for pattern in patterns:
            matches = re.findall(pattern, html_upper, re.IGNORECASE)
            if matches:
                zona = matches[0].strip()
                if zona and len(zona) <= 10:  # Filtrar matches muito longos
                    return zona
        
        # Busca específica por SEHIS
        if 'SEHIS' in html_upper:
            return 'SEHIS'
        
        return None
    
    def _extract_zone_from_json(self, data: dict) -> Optional[str]:
        """
        Extrai zona de dados JSON
        """
        
        # Possíveis chaves para zona
        zone_keys = ['zona', 'zoneamento', 'zone', 'uso_solo', 'land_use']
        
        for key in zone_keys:
            if key in data:
                zona = str(data[key]).strip()
                if zona and zona.upper() != 'NULL':
                    return zona.upper()
        
        # Buscar em dados aninhados
        for value in data.values():
            if isinstance(value, dict):
                zona = self._extract_zone_from_json(value)
                if zona:
                    return zona
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        zona = self._extract_zone_from_json(item)
                        if zona:
                            return zona
        
        return None
    
    def _get_from_cache(self, inscricao: str) -> Optional[SimpleIPPUCResult]:
        """
        Recupera do cache (válido por 24h)
        """
        
        try:
            with sqlite3.connect(self.cache_db) as conn:
                cursor = conn.execute("""
                    SELECT zona, details, timestamp
                    FROM simple_cache
                    WHERE inscricao = ?
                    AND datetime(timestamp, '+24 hours') > datetime('now')
                """, (inscricao,))
                
                row = cursor.fetchone()
                if row:
                    zona, details, timestamp_str = row
                    return SimpleIPPUCResult(
                        inscricao=inscricao,
                        zona=zona,
                        details=details,
                        timestamp=datetime.fromisoformat(timestamp_str),
                        source="cache"
                    )
        except Exception as e:
            logger.error(f"Erro ao acessar cache: {e}")
        
        return None
    
    def _save_to_cache(self, result: SimpleIPPUCResult):
        """
        Salva no cache
        """
        
        try:
            with sqlite3.connect(self.cache_db) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO simple_cache
                    (inscricao, zona, details, timestamp)
                    VALUES (?, ?, ?, ?)
                """, (result.inscricao, result.zona, result.details, result.timestamp.isoformat()))
        except Exception as e:
            logger.error(f"Erro ao salvar cache: {e}")

def test_simple_scraper():
    """
    Teste do scraper simplificado
    """
    
    print("TESTE DO SIMPLE IPPUC SCRAPER")
    print("=" * 40)
    
    scraper = SimpleIPPUCScraper()
    
    test_inscriptions = [
        "03012345600001",  # CIC - deveria ser SEHIS
        "05523456700002",  # Tatuquara - deveria ser SEHIS
        "00123456789012"   # Centro - teste controle
    ]
    
    for inscricao in test_inscriptions:
        print(f"\nTestando: {inscricao}")
        
        result = scraper.query_inscription(inscricao)
        
        if result:
            print(f"  OK Zona: {result.zona}")
            print(f"  OK Confianca: {result.confidence}")
            print(f"  OK Fonte: {result.source}")
            print(f"  OK Detalhes: {result.details}")
        else:
            print(f"  ERRO Nenhum resultado")
    
    print("\nTeste concluído!")

if __name__ == "__main__":
    test_simple_scraper()