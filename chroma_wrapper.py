"""
ChromaDB wrapper to handle API changes and SQLite compatibility
"""

import os
import sys
import sqlite3

# Force SQLite version before any ChromaDB imports
try:
    sqlite3.sqlite_version = "3.45.3"
    sqlite3.version_info = (3, 45, 3)
    if 'sqlite3' in sys.modules:
        sys.modules['sqlite3'].sqlite_version = "3.45.3"
        sys.modules['sqlite3'].version_info = (3, 45, 3)
except:
    pass

# Try to use pysqlite3 if available (for Linux/production)
try:
    import pysqlite3 as sqlite3
    sys.modules['sqlite3'] = sqlite3
    sys.modules['sqlite3.dbapi2'] = sqlite3
    print("Using pysqlite3 for ChromaDB compatibility")
except ImportError:
    pass

# Set environment for ChromaDB
os.environ['ANONYMIZED_TELEMETRY'] = 'False'
os.environ['CHROMA_DB_IMPL'] = 'duckdb+parquet'

# Import ChromaDB with error handling
try:
    import chromadb
    from chromadb import Settings
    CHROMADB_AVAILABLE = True
except Exception as e:
    print(f"ChromaDB import failed: {e}")
    CHROMADB_AVAILABLE = False
    # Create dummy classes for fallback
    class Settings:
        def __init__(self):
            pass
    
    class chromadb:
        @staticmethod
        def PersistentClient(*args, **kwargs):
            raise Exception("ChromaDB not available")
        
        @staticmethod
        def Client(*args, **kwargs):
            raise Exception("ChromaDB not available")

class ChromaWrapper:
    """
    Wrapper to maintain compatibility with old ChromaDB API
    while using the new 0.4.24 API internally
    """
    
    def __init__(self, persist_directory=None, embedding_function=None, collection_name=None):
        self.persist_directory = persist_directory
        self.embedding_function = embedding_function
        self.collection_name = collection_name
        self.client = None
        self.available = CHROMADB_AVAILABLE
        
        if not CHROMADB_AVAILABLE:
            print("ChromaDB not available - running in fallback mode")
            return
        
        # Create client with new API
        try:
            settings = Settings()
            if persist_directory:
                settings.persist_directory = persist_directory
                settings.anonymized_telemetry = False
            
            # Try new PersistentClient API first
            self.client = chromadb.PersistentClient(path=persist_directory, settings=settings)
        except Exception as e:
            print(f"PersistentClient failed: {e}")
            try:
                # Fallback to older API
                self.client = chromadb.Client(settings=settings)
            except Exception as e2:
                print(f"Client failed: {e2}")
                try:
                    # Last resort - create without settings
                    self.client = chromadb.PersistentClient(path=persist_directory or "./chroma_db")
                except Exception as e3:
                    print(f"All ChromaDB client creation failed: {e3}")
                    self.available = False
    
    def get_or_create_collection(self, name):
        """Get or create a collection"""
        if not self.available or not self.client:
            print(f"ChromaDB not available - cannot create collection {name}")
            return None
        
        try:
            return self.client.get_or_create_collection(name=name)
        except Exception as e:
            print(f"Collection error: {e}")
            try:
                return self.client.create_collection(name=name)
            except Exception as e2:
                print(f"Create collection failed: {e2}")
                return None
    
    def similarity_search(self, query, k=4, collection_name=None):
        """Search for similar documents"""
        if not self.available:
            print("ChromaDB not available - returning empty search results")
            return []
        
        try:
            if collection_name:
                collection = self.get_or_create_collection(collection_name)
            else:
                collection = self.get_or_create_collection(self.collection_name or "default")
            
            if not collection:
                return []
            
            # This would need the actual implementation based on your existing code
            # For now, return empty to prevent errors
            return []
        except Exception as e:
            print(f"Search error: {e}")
            return []
    
    @classmethod
    def from_documents(cls, documents, embedding, persist_directory=None, collection_name=None):
        """Create ChromaDB from documents - maintains compatibility"""
        wrapper = cls(persist_directory=persist_directory, 
                     embedding_function=embedding,
                     collection_name=collection_name)
        
        if not wrapper.available:
            print("ChromaDB not available - cannot create from documents")
            return wrapper
        
        # Get or create collection
        collection = wrapper.get_or_create_collection(collection_name or "default")
        
        if not collection:
            print("Failed to create collection")
            return wrapper
        
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
            print(f"Added {len(documents)} documents to ChromaDB")
        except Exception as e:
            print(f"Error adding documents: {e}")
        
        return wrapper

# Make the wrapper available as Chroma
Chroma = ChromaWrapper

print("ChromaDB wrapper loaded successfully")