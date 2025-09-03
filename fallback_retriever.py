"""
Fallback document retriever que usa dados JSON quando ChromaDB não está disponível
"""

import os
import json
import pickle
import logging
from typing import List, Dict, Any
from pathlib import Path
from langchain.schema import Document
import numpy as np
from langchain_community.embeddings import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)

class FallbackDocumentRetriever:
    """Retriever que funciona sem ChromaDB usando arquivos locais"""
    
    def __init__(self, fallback_dir: str = "db_fallback"):
        self.fallback_dir = Path(fallback_dir)
        self.documents = []
        self.embeddings_model = None
        self.document_embeddings = None
        self.available = False
        
        self._load_data()
    
    def _load_data(self):
        """Load documents and embeddings from fallback storage"""
        try:
            # Try to load from pickle first (faster)
            pkl_path = self.fallback_dir / "documents.pkl"
            if pkl_path.exists():
                with open(pkl_path, 'rb') as f:
                    self.documents = pickle.load(f)
                logger.info(f"Loaded {len(self.documents)} documents from pickle")
                self.available = True
                return
            
            # Fallback to JSON
            json_path = self.fallback_dir / "documents.json"
            if json_path.exists():
                with open(json_path, 'r', encoding='utf-8') as f:
                    doc_data = json.load(f)
                
                # Convert back to Document objects
                self.documents = [
                    Document(page_content=item['content'], metadata=item['metadata'])
                    for item in doc_data
                ]
                logger.info(f"Loaded {len(self.documents)} documents from JSON")
                self.available = True
                return
                
            logger.warning(f"No fallback data found in {self.fallback_dir}")
            
        except Exception as e:
            logger.error(f"Error loading fallback data: {e}")
    
    def get(self, where: Dict[str, Any] = None, limit: int = 5) -> Dict[str, List]:
        """Simulate ChromaDB get method with filtering"""
        if not self.available or not self.documents:
            return {'documents': [], 'metadatas': []}
        
        filtered_docs = []
        
        # Simple filtering based on where clause
        for doc in self.documents:
            if where is None:
                filtered_docs.append(doc)
            else:
                match = True
                for key, value in where.items():
                    if key in doc.metadata:
                        if isinstance(value, dict) and '$in' in value:
                            # Handle $in operator
                            if doc.metadata[key] not in value['$in']:
                                match = False
                                break
                        elif doc.metadata[key] != value:
                            match = False
                            break
                    else:
                        match = False
                        break
                
                if match:
                    filtered_docs.append(doc)
            
            if len(filtered_docs) >= limit:
                break
        
        return {
            'documents': [doc.page_content for doc in filtered_docs],
            'metadatas': [doc.metadata for doc in filtered_docs]
        }
    
    def similarity_search(self, query: str, k: int = 4) -> List[Document]:
        """Basic similarity search using keyword matching"""
        if not self.available or not self.documents:
            return []
        
        # Simple keyword-based similarity
        query_words = set(query.lower().split())
        scored_docs = []
        
        for doc in self.documents:
            doc_words = set(doc.page_content.lower().split())
            # Simple Jaccard similarity
            intersection = len(query_words & doc_words)
            union = len(query_words | doc_words)
            score = intersection / union if union > 0 else 0
            
            # Boost score if query terms appear in metadata
            for key, value in doc.metadata.items():
                if isinstance(value, str) and any(word in value.lower() for word in query_words):
                    score += 0.1
            
            scored_docs.append((score, doc))
        
        # Sort by score and return top k
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        return [doc for score, doc in scored_docs[:k]]
    
    def as_retriever(self, search_type="similarity", search_kwargs=None):
        """Return a retriever interface"""
        if search_kwargs is None:
            search_kwargs = {}
        
        class SimpleRetriever:
            def __init__(self, retriever_instance):
                self.retriever = retriever_instance
            
            def get_relevant_documents(self, query: str) -> List[Document]:
                k = search_kwargs.get('k', 4)
                return self.retriever.similarity_search(query, k=k)
        
        return SimpleRetriever(self)


