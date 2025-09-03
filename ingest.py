# ingest_melhorado.py - Versão Otimizada 2.0

# Fix SQLite compatibility for ChromaDB - MUST be first
import sqlite_fix

import os, argparse, re, json, logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing as mp

import pdfplumber
import pandas as pd
import spacy
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.docstore.document import Document

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent

@dataclass
class IngestConfig:
    PASTA_DADOS_RAIZ: Path = PROJECT_ROOT / "dados"
    PASTA_BD: Path = PROJECT_ROOT / "db"
    MODELO_EMBEDDING: str = "sentence-transformers/all-MiniLM-L6-v2"
    NOME_BASE_COLECAO: str = "regulamentacao"
    CHUNK_SIZE: int = 1500
    CHUNK_OVERLAP: int = 300
    MAX_WORKERS: int = min(4, mp.cpu_count())
    BATCH_SIZE: int = 50

CONFIG = IngestConfig()

class AdvancedTableDetector:
    """Detector avançado de tabelas usando ML e heurísticas"""
    
    def __init__(self):
        # Carrega modelo spaCy se disponível
        try:
            self.nlp = spacy.load("pt_core_news_sm")
        except OSError:
            logger.warning("Modelo spaCy não encontrado. Usando fallback.")
            self.nlp = None
        
        # Padrões otimizados
        self.zone_pattern = re.compile(r'\b(ZR-?\d+[A-Z]*|ZS-?\d+|ZC|ZT[A-Z]*|ZONA\s+[A-Z0-9-]+)\b', re.IGNORECASE)
        self.param_pattern = re.compile(r'\b(coeficiente|taxa|ocupação|aproveitamento|afastamento|gabarito|altura|recuo)\b', re.IGNORECASE)
        self.numeric_pattern = re.compile(r'\d+[,.]?\d*\s*[%m]?')
        self.table_structure = re.compile(r'(\|.*\||\+[-+]+\+|─{3,})')
    
    def detect_parameters_table(self, text: str, raw_tables: List) -> Tuple[bool, float]:
        """Detecta tabelas de parâmetros com score de confiança"""
        score = 0.0
        
        # Análise textual
        text_lower = text.lower()
        
        # Palavras-chave críticas (peso alto)
        critical_keywords = ['coeficiente de aproveitamento', 'taxa de ocupação', 'parâmetros urbanísticos']
        score += sum(3.0 for kw in critical_keywords if kw in text_lower)
        
        # Palavras-chave importantes (peso médio)
        important_keywords = ['afastamento', 'gabarito', 'altura', 'recuo', 'zoneamento']
        score += sum(2.0 for kw in important_keywords if kw in text_lower)
        
        # Estrutura de tabela
        if self.table_structure.search(text):
            score += 2.5
        
        # Tabelas extraídas
        if raw_tables:
            score += len(raw_tables) * 1.5
        
        # Zonas identificadas
        zones = self.zone_pattern.findall(text)
        score += len(set(zones)) * 1.0
        
        # Valores numéricos
        numbers = self.numeric_pattern.findall(text)
        if len(numbers) >= 5:
            score += 2.0
        elif len(numbers) >= 3:
            score += 1.0
        
        # Análise NLP se disponível
        if self.nlp:
            score += self._nlp_analysis(text)
        
        # Normalização do score (0-10)
        normalized_score = min(score / 2.0, 10.0)
        is_parameter_table = normalized_score >= 4.0
        
        return is_parameter_table, normalized_score
    
    def _nlp_analysis(self, text: str) -> float:
        """Análise NLP para identificar contexto jurídico/urbanístico"""
        try:
            doc = self.nlp(text[:1000])  # Limita para performance
            
            # Entidades relevantes
            relevant_entities = ['ORG', 'LAW', 'MISC']
            entity_score = sum(0.5 for ent in doc.ents if ent.label_ in relevant_entities)
            
            # Termos técnicos
            technical_terms = ['lei', 'artigo', 'parágrafo', 'decreto', 'norma']
            term_score = sum(0.3 for token in doc if token.lemma_.lower() in technical_terms)
            
            return min(entity_score + term_score, 2.0)
        except Exception:
            return 0.0

