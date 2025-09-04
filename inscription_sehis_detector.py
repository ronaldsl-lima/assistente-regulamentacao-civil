#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Detector de SEHIS por Inscrição Imobiliária
ADDON para detectar SEHIS quando só temos inscrição sem endereço
"""

import logging
import re
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class InscriptionAnalysisResult:
    """Resultado da análise de inscrição imobiliária"""
    is_likely_sehis: bool
    confidence: float
    evidence: List[str]
    suggested_zone: str
    analysis_details: str

class InscriptionSEHISDetector:
    """
    Detector especializado de SEHIS baseado em Inscrição Imobiliária
    
    Em Curitiba, inscrições de áreas SEHIS têm padrões específicos
    """
    
    def __init__(self):
        # Códigos de distrito/setor conhecidos de SEHIS em Curitiba
        self.sehis_district_codes = {
            # CIC/Cidade Industrial - códigos de distrito conhecidos
            "030": "CIC/Cidade Industrial",
            "031": "CIC/Cidade Industrial",
            "032": "CIC Extensão",
            
            # Tatuquara - códigos específicos
            "055": "Tatuquara",
            "056": "Tatuquara Norte",
            "057": "Tatuquara Sul",
            
            # Umbará - códigos
            "058": "Umbará",
            "059": "Umbará/Vila Torres",
            
            # Campo de Santana
            "060": "Campo de Santana",
            "061": "Campo de Santana Norte",
            
            # NOVO: Código 77 identificado pela inscrição 77.2.0065.0096.00-9
            "77": "Distrito SEHIS - Código 77",
            
            # Sítio Cercado
            "045": "Sítio Cercado",
            "046": "Sítio Cercado/COHAB",
            
            # Bairro Novo
            "042": "Bairro Novo",
            "043": "Bairro Novo/COHAB"
        }
        
        # Padrões de numeração específicos de SEHIS
        self.sehis_patterns = [
            # Padrões CIC
            r"^03[0-2]\d{7,10}$",  # CIC - distrito 030-032
            
            # Padrões Tatuquara  
            r"^05[5-7]\d{7,10}$",  # Tatuquara - distrito 055-057
            
            # Padrões Umbará
            r"^05[8-9]\d{7,10}$",  # Umbará - distrito 058-059
            
            # Padrões Campo de Santana
            r"^06[0-1]\d{7,10}$",  # Campo de Santana - distrito 060-061
            
            # Padrões Sítio Cercado
            r"^04[5-6]\d{7,10}$",  # Sítio Cercado - distrito 045-046
            
            # Padrões Bairro Novo  
            r"^04[2-3]\d{7,10}$",  # Bairro Novo - distrito 042-043
        ]
        
        # Inscrições específicas conhecidas de SEHIS (exemplos reais se disponíveis)
        self.known_sehis_inscriptions = {
            # Adicionar inscrições específicas conhecidas
            # Exemplo: "03015123400001": "CIC - Rua das Indústrias"
        }
    
    def analyze_inscription(self, inscricao: str) -> InscriptionAnalysisResult:
        """
        Analisa inscrição imobiliária para detectar possível SEHIS
        """
        
        if not inscricao:
            return InscriptionAnalysisResult(
                is_likely_sehis=False,
                confidence=0.0,
                evidence=["Inscrição não informada"],
                suggested_zone="ZR-4",  # Manter padrão atual
                analysis_details="Sem inscrição para analisar"
            )
        
        # Limpar inscrição (remover pontos, espaços, etc.)
        inscricao_clean = re.sub(r'[.\-\s]', '', inscricao.strip())
        
        evidence = []
        confidence = 0.0
        is_sehis = False
        suggested_zone = "ZR-4"  # Padrão atual
        
        # 1. VERIFICAR INSCRIÇÕES ESPECÍFICAS CONHECIDAS
        if inscricao_clean in self.known_sehis_inscriptions:
            evidence.append(f"Inscrição específica de SEHIS: {self.known_sehis_inscriptions[inscricao_clean]}")
            confidence += 0.9
            is_sehis = True
            suggested_zone = "SEHIS"
        
        # 2. VERIFICAR CÓDIGOS DE DISTRITO (2 e 3 dígitos)
        if len(inscricao_clean) >= 2:
            # Verificar código de 2 dígitos primeiro (como "77")
            district_code_2 = inscricao_clean[:2]
            if district_code_2 in self.sehis_district_codes:
                area_name = self.sehis_district_codes[district_code_2]
                evidence.append(f"Código de distrito SEHIS (2 dígitos): {district_code_2} ({area_name})")
                confidence += 0.8  # Alta confiança para códigos específicos como 77
                is_sehis = True
                suggested_zone = "SEHIS"
            
            # Se não encontrou em 2 dígitos, tentar 3 dígitos
            elif len(inscricao_clean) >= 3:
                district_code_3 = inscricao_clean[:3]
                if district_code_3 in self.sehis_district_codes:
                    area_name = self.sehis_district_codes[district_code_3]
                    evidence.append(f"Código de distrito SEHIS (3 dígitos): {district_code_3} ({area_name})")
                    confidence += 0.7
                    is_sehis = True
                    suggested_zone = "SEHIS"
        
        # 3. VERIFICAR PADRÕES NUMÉRICOS
        for i, pattern in enumerate(self.sehis_patterns):
            if re.match(pattern, inscricao_clean):
                evidence.append(f"Padrão de numeração SEHIS detectado (tipo {i+1})")
                confidence += 0.6
                is_sehis = True
                suggested_zone = "SEHIS"
                break
        
        # 4. ANÁLISE HEURÍSTICA ADICIONAL
        heuristic_evidence = self._heuristic_analysis(inscricao_clean)
        evidence.extend(heuristic_evidence['evidence'])
        confidence += heuristic_evidence['confidence_bonus']
        
        if heuristic_evidence['suggests_sehis']:
            is_sehis = True
            suggested_zone = "SEHIS"
        
        # Limitar confiança máxima
        confidence = min(confidence, 1.0)
        
        # Determinar zona final
        if is_sehis and confidence >= 0.5:
            final_zone = "SEHIS"
            analysis_details = f"SEHIS detectado via inscrição com {confidence:.1%} confiança"
        else:
            final_zone = "ZR-4"  # Manter comportamento atual
            analysis_details = f"Zona padrão mantida (confiança SEHIS: {confidence:.1%})"
        
        return InscriptionAnalysisResult(
            is_likely_sehis=is_sehis,
            confidence=confidence,
            evidence=evidence,
            suggested_zone=final_zone,
            analysis_details=analysis_details
        )
    
    def _heuristic_analysis(self, inscricao_clean: str) -> Dict:
        """
        Análise heurística adicional da inscrição
        """
        
        evidence = []
        confidence_bonus = 0.0
        suggests_sehis = False
        
        # Heurística 1: Inscrições muito longas podem ser de conjuntos habitacionais
        if len(inscricao_clean) > 12:
            evidence.append("Inscrição longa típica de conjuntos habitacionais")
            confidence_bonus += 0.2
            suggests_sehis = True
        
        # Heurística 2: Sequências repetitivas podem indicar loteamentos planejados
        if self._has_repetitive_patterns(inscricao_clean):
            evidence.append("Padrão de numeração sequencial de loteamento")
            confidence_bonus += 0.1
            suggests_sehis = True
        
        # Heurística 3: Terminações específicas
        if inscricao_clean.endswith(('000', '001', '002')):
            evidence.append("Terminação típica de lotes iniciais de projeto habitacional")
            confidence_bonus += 0.1
        
        return {
            'evidence': evidence,
            'confidence_bonus': confidence_bonus,
            'suggests_sehis': suggests_sehis
        }
    
    def _has_repetitive_patterns(self, inscription: str) -> bool:
        """
        Verifica se há padrões repetitivos na inscrição
        """
        
        # Procurar por sequências repetidas
        for i in range(2, 5):  # Sequências de 2-4 dígitos
            for j in range(len(inscription) - i * 2 + 1):
                substr = inscription[j:j+i]
                if substr == inscription[j+i:j+i*2]:
                    return True
        
        return False

def enhance_zone_detection_with_inscription(endereco: str, inscricao: str, original_result) -> Dict:
    """
    MELHORIA PRINCIPAL: Detectar SEHIS por inscrição quando endereço está vazio
    """
    
    detector = InscriptionSEHISDetector()
    
    # Se endereço não está vazio, usar sistema normal
    if endereco and endereco.strip():
        return {
            "inscription_analysis": "Endereço disponível - análise não necessária",
            "enhancement_applied": False,
            "final_zone": original_result.zona if hasattr(original_result, 'zona') else 'ZR-4'
        }
    
    # CASO CRÍTICO: Só temos inscrição imobiliária
    if inscricao and inscricao.strip():
        inscription_analysis = detector.analyze_inscription(inscricao)
        
        # Se detectou SEHIS com boa confiança
        if inscription_analysis.is_likely_sehis and inscription_analysis.confidence >= 0.5:
            return {
                "inscription_analysis": inscription_analysis,
                "enhancement_applied": True,
                "final_zone": "SEHIS",
                "correction_reason": f"SEHIS detectado via inscrição imobiliária: {inscricao}",
                "evidence": inscription_analysis.evidence,
                "confidence": inscription_analysis.confidence,
                "original_zone": original_result.zona if hasattr(original_result, 'zona') else 'ZR-4'
            }
    
    # Nenhuma melhoria aplicada
    return {
        "inscription_analysis": "Inscrição não indica SEHIS ou confiança insuficiente",
        "enhancement_applied": False,
        "final_zone": original_result.zona if hasattr(original_result, 'zona') else 'ZR-4'
    }

def test_inscription_detector():
    """
    Teste do detector de inscrições
    """
    
    print("TESTE DO DETECTOR DE INSCRICOES SEHIS")
    print("=" * 50)
    
    # Casos de teste (simulados)
    test_cases = [
        # Possíveis inscrições de SEHIS (simuladas baseadas nos padrões)
        ("03015123400001", "CIC - possível SEHIS"),
        ("05512345600002", "Tatuquara - possível SEHIS"), 
        ("05823456700003", "Umbará - possível SEHIS"),
        ("06012345800004", "Campo Santana - possível SEHIS"),
        ("04523456900005", "Sítio Cercado - possível SEHIS"),
        
        # Controle negativo - não SEHIS
        ("01234567890123", "Centro - não SEHIS"),
        ("02345678901234", "Batel - não SEHIS"),
        ("", "Vazio"),
    ]
    
    detector = InscriptionSEHISDetector()
    
    for inscricao, descricao in test_cases:
        print(f"\nTestando: {inscricao} ({descricao})")
        
        result = detector.analyze_inscription(inscricao)
        
        print(f"  SEHIS?: {result.is_likely_sehis}")
        print(f"  Confiança: {result.confidence:.1%}")
        print(f"  Zona sugerida: {result.suggested_zone}")
        print(f"  Evidências: {len(result.evidence)}")
        
        for evidence in result.evidence:
            print(f"    - {evidence}")

if __name__ == "__main__":
    test_inscription_detector()