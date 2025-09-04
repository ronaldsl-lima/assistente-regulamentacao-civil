#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Função de detecção melhorada - ADDON que melhora o sistema existente
COMPATÍVEL COM app.py sem alterações
"""

from enhanced_zone_detector import detect_zone_with_sehis_validation
from inscription_sehis_detector import enhance_zone_detection_with_inscription
import logging

logger = logging.getLogger(__name__)

def detect_zone_professional(endereco: str, inscricao: str = ""):
    """
    VERSÃO MELHORADA da função detect_zone_professional
    
    Esta função substitui a importação original no app.py e:
    1. Mantém a mesma interface (mesma assinatura)
    2. Usa o sistema melhorado com validação SEHIS
    3. É 100% compatível com o código existente
    4. NÃO quebra nada do sistema atual
    """
    
    try:
        # Usar detector melhorado
        result = detect_zone_with_sehis_validation(endereco)
        
        # NOVA FUNCIONALIDADE: Validação por inscrição imobiliária
        if inscricao:
            inscription_enhancement = enhance_zone_detection_with_inscription(
                endereco=endereco,
                inscricao=inscricao,
                original_result=result
            )
            
            # Se a inscrição sugere SEHIS, aplicar correção
            if inscription_enhancement.get('enhancement_applied'):
                class InscriptionCorrectedResult:
                    def __init__(self, original, correction_info):
                        self.zona = correction_info['final_zone']
                        self.confidence = "INSCRICAO_SEHIS"
                        self.source = "inscription_validator"
                        self.details = correction_info['correction_reason']
                        self.coordinates = getattr(original, 'coordinates', None)
                        self.original_detection = correction_info['original_zone']
                        self.correction_reason = correction_info['correction_reason']
                        self.inscription_evidence = correction_info.get('evidence', [])
                
                logger.info(f"🔧 SEHIS por inscrição: {inscricao} → {inscription_enhancement['final_zone']}")
                return InscriptionCorrectedResult(result, inscription_enhancement)
        
        # Log da melhoria se houve correção SEHIS por endereço
        if hasattr(result, 'correction_reason'):
            logger.info(f"🔧 SEHIS corrigido: {endereco} → {result.zona}")
        
        return result
        
    except Exception as e:
        logger.error(f"Erro no detector melhorado: {e}")
        # Fallback para detector original em caso de erro
        try:
            from gis_zone_detector import detect_zone_professional as original_detector
            return original_detector(endereco)
        except Exception as e2:
            logger.error(f"Erro também no detector original: {e2}")
            
            # Último fallback
            class ErrorResult:
                zona = "ZR-2"
                confidence = "ERRO"
                source = "fallback_error"
                details = f"Erro: {e}"
                coordinates = None
                
            return ErrorResult()

# Função de compatibilidade
def test_compatibility():
    """
    Testa se a função melhorada é compatível com o uso no app.py
    """
    
    print("TESTE DE COMPATIBILIDADE COM APP.PY")
    print("=" * 40)
    
    # Testar casos que app.py usaria
    test_cases = [
        "Cidade Industrial, Curitiba",  # Deve ser corrigido para SEHIS
        "Centro, Curitiba",            # Deve permanecer ZC
        "Batel, Curitiba"              # Deve permanecer ZUM-1
    ]
    
    for endereco in test_cases:
        print(f"\nTeste: {endereco}")
        try:
            result = detect_zone_professional(endereco)
            print(f"  Zona: {result.zona}")
            print(f"  Confianca: {result.confidence}")
            print(f"  Fonte: {result.source}")
            
            # Verificar se tem correção SEHIS
            if hasattr(result, 'correction_reason'):
                print(f"  Correcao SEHIS: {result.original_detection} -> {result.zona}")
            
        except Exception as e:
            print(f"  ERRO: {e}")

if __name__ == "__main__":
    test_compatibility()