class OptimizedPDFProcessor:
    """Processador otimizado de PDFs com paralelização"""
    
    def __init__(self):
        self.detector = AdvancedTableDetector()
        self.stats = {
            'total_pages': 0,
            'parameter_pages': 0,
            'tables_extracted': 0,
            'zones_detected': set()
        }
    
    def process_pdf(self, pdf_path: Path) -> Tuple[str, Dict]:
        """Processa um PDF completo"""
        logger.info(f"Processando: {pdf_path.name}")
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                pages_data = []
                
                # Processa páginas em paralelo (grupos pequenos para evitar memory issues)
                total_pages = len(pdf.pages)
                self.stats['total_pages'] = total_pages
                
                # Processamento em batches para otimizar memória
                batch_size = min(10, total_pages)
                for i in range(0, total_pages, batch_size):
                    batch = pdf.pages[i:i+batch_size]
                    batch_results = self._process_page_batch(batch, i)
                    pages_data.extend(batch_results)
                
                # Consolida resultados
                content = self._consolidate_content(pages_data)
                
                logger.info(f"✅ {pdf_path.name}: {self.stats['parameter_pages']}/{total_pages} páginas relevantes")
                return content, self.stats.copy()
                
        except Exception as e:
            logger.error(f"❌ Erro ao processar {pdf_path}: {e}")
            return "", {}
    
    def _process_page_batch(self, pages: List, start_idx: int) -> List[Dict]:
        """Processa batch de páginas"""
        results = []
        
        for idx, page in enumerate(pages):
            page_num = start_idx + idx + 1
            
            # Extrai texto
            text = page.extract_text(
                x_tolerance=2,
                y_tolerance=2,
                layout=True,
                keep_blank_chars=True
            ) or ""
            
            # Extrai tabelas com múltiplas estratégias
            raw_tables = self._extract_tables_multi_strategy(page)
            
            # Detecta se é página de parâmetros
            is_param_page, confidence = self.detector.detect_parameters_table(text, raw_tables)
            
            if is_param_page:
                self.stats['parameter_pages'] += 1
                self.stats['tables_extracted'] += len(raw_tables)
                
                # Identifica zonas
                zones = self.detector.zone_pattern.findall(text.upper())
                self.stats['zones_detected'].update(zones)
                
                # Enriquece conteúdo
                enriched_content = self._enrich_page_content(
                    text, raw_tables, page_num, confidence, zones
                )
                
                results.append({
                    'page_num': page_num,
                    'content': enriched_content,
                    'is_parameter': True,
                    'confidence': confidence,
                    'zones': zones,
                    'table_count': len(raw_tables)
                })
        
        return results
    
    def _extract_tables_multi_strategy(self, page) -> List:
        """Extrai tabelas com múltiplas estratégias"""
        all_tables = []
        
        # Estratégia 1: Padrão
        try:
            tables = page.extract_tables()
            if tables:
                all_tables.extend(tables)
        except Exception:
            pass
        
        # Estratégia 2: Linhas estritas
        try:
            tables = page.extract_tables(
                table_settings={
                    "vertical_strategy": "lines_strict",
                    "horizontal_strategy": "lines_strict",
                    "intersection_tolerance": 3
                }
            )
            if tables:
                for table in tables:
                    if table not in all_tables:
                        all_tables.append(table)
        except Exception:
            pass
        
        # Estratégia 3: Texto estruturado
        try:
            tables = page.extract_tables(
                table_settings={
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                    "text_tolerance": 3
                }
            )
            if tables:
                for table in tables:
                    if table not in all_tables:
                        all_tables.append(table)
        except Exception:
            pass
        
        return all_tables
    
    def _enrich_page_content(self, text: str, tables: List, page_num: int, 
                           confidence: float, zones: List[str]) -> str:
        """Enriquece conteúdo da página com metadados estruturados"""
        
        enriched = f"\n\n=== PÁGINA {page_num} - PARÂMETROS URBANÍSTICOS ===\n"
        enriched += f"CONFIANÇA: {confidence:.2f}/10\n"
        enriched += "TIPO: Parâmetros de uso e ocupação do solo\n"
        
        if zones:
            enriched += f"ZONAS IDENTIFICADAS: {', '.join(set(zones))}\n"
        
        # Adiciona palavras-chave para busca
        keywords = self._extract_semantic_keywords(text)
        if keywords:
            enriched += f"PALAVRAS-CHAVE: {', '.join(keywords)}\n"
        
        enriched += "\n--- CONTEÚDO ORIGINAL ---\n"
        enriched += text
        enriched += "\n\n"
        
        # Processa tabelas estruturadas
        if tables:
            enriched += "--- TABELAS ESTRUTURADAS ---\n"
            for i, table in enumerate(tables):
                enriched += self._format_table_content(table, i + 1)
        
        # Adiciona análise semântica
        enriched += self._add_semantic_analysis(text, zones)
        
        enriched += "\n=== FIM DA PÁGINA ===\n"
        
        return enriched
    
    def _extract_semantic_keywords(self, text: str) -> List[str]:
        """Extrai palavras-chave semânticas relevantes"""
        keywords = set()
        
        # Keywords diretas
        direct_keywords = [
            'coeficiente de aproveitamento', 'taxa de ocupação', 'afastamento',
            'gabarito', 'altura máxima', 'recuo frontal', 'recuo lateral',
            'recuo de fundos', 'área permeável', 'uso permitido'
        ]
        
        text_lower = text.lower()
        for keyword in direct_keywords:
            if keyword in text_lower:
                keywords.add(keyword.replace(' ', '_'))
        
        # Zonas
        zones = self.detector.zone_pattern.findall(text.upper())
        for zone in zones:
            keywords.add(f"zona_{zone.replace('-', '_').replace(' ', '_').lower()}")
        
        return list(keywords)[:10]  # Limita a 10 keywords
    
    def _format_table_content(self, table: List, table_num: int) -> str:
        """Formata conteúdo estruturado da tabela"""
        if not table or len(table) == 0:
            return f"\n** TABELA {table_num} - VAZIA **\n"
        
        content = f"\n** TABELA {table_num} **\n"
        
        # Cabeçalho
        if table[0]:
            headers = [str(h).strip() if h else "" for h in table[0]]
            if any(h for h in headers):
                content += f"CABEÇALHO: {' | '.join(headers)}\n"
        
        # Dados
        for i, row in enumerate(table[1:] if len(table) > 1 else []):
            if not row:
                continue
            
            row_clean = [str(cell).strip() if cell else "" for cell in row]
            if any(cell for cell in row_clean):
                row_text = ' | '.join(row_clean)
                
                # Identifica zonas na linha
                zones_in_row = self.detector.zone_pattern.findall(row_text.upper())
                if zones_in_row:
                    content += f"ZONA-DADOS: {row_text} [ZONAS: {', '.join(zones_in_row)}]\n"
                else:
                    content += f"DADOS: {row_text}\n"
        
        return content + "\n"
    
    def _add_semantic_analysis(self, text: str, zones: List[str]) -> str:
        """Adiciona análise semântica do conteúdo"""
        analysis = "\n--- ANÁLISE SEMÂNTICA ---\n"
        
        # Zonas únicas
        unique_zones = list(set(zones))
        if unique_zones:
            analysis += f"ZONAS: {', '.join(unique_zones)}\n"
        
        # Valores numéricos importantes
        values = self.detector.numeric_pattern.findall(text)
        if values:
            analysis += f"VALORES: {', '.join(values[:15])}\n"  # Primeiros 15
        
        # Quadros/anexos
        quadros = re.findall(r'QUADRO\s+([IVXLCDM]+|\d+)', text.upper())
        if quadros:
            analysis += f"QUADROS: {', '.join(set(quadros))}\n"
        
        # Artigos/seções
        artigos = re.findall(r'ART\w*\.?\s*(\d+)', text.upper())
        if artigos:
            analysis += f"ARTIGOS: {', '.join(set(artigos[:5]))}\n"
        
        return analysis
    
    def _consolidate_content(self, pages_data: List[Dict]) -> str:
        """Consolida conteúdo de todas as páginas"""
        if not pages_data:
            return ""
        
        # Ordena por número da página
        pages_data.sort(key=lambda x: x['page_num'])
        
        # Combina conteúdo
        full_content = ""
        for page_data in pages_data:
            full_content += page_data['content']
        
        return full_content

