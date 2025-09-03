#!/usr/bin/env python3
"""
Teste específico para a zona ZONA RESIDENCIAL 4 - LINHA VERDE
"""

from fallback_retriever import FallbackDocumentRetriever

def test_zona_linha_verde():
    print("Testando busca por 'ZONA RESIDENCIAL 4 - LINHA VERDE'...")
    
    retriever = FallbackDocumentRetriever()
    
    if not retriever.available:
        print("Retriever não disponível")
        return
    
    print(f"Total de documentos carregados: {len(retriever.documents)}")
    
    # Teste 1: Busca exata pelo nome
    result1 = retriever.get(where={'zona_nome_completo': 'ZONA RESIDENCIAL 4 - LINHA VERDE'}, limit=5)
    print(f"\nBusca por nome completo: {len(result1['documents'])} documentos")
    
    # Teste 2: Busca pela zona normalizada ZR-4
    result2 = retriever.get(where={'zona_especifica': 'ZR-4'}, limit=5)
    print(f"Busca por zona normalizada ZR-4: {len(result2['documents'])} documentos")
    
    # Teste 3: Busca por similaridade
    docs = retriever.similarity_search("zona residencial 4 linha verde", k=3)
    print(f"Busca por similaridade: {len(docs)} documentos")
    
    # Mostrar exemplo de documento encontrado
    if result2['documents']:
        print(f"\nExemplo de documento ZR-4:")
        print(f"Conteúdo: {result2['documents'][0][:200]}...")
        print(f"Metadata: {result2['metadatas'][0]}")
    
    # Mostrar todas as zonas disponíveis que começam com ZR-4
    print(f"\nZonas disponíveis relacionadas a ZR-4:")
    zonas_zr4 = set()
    for doc in retriever.documents:
        zona = doc.metadata.get('zona_especifica', '')
        nome_completo = doc.metadata.get('zona_nome_completo', '')
        if 'ZR-4' in zona or 'LINHA VERDE' in nome_completo:
            zonas_zr4.add(f"{zona} ({nome_completo})")
    
    for zona in sorted(zonas_zr4):
        print(f"  - {zona}")
    
    return len(result2['documents']) > 0

if __name__ == "__main__":
    sucesso = test_zona_linha_verde()
    if sucesso:
        print("\n✅ ZONA RESIDENCIAL 4 - LINHA VERDE encontrada com sucesso!")
    else:
        print("\n❌ Zona não encontrada")