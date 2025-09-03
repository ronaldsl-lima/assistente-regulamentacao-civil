"""
Ingestão simplificada para popular base de dados
Funciona mesmo quando ChromaDB tem problemas
"""

import os
import json
import pickle
import logging
from pathlib import Path
from typing import List, Dict
import pdfplumber
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_community.embeddings import HuggingFaceEmbeddings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_text_from_pdf(pdf_path: str) -> List[str]:
    """Extract text from PDF"""
    texts = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text and len(text.strip()) > 50:  # Skip empty pages
                    texts.append(text)
                    
        logger.info(f"Extracted text from {len(texts)} pages in {pdf_path}")
        return texts
        
    except Exception as e:
        logger.error(f"Error extracting from {pdf_path}: {e}")
        return []

def create_documents_from_texts(texts: List[str], source: str) -> List[Document]:
    """Create documents with metadata"""
    documents = []
    
    # Text splitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=200,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    for i, text in enumerate(texts):
        # Split into chunks
        chunks = splitter.split_text(text)
        
        for j, chunk in enumerate(chunks):
            if len(chunk.strip()) > 100:  # Skip very small chunks
                # Basic zone detection
                zones = []
                zone_patterns = [
                    'ZCC', 'ZR', 'ZS', 'ZUM', 'ECO', 'ZH', 'EAC', 'EACB', 'EACF', 
                    'EMF', 'EMLV', 'EE', 'ENC', 'SEHIS', 'SEPE', 'ZE', 'ZI', 'ZM', 
                    'ZT', 'ZPS', 'ZROC', 'ZROI', 'ZC', 'ZCSF', 'ZCUM', 'ZSF', 'ZSM', 'ZUMVP'
                ]
                
                for zone in zone_patterns:
                    if zone in chunk.upper():
                        zones.append(zone)
                
                # Create document
                doc = Document(
                    page_content=chunk,
                    metadata={
                        'source': source,
                        'page': i,
                        'chunk': j,
                        'zona_especifica': zones[0] if zones else '',
                        'zonas_mencionadas': zones,
                        'tipo_conteudo': 'parametros_urbanisticos' if any(
                            word in chunk.lower() 
                            for word in ['coeficiente', 'taxa', 'altura', 'recuo', 'afastamento']
                        ) else 'geral',
                        'contem_tabela': 'tabela' in chunk.lower() or '|' in chunk
                    }
                )
                documents.append(doc)
    
    return documents

def save_documents_to_json(documents: List[Document], output_dir: str):
    """Save documents as JSON fallback"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Convert documents to serializable format
    doc_data = []
    for doc in documents:
        doc_data.append({
            'content': doc.page_content,
            'metadata': doc.metadata
        })
    
    # Save as JSON
    with open(os.path.join(output_dir, 'documents.json'), 'w', encoding='utf-8') as f:
        json.dump(doc_data, f, ensure_ascii=False, indent=2)
    
    # Save as pickle for faster loading
    with open(os.path.join(output_dir, 'documents.pkl'), 'wb') as f:
        pickle.dump(documents, f)
    
    logger.info(f"Saved {len(documents)} documents to {output_dir}")

def create_embeddings_and_index(documents: List[Document], output_dir: str):
    """Create embeddings and search index"""
    try:
        # Load embeddings model
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        
        # Create embeddings for all documents
        texts = [doc.page_content for doc in documents]
        doc_embeddings = embeddings.embed_documents(texts)
        
        # Save embeddings and metadata
        index_data = {
            'embeddings': doc_embeddings,
            'documents': documents,
            'metadata': [doc.metadata for doc in documents]
        }
        
        with open(os.path.join(output_dir, 'embeddings_index.pkl'), 'wb') as f:
            pickle.dump(index_data, f)
            
        logger.info(f"Created embeddings index with {len(documents)} documents")
        
    except Exception as e:
        logger.error(f"Error creating embeddings: {e}")

def main():
    """Main ingestion process"""
    
    # Paths
    data_dir = Path("dados/curitiba")
    output_dir = Path("db_fallback")
    
    if not data_dir.exists():
        logger.error(f"Data directory {data_dir} not found")
        return
    
    logger.info("Starting simplified document ingestion...")
    
    # Find PDF files
    pdf_files = list(data_dir.glob("*.pdf"))
    if not pdf_files:
        logger.error("No PDF files found")
        return
    
    logger.info(f"Found {len(pdf_files)} PDF files")
    
    all_documents = []
    
    # Process each PDF
    for pdf_file in pdf_files:
        logger.info(f"Processing {pdf_file.name}...")
        
        # Extract text
        texts = extract_text_from_pdf(str(pdf_file))
        
        if texts:
            # Create documents
            documents = create_documents_from_texts(texts, str(pdf_file))
            all_documents.extend(documents)
            logger.info(f"Created {len(documents)} documents from {pdf_file.name}")
    
    if all_documents:
        logger.info(f"Total documents created: {len(all_documents)}")
        
        # Save documents
        save_documents_to_json(all_documents, str(output_dir))
        
        # Create embeddings index
        create_embeddings_and_index(all_documents, str(output_dir))
        
        logger.info("✅ Ingestion completed successfully!")
        logger.info(f"📁 Data saved to: {output_dir}")
        logger.info("🚀 You can now use the system for analysis!")
        
    else:
        logger.error("❌ No documents were created")

if __name__ == "__main__":
    main()