class SmartChunker:
    """Chunker inteligente que preserva contexto de tabelas"""
    
    def __init__(self):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=CONFIG.CHUNK_SIZE,
            chunk_overlap=CONFIG.CHUNK_OVERLAP,
            separators=[
                "\n\n=== FIM DA PÁGINA ===\n",
                "\n--- FIM DAS TABELAS ---\n",
                "\n** TABELA",
                "\n=== PÁGINA",
                "\n\n",
                "\n",
                " "
            ],
            keep_separator=True
        )
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Split inteligente preservando contexto"""
        chunks = self.splitter.split_documents(documents)
        
        # Enriquece chunks com metadados avançados
        enriched_chunks = []
        for chunk in chunks:
            enriched_chunk = self._enrich_chunk_metadata(chunk)
            enriched_chunks.append(enriched_chunk)
        
        logger.info(f"Gerados {len(enriched_chunks)} chunks inteligentes")
        return enriched_chunks
    
    def _enrich_chunk_metadata(self, chunk: Document) -> Document:
        """Enriquece metadados do chunk"""
        content = chunk.page_content
        metadata = chunk.metadata.copy()
        
        # Tipo de conteúdo
        if any(marker in content for marker in ["TABELA", "ZONA-DADOS:", "CABEÇALHO:"]):
            metadata['tipo_conteudo'] = 'parametros_urbanisticos'
            metadata['contem_tabela'] = True
        else:
            metadata['tipo_conteudo'] = 'texto_geral'
            metadata['contem_tabela'] = False
        
        # Zonas específicas
        detector = AdvancedTableDetector()
        zones = detector.zone_pattern.findall(content.upper())
        if zones:
            unique_zones = list(set(zones))
            metadata['zonas_mencionadas'] = unique_zones
            if len(unique_zones) == 1:
                metadata['zona_especifica'] = unique_zones[0]
        
        # Quadros
        quadros = re.findall(r'QUADRO\s+([IVXLCDM]+|\d+)', content.upper())
        if quadros:
            metadata['quadros'] = list(set(quadros))
        
        # Densidade informacional
        numbers = detector.numeric_pattern.findall(content)
        metadata['densidade_numerica'] = len(numbers)
        
        # Score de relevância
        param_keywords = ['coeficiente', 'taxa', 'ocupação', 'aproveitamento', 'altura', 'recuo']
        relevance_score = sum(1 for kw in param_keywords if kw.lower() in content.lower())
        metadata['relevance_score'] = relevance_score
        
        return Document(page_content=content, metadata=metadata)

class OptimizedIngestor:
    """Ingestor principal otimizado"""
    
    def __init__(self):
        self.processor = OptimizedPDFProcessor()
        self.chunker = SmartChunker()
        self.embeddings = None
    
    def get_embeddings(self):
        """Lazy loading dos embeddings"""
        if self.embeddings is None:
            logger.info("Carregando modelo de embeddings...")
            self.embeddings = HuggingFaceEmbeddings(
                model_name=CONFIG.MODELO_EMBEDDING,
                model_kwargs={"device": "cpu"},
                encode_kwargs={'normalize_embeddings': True, 'show_progress_bar': True}
            )
        return self.embeddings
    
    def process_city(self, cidade: str):
        """Processa todos os PDFs de uma cidade"""
        logger.info(f"🚀 INGESTÃO OTIMIZADA - {cidade.upper()}")
        logger.info("=" * 60)
        
        # Setup
        collection_name = f"{CONFIG.NOME_BASE_COLECAO}_{cidade.lower()}"
        data_path = CONFIG.PASTA_DADOS_RAIZ / cidade.lower()
        
        if not data_path.exists():
            raise ValueError(f"Pasta não encontrada: {data_path}")
        
        # Remove coleção antiga
        self._cleanup_old_collection(collection_name)
        
        # Processa PDFs
        documents = self._load_and_process_pdfs(data_path)
        if not documents:
            raise ValueError("Nenhum documento processado!")
        
        # Chunking inteligente
        logger.info("✂️ Aplicando chunking inteligente...")
        chunks = self.chunker.split_documents(documents)
        
        # Salva estatísticas
        stats = self._calculate_stats(chunks)
        self._save_stats(data_path, stats)
        
        # Cria vectorstore
        logger.info("🧠 Gerando embeddings e salvando...")
        embeddings = self.get_embeddings()
        
        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            collection_name=collection_name,
            persist_directory=str(CONFIG.PASTA_BD)
        )
        
        logger.info("=" * 60)
        logger.info("🎉 INGESTÃO CONCLUÍDA COM SUCESSO!")
        logger.info(f"📊 Estatísticas finais:")
        logger.info(f"   • Documentos: {len(documents)}")
        logger.info(f"   • Chunks: {len(chunks)}")
        logger.info(f"   • Chunks com tabelas: {stats['chunks_com_tabelas']}")
        logger.info(f"   • Zonas detectadas: {len(stats['zonas_unicas'])}")
        
    def _cleanup_old_collection(self, collection_name: str):
        """Remove coleção antiga"""
        try:
            client = Chroma(persist_directory=str(CONFIG.PASTA_BD))
            client._client.delete_collection(name=collection_name)
            logger.info("🗑️ Coleção antiga removida")
        except Exception:
            logger.info("ℹ️ Nenhuma coleção anterior encontrada")
    
    def _load_and_process_pdfs(self, data_path: Path) -> List[Document]:
        """Carrega e processa todos os PDFs"""
        pdf_files = list(data_path.glob("*.pdf"))
        if not pdf_files:
            logger.warning("❌ Nenhum PDF encontrado!")
            return []
        
        logger.info(f"📄 Processando {len(pdf_files)} PDFs...")
        
        documents = []
        total_stats = {
            'total_pages': 0,
            'parameter_pages': 0,
            'tables_extracted': 0,
            'zones_detected': set()
        }
        
        # Processa PDFs (sequencial para controle de memória)
        for pdf_file in pdf_files:
            content, stats = self.processor.process_pdf(pdf_file)
            
            if content and len(content.strip()) > 200:
                doc = Document(
                    page_content=content,
                    metadata={
                        "fonte": pdf_file.name,
                        "tamanho_original": len(content),
                        "paginas_parametros": stats.get('parameter_pages', 0),
                        "tabelas_extraidas": stats.get('tables_extracted', 0),
                        "processamento": "otimizado_2.0"
                    }
                )
                documents.append(doc)
                
                # Agrega stats
                for key in ['total_pages', 'parameter_pages', 'tables_extracted']:
                    total_stats[key] += stats.get(key, 0)
                total_stats['zones_detected'].update(stats.get('zones_detected', set()))
                
                logger.info(f"✅ {pdf_file.name}: {stats.get('parameter_pages', 0)} páginas relevantes")
            else:
                logger.warning(f"⚠️ {pdf_file.name}: conteúdo insuficiente")
        
        # Log final
        logger.info(f"📊 Processamento concluído:")
        logger.info(f"   • Total de páginas: {total_stats['total_pages']}")
        logger.info(f"   • Páginas de parâmetros: {total_stats['parameter_pages']}")
        logger.info(f"   • Tabelas extraídas: {total_stats['tables_extracted']}")
        logger.info(f"   • Zonas detectadas: {len(total_stats['zones_detected'])}")
        
        return documents
    
    def _calculate_stats(self, chunks: List[Document]) -> Dict:
        """Calcula estatísticas dos chunks"""
        stats = {
            'total_chunks': len(chunks),
            'chunks_com_tabelas': 0,
            'zonas_unicas': set(),
            'quadros_encontrados': set(),
            'tipos_conteudo': {}
        }
        
        for chunk in chunks:
            meta = chunk.metadata
            
            # Contadores
            if meta.get('contem_tabela'):
                stats['chunks_com_tabelas'] += 1
            
            # Zonas
            if meta.get('zonas_mencionadas'):
                stats['zonas_unicas'].update(meta['zonas_mencionadas'])
            
            # Quadros
            if meta.get('quadros'):
                stats['quadros_encontrados'].update(meta['quadros'])
            
            # Tipos de conteúdo
            tipo = meta.get('tipo_conteudo', 'indefinido')
            stats['tipos_conteudo'][tipo] = stats['tipos_conteudo'].get(tipo, 0) + 1
        
        # Converte sets para listas para serialização
        stats['zonas_unicas'] = list(stats['zonas_unicas'])
        stats['quadros_encontrados'] = list(stats['quadros_encontrados'])
        
        return stats
    
    def _save_stats(self, data_path: Path, stats: Dict):
        """Salva estatísticas de processamento"""
        stats_file = data_path / "estatisticas_processamento.json"
        
        # Adiciona timestamp
        stats['timestamp'] = pd.Timestamp.now().isoformat()
        stats['versao_ingest'] = "2.0_otimizado"
        
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Estatísticas salvas em: {stats_file}")

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(
        description="Ingestão otimizada 2.0 para sistema RAG de análise regulatória"
    )
    parser.add_argument(
        "cidade", 
        type=str, 
        help="Nome da cidade (pasta em 'dados/')"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=CONFIG.MAX_WORKERS,
        help="Número de workers paralelos"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=CONFIG.CHUNK_SIZE,
        help="Tamanho dos chunks"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Modo verboso"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Atualiza config com argumentos
    CONFIG.MAX_WORKERS = args.workers
    CONFIG.CHUNK_SIZE = args.chunk_size
    
    # Executa ingestão
    try:
        ingestor = OptimizedIngestor()
        ingestor.process_city(args.cidade)
        
    except Exception as e:
        logger.error(f"❌ Erro na ingestão: {e}")
        raise

if __name__ == "__main__":
    main()