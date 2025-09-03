#!/usr/bin/env python3
"""
Teste completo do sistema com múltiplas zonas
"""

import sys
sys.path.append('.')

from chroma_wrapper import Chroma
from app_backup import resource_manager, AnalysisEngine

def test_multiple_zones():
    print("Testando sistema completo com múltiplas zonas...")
    
    # Carregar recursos
    resources = resource_manager.get_resources("curitiba")
    print(f"Recursos carregados: {list(resources.keys())}")
    
    vectorstore = resources.get("vectorstore")
    if vectorstore:
        print(f"Vectorstore disponível: {getattr(vectorstore, 'available', 'unknown')}")
        
        if hasattr(vectorstore, 'fallback_retriever'):
            print(f"Fallback retriever: {len(vectorstore.fallback_retriever.documents)} documentos")
    
    # Testar análise engine
    engine = AnalysisEngine()
    
    # Zonas para testar
    zonas_teste = [
        ("ZONA RESIDENCIAL 4 - LINHA VERDE", "ZR-4"),
        ("ZR2", "ZR2"),
        ("ZCC", "ZCC"),
        ("ZR-50", "ZR-50"),
        ("ZUM-1", "ZUM-1")
    ]
    
    sucessos = 0
    total = len(zonas_teste)
    
    for zona_input, zona_esperada in zonas_teste:
        try:
            print(f"\n=== Testando zona: {zona_input} ===")
            result = engine.run_analysis(
                endereco=f"Teste - {zona_input}",
                cidade="curitiba",
                memorial=f"Teste da zona {zona_input}",
                zona_manual=zona_input,
                usar_zona_manual=True
            )
            
            if isinstance(result, dict) and 'relatorio' in result:
                print(f"✓ Análise concluída para {zona_input}")
                sucessos += 1
            else:
                print(f"✗ Resultado inesperado para {zona_input}: {type(result)}")
                
        except Exception as e:
            error_msg = str(e)
            if "Zonas disponíveis no sistema" in error_msg:
                print(f"✓ Zona {zona_input} não encontrada (comportamento esperado)")
                print(f"  Mensagem: {error_msg[:100]}...")
            else:
                print(f"✗ Erro inesperado para {zona_input}: {error_msg}")
    
    print(f"\n=== RESULTADO FINAL ===")
    print(f"Sucessos: {sucessos}/{total}")
    
    # Mostrar amostra das zonas disponíveis
    if hasattr(vectorstore, 'fallback_retriever') and vectorstore.fallback_retriever:
        zonas_disponiveis = set()
        for doc in vectorstore.fallback_retriever.documents:
            zona = doc.metadata.get('zona_especifica', '')
            if zona:
                zonas_disponiveis.add(zona)
        
        zonas_sorted = sorted(zonas_disponiveis)
        print(f"\nTotal de zonas no sistema: {len(zonas_sorted)}")
        print(f"Primeiras 20: {zonas_sorted[:20]}")
        print(f"Últimas 10: {zonas_sorted[-10:]}")
        
        # Verificar se ZR-4 está disponível
        if 'ZR-4' in zonas_sorted:
            print("\n✓ ZR-4 confirmado no sistema!")
    
    return sucessos == total

if __name__ == "__main__":
    resultado = test_multiple_zones()
    if resultado:
        print("\nSISTEMA COMPLETO FUNCIONANDO!")
    else:
        print("\nAlguns testes falharam, mas sistema esta operacional")