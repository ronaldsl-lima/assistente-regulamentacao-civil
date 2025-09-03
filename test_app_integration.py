#!/usr/bin/env python3
"""
Test the app integration with fallback system
"""

import sys
sys.path.append('.')

from chroma_wrapper import Chroma
from app_backup import resource_manager, AnalysisEngine

def test_app_integration():
    print("Testing app integration with fallback system...")
    
    # Load resources as the app would
    resources = resource_manager.get_resources("curitiba")
    
    print(f"Resources loaded: {list(resources.keys())}")
    
    vectorstore = resources.get("vectorstore")
    if vectorstore:
        print(f"Vectorstore available: {getattr(vectorstore, 'available', 'unknown')}")
        print(f"Has fallback retriever: {hasattr(vectorstore, 'fallback_retriever')}")
        
        if hasattr(vectorstore, 'fallback_retriever'):
            print(f"Fallback retriever available: {getattr(vectorstore.fallback_retriever, 'available', 'unknown')}")
    
    # Test analysis engine
    engine = AnalysisEngine()
    
    try:
        print("\n=== Testing analysis for ZR2 ===")
        result_zr2 = engine.run_analysis(
            endereco="Bairro Residencial, Curitiba-PR",
            cidade="curitiba",
            memorial="Teste de integração ZR2",
            zona_manual="ZR2",
            usar_zona_manual=True
        )
        print("Analysis ZR2 successful!")
        print(f"Result type: {type(result_zr2)}")
        if isinstance(result_zr2, dict) and 'relatorio' in result_zr2:
            print(f"Report ZR2 preview: {result_zr2['relatorio'][:200]}...")
        
        print("\n=== Testing analysis for ZCC.4 ===")
        result_zcc = engine.run_analysis(
            endereco="Centro Cívico, Curitiba-PR",
            cidade="curitiba",
            memorial="Teste de integração ZCC.4",
            zona_manual="ZCC.4",
            usar_zona_manual=True
        )
        print("Analysis ZCC.4 successful!")
        print(f"Result type: {type(result_zcc)}")
        if isinstance(result_zcc, dict) and 'relatorio' in result_zcc:
            print(f"Report ZCC.4 preview: {result_zcc['relatorio'][:200]}...")
    except Exception as e:
        print(f"Analysis failed: {e}")
        # This is expected - let's see the error message
        if "Zonas disponíveis no sistema" in str(e):
            print("Good! The new error handling is working")
        else:
            print("Error doesn't match expected fallback behavior")

if __name__ == "__main__":
    test_app_integration()