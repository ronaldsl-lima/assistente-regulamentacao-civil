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
        print("\nTesting analysis for ZCC.4...")
        result = engine.run_analysis(
            endereco="Centro Cívico, Curitiba-PR",
            cidade="curitiba",
            memorial="Teste de integração",
            zona_manual="ZCC.4",
            usar_zona_manual=True
        )
        print("Analysis successful!")
        print(f"Result type: {type(result)}")
        if isinstance(result, dict) and 'relatorio' in result:
            print(f"Report preview: {result['relatorio'][:200]}...")
    except Exception as e:
        print(f"Analysis failed: {e}")
        # This is expected - let's see the error message
        if "Zonas disponíveis no sistema" in str(e):
            print("Good! The new error handling is working")
        else:
            print("Error doesn't match expected fallback behavior")

if __name__ == "__main__":
    test_app_integration()