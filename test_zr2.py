#!/usr/bin/env python3
"""
Test ZR2 zone search to ensure correct documents are returned
"""

from fallback_retriever import FallbackDocumentRetriever

def test_zr2_search():
    print("Testing ZR2 zone search...")
    
    retriever = FallbackDocumentRetriever()
    
    if not retriever.available:
        print("Retriever not available")
        return
    
    print(f"Total documents loaded: {len(retriever.documents)}")
    
    # Test filtering by ZR2 zone
    result = retriever.get(where={'zona_especifica': 'ZR2'}, limit=5)
    print(f"Found {len(result['documents'])} documents for ZR2")
    
    if result['documents']:
        print("ZR2 documents found:")
        for i, doc in enumerate(result['documents']):
            print(f"\nDocument {i+1}:")
            print(f"Content preview: {doc[:100]}...")
            print(f"Metadata: {result['metadatas'][i]}")
    
    # Test filtering by ZCC.4 zone (should still work)
    result_zcc = retriever.get(where={'zona_especifica': 'ZCC.4'}, limit=5)
    print(f"\nFound {len(result_zcc['documents'])} documents for ZCC.4")
    
    # Show all available zones
    print("\nAll available zones in the system:")
    zones = set()
    for doc in retriever.documents:
        if 'zona_especifica' in doc.metadata:
            zones.add(doc.metadata['zona_especifica'])
    print(f"Available zones: {sorted(zones)}")

if __name__ == "__main__":
    test_zr2_search()