def create_sample_documents():
    """Create sample documents for multiple zones for testing"""
    
    sample_docs = [
        # ZCC.4 Documents
        Document(
            page_content="""
            ZONA CENTRO CÍVICO (ZCC.4)
            
            PARÂMETROS URBANÍSTICOS:
            - Taxa de Ocupação: máximo 70%
            - Coeficiente de Aproveitamento: máximo 4,0
            - Altura da Edificação: máximo 12 pavimentos ou 36 metros
            - Recuo Frontal: mínimo 5,0 metros
            - Recuos Laterais: mínimo 3,0 metros
            - Recuo de Fundos: mínimo 3,0 metros  
            - Área Permeável: mínimo 15%
            """,
            metadata={
                'source': 'lei_municipal',
                'zona_especifica': 'ZCC.4',
                'zonas_mencionadas': ['ZCC', 'ZCC.4'],
                'tipo_conteudo': 'parametros_urbanisticos',
                'contem_tabela': True
            }
        ),
        Document(
            page_content="""
            A Zona Centro Cívico subdivide-se em ZCC.1, ZCC.2, ZCC.3 e ZCC.4.
            
            Na ZCC.4 são permitidos os seguintes usos:
            - Residencial multifamiliar
            - Comercial de grande porte
            - Serviços especializados
            - Institucionais
            
            As edificações na ZCC.4 devem atender aos parâmetros específicos
            estabelecidos na tabela de parâmetros urbanísticos.
            """,
            metadata={
                'source': 'lei_municipal',
                'zona_especifica': 'ZCC.4',
                'zonas_mencionadas': ['ZCC', 'ZCC.4', 'ZCC.1', 'ZCC.2', 'ZCC.3'],
                'tipo_conteudo': 'usos_permitidos',
                'contem_tabela': False
            }
        ),
        # ZR2 Documents
        Document(
            page_content="""
            ZONA RESIDENCIAL 2 (ZR2)
            
            PARÂMETROS URBANÍSTICOS:
            - Taxa de Ocupação: máximo 50%
            - Coeficiente de Aproveitamento: máximo 1,4
            - Altura da Edificação: máximo 2 pavimentos ou 8,5 metros
            - Recuo Frontal: mínimo 4,0 metros
            - Recuos Laterais: mínimo 1,5 metros quando exigido
            - Recuo de Fundos: mínimo 3,0 metros
            - Área Permeável: mínimo 20%
            """,
            metadata={
                'source': 'lei_municipal',
                'zona_especifica': 'ZR2',
                'zonas_mencionadas': ['ZR', 'ZR2'],
                'tipo_conteudo': 'parametros_urbanisticos',
                'contem_tabela': True
            }
        ),
        Document(
            page_content="""
            ZONA RESIDENCIAL 2 (ZR2) - Usos Permitidos
            
            São permitidos na ZR2:
            - Residencial unifamiliar
            - Residencial multifamiliar (máximo 4 unidades)
            - Comércio de proximidade (até 250m²)
            - Serviços de proximidade
            - Institucional de vizinhança
            
            Características: Zona destinada predominantemente à habitação,
            com baixa densidade construtiva e ocupação.
            """,
            metadata={
                'source': 'lei_municipal',
                'zona_especifica': 'ZR2',
                'zonas_mencionadas': ['ZR', 'ZR2'],
                'tipo_conteudo': 'usos_permitidos',
                'contem_tabela': False
            }
        )
    ]
    
    # Save sample documents
    os.makedirs("db_fallback", exist_ok=True)
    
    with open("db_fallback/documents.pkl", 'wb') as f:
        pickle.dump(sample_docs, f)
    
    doc_data = [
        {'content': doc.page_content, 'metadata': doc.metadata}
        for doc in sample_docs
    ]
    
    with open("db_fallback/documents.json", 'w', encoding='utf-8') as f:
        json.dump(doc_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Created sample documents for testing")

if __name__ == "__main__":
    # Create sample documents for immediate testing
    create_sample_documents()
    
    # Test the retriever
    retriever = FallbackDocumentRetriever()
    
    if retriever.available:
        # Test filtering
        result = retriever.get(where={'zona_especifica': 'ZCC.4'}, limit=5)
        print(f"Found {len(result['documents'])} documents for ZCC.4")
        
        # Test similarity search
        docs = retriever.similarity_search("coeficiente aproveitamento taxa ocupação", k=2)
        print(f"Similarity search found {len(docs)} documents")
        
    else:
        print("Fallback retriever not available")