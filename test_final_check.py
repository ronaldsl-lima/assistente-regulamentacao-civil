#!/usr/bin/env python3
"""
Teste final para verificar se todas as zonas principais estão funcionando
"""

from fallback_retriever import FallbackDocumentRetriever

def test_principais_zonas():
    retriever = FallbackDocumentRetriever()
    
    zonas_teste = [
        "ZR-4",     # ZONA RESIDENCIAL 4 - LINHA VERDE
        "ZCC",      # Centro Cívico  
        "ZR2",      # Zona residencial 2
        "ZR-1",     # Primeira zona residencial
        "ZC",       # Zona Central
        "ZUM-1",    # Zona de Uso Misto
    ]
    
    print(f"Total de documentos: {len(retriever.documents)}")
    
    for zona in zonas_teste:
        result = retriever.get(where={'zona_especifica': zona}, limit=3)
        count = len(result['documents'])
        print(f"Zona {zona}: {count} documentos")
        
        if count > 0 and result['metadatas']:
            nome_completo = result['metadatas'][0].get('zona_nome_completo', 'N/A')
            print(f"  Nome completo: {nome_completo}")
    
    # Verificar se ZR-4 tem o documento da LINHA VERDE
    result_zr4 = retriever.get(where={'zona_especifica': 'ZR-4'}, limit=10)
    for metadata in result_zr4.get('metadatas', []):
        nome_completo = metadata.get('zona_nome_completo', '')
        if 'LINHA VERDE' in nome_completo:
            print(f"\n✓ Encontrado: {nome_completo}")
            break
    else:
        print(f"\n✗ LINHA VERDE não encontrada nos documentos ZR-4")
        
    return True

if __name__ == "__main__":
    test_principais_zonas()