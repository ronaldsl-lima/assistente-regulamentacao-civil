# chroma_wrapper.py - Wrapper simples para ChromaDB
import os
import sys

# Import ChromaDB
try:
    from langchain_community.vectorstores import Chroma as LangChainChroma
    
    class Chroma(LangChainChroma):
        """Wrapper para ChromaDB"""
        pass
        
except ImportError:
    print("Aviso: ChromaDB não está disponível. Funcionalidade de busca em documentos pode estar limitada.")
    
    class Chroma:
        """Fallback quando ChromaDB não está disponível"""
        def __init__(self, *args, **kwargs):
            self.available = False
            
        def similarity_search(self, *args, **kwargs):
            return []