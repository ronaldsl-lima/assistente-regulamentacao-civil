#!/usr/bin/env python3
"""
Test the fallback system integration
"""

from chroma_wrapper import ChromaWrapper
from fallback_retriever import FallbackDocumentRetriever

def test_chroma_wrapper():
    print("Testing ChromaWrapper initialization...")
    
    # This should trigger fallback mode since ChromaDB likely won't work
    wrapper = ChromaWrapper(persist_directory="./db", collection_name="curitiba")
    
    print(f"Wrapper available: {wrapper.available}")
    print(f"Has fallback retriever: {hasattr(wrapper, 'fallback_retriever')}")
    
    if hasattr(wrapper, 'fallback_retriever'):
        print(f"Fallback available: {wrapper.fallback_retriever.available}")
    
    # Test document retrieval
    try:
        collection = wrapper.get_or_create_collection("curitiba")
        if collection:
            print("Collection created/retrieved successfully")
            
            # Test filtering by zone
            result = collection.get(where={'zona_especifica': 'ZCC.4'}, limit=5)
            print(f"Found {len(result['documents'])} documents for ZCC.4")
            
            if result['documents']:
                print("Sample document content:")
                print(result['documents'][0][:200] + "...")
        else:
            print("Failed to create collection")
    except Exception as e:
        print(f"Error testing collection: {e}")
    
    # Test retriever interface
    try:
        retriever = wrapper.as_retriever()
        docs = retriever.get_relevant_documents("coeficiente aproveitamento taxa ocupação")
        print(f"Retriever found {len(docs)} relevant documents")
    except Exception as e:
        print(f"Error testing retriever: {e}")

if __name__ == "__main__":
    test_chroma_wrapper()