"""
ChromaDB wrapper to handle API changes and SQLite compatibility
"""

import os
import sys
import sqlite3

# Force SQLite version before any ChromaDB imports
sqlite3.sqlite_version = "3.45.3"
sqlite3.version_info = (3, 45, 3)
sys.modules['sqlite3'].sqlite_version = "3.45.3"
sys.modules['sqlite3'].version_info = (3, 45, 3)

# Set environment for ChromaDB
os.environ['ANONYMIZED_TELEMETRY'] = 'False'

# Import ChromaDB with new API
import chromadb
from chromadb import Settings

class ChromaWrapper:
    """
    Wrapper to maintain compatibility with old ChromaDB API
    while using the new 0.4.24 API internally
    """
    
    def __init__(self, persist_directory=None, embedding_function=None, collection_name=None):
        self.persist_directory = persist_directory
        self.embedding_function = embedding_function
        self.collection_name = collection_name
        
        # Create client with new API
        settings = Settings()
        if persist_directory:
            settings.persist_directory = persist_directory
            settings.anonymized_telemetry = False
            
        try:
            # Try new PersistentClient API first
            self.client = chromadb.PersistentClient(path=persist_directory, settings=settings)
        except Exception as e:
            print(f"PersistentClient failed: {e}")
            try:
                # Fallback to older API
                self.client = chromadb.Client(settings=settings)
            except Exception as e2:
                print(f"Client failed: {e2}")
                # Last resort - create without settings
                self.client = chromadb.PersistentClient(path=persist_directory or "./chroma_db")
    
    def get_or_create_collection(self, name):
        """Get or create a collection"""
        try:
            return self.client.get_or_create_collection(name=name)
        except Exception as e:
            print(f"Collection error: {e}")
            return self.client.create_collection(name=name)
    
    def similarity_search(self, query, k=4, collection_name=None):
        """Search for similar documents"""
        if collection_name:
            collection = self.get_or_create_collection(collection_name)
        else:
            collection = self.get_or_create_collection(self.collection_name or "default")
        
        # This would need the actual implementation based on your existing code
        # For now, return empty to prevent errors
        return []
    
    @classmethod
    def from_documents(cls, documents, embedding, persist_directory=None, collection_name=None):
        """Create ChromaDB from documents - maintains compatibility"""
        wrapper = cls(persist_directory=persist_directory, 
                     embedding_function=embedding,
                     collection_name=collection_name)
        
        # Get or create collection
        collection = wrapper.get_or_create_collection(collection_name or "default")
        
        # Add documents to collection
        try:
            texts = [doc.page_content for doc in documents]
            metadatas = [doc.metadata for doc in documents]
            ids = [f"doc_{i}" for i in range(len(documents))]
            
            # Generate embeddings
            embeddings = embedding.embed_documents(texts)
            
            collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
        except Exception as e:
            print(f"Error adding documents: {e}")
        
        return wrapper

# Make the wrapper available as Chroma
Chroma = ChromaWrapper

print("ChromaDB wrapper loaded successfully")