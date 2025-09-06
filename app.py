# app_melhorado.py - Versão Otimizada 6.0

# Fix SQLite compatibility for ChromaDB - MUST be before any other imports
import chroma_wrapper

import os, asyncio, streamlit as st, re, json, time, pathlib, logging
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables early
load_dotenv()
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.prompts import PromptTemplate
from langchain_google_genai import GoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from chroma_wrapper import Chroma
from langchain.schema import Document
import pypdf
import pandas as pd
from datetime import datetime
from utils import encontrar_zona_por_endereco
from detect_zone_enhanced import detect_zone_professional
from enhanced_official_system import EnhancedOfficialSystem

# Configuração de logging otimizada
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ProjectConfig:
    """Configurações centralizadas do projeto"""
    PASTA_DADOS_RAIZ: pathlib.Path = pathlib.Path(__file__).parent / "dados"
    PASTA_BD: pathlib.Path = pathlib.Path(__file__).parent / "db"
    MODELO_EMBEDDING: str = "sentence-transformers/all-MiniLM-L6-v2"
    NOME_BASE_COLECAO: str = "regulamentacao"
    MODELO_LLM: str = "gemini-1.5-pro-latest"
    CAMINHO_MAPA_ZONEAMENTO: pathlib.Path = pathlib.Path(__file__).parent / "mapas" / "feature_20250828120625247331.shp"
    VERSAO_APP: str = "6.0"
    MAX_WORKERS: int = 4
    CACHE_TTL: int = 3600
    CHUNK_SIZE: int = 1500
    OVERLAP_SIZE: int = 300

CONFIG = ProjectConfig()

class CacheManager:
    """Gerenciador de cache otimizado"""
    
    def __init__(self):
        self._cache = {}
        self._timestamps = {}
    
    def get(self, key: str, default=None):
        if key in self._cache:
            if time.time() - self._timestamps[key] < CONFIG.CACHE_TTL:
                return self._cache[key]
            else:
                self.invalidate(key)
        return default
    
    def set(self, key: str, value):
        self._cache[key] = value
        self._timestamps[key] = time.time()
    
    def invalidate(self, key: str):
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)

# Cache global
cache = CacheManager()

class ResourceManager:
    """Gerenciador otimizado de recursos"""
    
    def __init__(self):
        self._resources = {}
        self._embeddings = None
    
    @property
    def embeddings(self):
        if self._embeddings is None:
            logger.info("Carregando modelo de embeddings...")
            self._embeddings = HuggingFaceEmbeddings(
                model_name=CONFIG.MODELO_EMBEDDING,
                model_kwargs={"device": "cpu"},
                encode_kwargs={'normalize_embeddings': True}  # Melhora a precisão
            )
        return self._embeddings
    
    def get_resources(self, cidade: str) -> Dict[str, Any]:
        cache_key = f"resources_{cidade}"
        resources = cache.get(cache_key)
        
        if resources is None:
            logger.info(f"Carregando recursos para {cidade}...")
            nome_colecao = f"{CONFIG.NOME_BASE_COLECAO}_{cidade.lower()}"
            
            vectorstore = Chroma(
                persist_directory=str(CONFIG.PASTA_BD),
                embedding_function=self.embeddings,
                collection_name=nome_colecao
            )
            
            llm = GoogleGenerativeAI(
                model=CONFIG.MODELO_LLM,
                temperature=0.1,
                max_retries=3
            )
            
            resources = {
                "vectorstore": vectorstore,
                "llm": llm,
                "embeddings": self.embeddings
            }
            cache.set(cache_key, resources)
            logger.info(f"Recursos para {cidade} carregados e cached")
        
        return resources

# Instância global do gerenciador
resource_manager = ResourceManager()

class ProjectDataCalculator:
    """Calculadora de parâmetros urbanísticos do projeto"""
    
    @staticmethod
    def calcular_taxa_ocupacao(area_projecao: float, area_lote: float) -> float:
        """Calcula taxa de ocupação em %"""
        if area_lote <= 0:
            return 0.0
        return (area_projecao / area_lote) * 100
    
    @staticmethod
    def calcular_coeficiente_aproveitamento(area_construida_total: float, area_lote: float) -> float:
        """Calcula coeficiente de aproveitamento"""
        if area_lote <= 0:
            return 0.0
        return area_construida_total / area_lote
    
    @staticmethod
    def calcular_taxa_permeabilidade(area_permeavel: float, area_lote: float) -> float:
        """Calcula taxa de permeabilidade em %"""
        if area_lote <= 0:
            return 0.0
        return (area_permeavel / area_lote) * 100
    
    @staticmethod
    def calcular_area_util_lote(area_total: float, area_app: float = 0.0, area_drenagem: float = 0.0) -> float:
        """Calcula área útil do lote descontando restrições"""
        return area_total - area_app - area_drenagem
    
    @staticmethod
    def validar_consistencia_dados(dados: dict) -> list:
        """Valida consistência dos dados inseridos"""
        erros = []
        
        # Validações básicas
        if dados.get('area_projecao', 0) > dados.get('area_lote', 0):
            erros.append("Área de projeção não pode ser maior que a área do lote")
        
        if dados.get('area_construida_total', 0) < dados.get('area_projecao', 0):
            erros.append("Área construída total deve ser maior ou igual à área de projeção")
        
        area_restricoes = dados.get('area_app', 0) + dados.get('area_drenagem', 0)
        if area_restricoes > dados.get('area_lote', 0):
            erros.append("Soma de áreas restritivas não pode ser maior que a área do lote")
        
        if dados.get('area_permeavel', 0) > dados.get('area_lote', 0):
            erros.append("Área permeável não pode ser maior que a área do lote")
        
        return erros

class HeightConverter:
    """Conversor inteligente entre metros e pavimentos"""
    
    # Padrões típicos de altura por pavimento
    ALTURA_PADRAO_PAVIMENTO = 3.0  # metros (conforme prática de mercado)
    ALTURA_MINIMA_PAVIMENTO = 2.4   # metros (mínimo legal típico)
    ALTURA_MAXIMA_PAVIMENTO = 4.0   # metros (máximo razoável)
    
    @staticmethod
    def metros_para_pavimentos(metros: float) -> float:
        """Converte metros para número de pavimentos"""
        return metros / HeightConverter.ALTURA_PADRAO_PAVIMENTO
    
    @staticmethod
    def pavimentos_para_metros(pavimentos: float) -> float:
        """Converte pavimentos para metros"""
        return pavimentos * HeightConverter.ALTURA_PADRAO_PAVIMENTO
    
    @staticmethod
    def detectar_unidade_altura(valor: float) -> str:
        """Detecta se um valor provavelmente representa metros ou pavimentos"""
        # Lógica melhorada baseada em ranges típicos
        if valor <= 6:  # Até 6 pode ser pavimentos (comum em legislação)
            return "pavimentos" 
        elif valor > 6 and valor <= 40:  # Entre 6 e 40 são provavelmente metros
            return "metros"
        elif valor > 40:  # Acima de 40 provavelmente metros (prédios altos)
            return "metros"
        else:
            return "ambiguo"
    
    @staticmethod
    def normalizar_altura(valor: float, unidade_detectada: str = None) -> dict:
        """
        Normaliza altura para ambas as unidades com informações detalhadas
        
        Returns:
            dict: {
                'metros': float,
                'pavimentos': float,
                'unidade_original': str,
                'conversao_aplicada': bool
            }
        """
        if unidade_detectada is None:
            unidade_detectada = HeightConverter.detectar_unidade_altura(valor)
        
        if unidade_detectada == "metros":
            return {
                'metros': valor,
                'pavimentos': HeightConverter.metros_para_pavimentos(valor),
                'unidade_original': 'metros',
                'conversao_aplicada': True
            }
        elif unidade_detectada == "pavimentos":
            return {
                'metros': HeightConverter.pavimentos_para_metros(valor),
                'pavimentos': valor,
                'unidade_original': 'pavimentos', 
                'conversao_aplicada': True
            }
        else:
            # Caso ambíguo, assume metros (mais comum em memoriais)
            return {
                'metros': valor,
                'pavimentos': HeightConverter.metros_para_pavimentos(valor),
                'unidade_original': 'metros_assumido',
                'conversao_aplicada': False
            }

class ParameterExtractor:
    """Extrator otimizado de parâmetros"""
    
    PATTERNS = {
        "taxa_ocupacao": re.compile(r"taxa\s+de\s+ocupa[çc][ãa]o\s*(?:máxima)?[:\s]*(\d+[.,]?\d*)\s*%", re.IGNORECASE),
        "coeficiente_aproveitamento": re.compile(r"coeficiente\s+de\s+aproveitamento\s*(?:máximo)?[:\s]*(\d+[.,]?\d*)", re.IGNORECASE),
        "altura_edificacao": re.compile(r"altura\s+(?:da\s+edificação|máxima)[:\s]*(\d+[.,]?\d*)\s*m", re.IGNORECASE),
        "recuo_frontal": re.compile(r"recuo\s+frontal[:\s]*(\d+[.,]?\d*)\s*m", re.IGNORECASE),
        "recuos_laterais": re.compile(r"recuos?\s+laterais?[:\s]*(\d+[.,]?\d*)\s*m", re.IGNORECASE),
        "recuo_fundos": re.compile(r"recuos?\s+(?:de\s+)?fundos?[:\s]*(\d+[.,]?\d*)\s*m", re.IGNORECASE),
        "area_permeavel": re.compile(r"[áa]rea\s+perm[eé][aá]vel[:\s]*(\d+[.,]?\d*)\s*%", re.IGNORECASE)
    }
    
    @classmethod
    def extract(cls, texto: str) -> Dict[str, Optional[float]]:
        parametros = {}
        
        for param, pattern in cls.PATTERNS.items():
            match = pattern.search(texto)
            if match:
                try:
                    valor = float(match.group(1).replace(',', '.'))
                    parametros[param] = valor
                    
                    # Tratamento especial para altura da edificação
                    if param == "altura_edificacao":
                        altura_info = HeightConverter.normalizar_altura(valor)
                        parametros["altura_metros"] = altura_info['metros']
                        parametros["altura_pavimentos"] = round(altura_info['pavimentos'], 1)
                        parametros["altura_unidade_original"] = altura_info['unidade_original']
                        
                except ValueError:
                    parametros[param] = None
            else:
                parametros[param] = None
        
        return parametros

class DocumentRetriever:
    """Retriever otimizado com busca híbrida"""
    
    def __init__(self, vectorstore, max_docs: int = 7):
        self.vectorstore = vectorstore
        self.max_docs = max_docs
    
    def search(self, zona: str, query_terms: List[str]) -> List[Document]:
        """Busca híbrida otimizada"""
        print(f"DEBUG - Iniciando search() para zona: '{zona}'")
        
        # Garante que as variáveis são sempre definidas
        zona_normalizada = zona  # Valor padrão seguro
        zona_limpa = zona.upper().replace(" ", "-")  # Valor padrão seguro
        
        try:
            # Normaliza a zona usando o mapeamento
            print(f"DEBUG - zona_normalizada inicializada: '{zona_normalizada}'")
            
            try:
                from zona_mapping import normalizar_zona
                zona_normalizada = normalizar_zona(zona)
                print(f"DEBUG - Busca de documentos: '{zona}' -> normalizada: '{zona_normalizada}'")
            except ImportError:
                print(f"DEBUG - zona_mapping não encontrado, usando zona original: '{zona}'")
                zona_normalizada = zona
            except Exception as e:
                print(f"DEBUG - Erro ao normalizar zona: {e}, usando zona original: '{zona}'")
                zona_normalizada = zona
            
            print(f"DEBUG - Valor final de zona_normalizada: '{zona_normalizada}'")
            zona_limpa = zona_normalizada.upper().replace(" ", "-")
            print(f"DEBUG DocumentRetriever - Zona limpa para busca: '{zona_limpa}'")
            
        except Exception as e:
            print(f"DEBUG - Erro crítico na normalização: {e}")
            # Garante valores seguros mesmo em caso de erro
            zona_normalizada = zona
            zona_limpa = zona.upper().replace(" ", "-")
        documentos = []
        
        # Estratégia 1: Busca por filtros
        try:
            # Gerador robusto de variações para TODAS as zonas
            zona_variations = self._gerar_variacoes_zona(zona_limpa)
            print(f"DEBUG - Variações da zona '{zona_limpa}': {zona_variations}")
            
            filtros = []
            for zona_var in zona_variations:
                filtros.extend([
                    {'zona_especifica': zona_var},
                    {'zona_especifica': zona_var.replace('-', '')},
                    {'zona_especifica': zona_var.replace('.', '')},
                    {'zonas_mencionadas': {'$in': [zona_var]}},
                ])
            print(f"DEBUG - Total filtros: {len(filtros)}")
            
            for i, filtro in enumerate(filtros):
                try:
                    resultados = self.vectorstore.get(where=filtro, limit=5)
                    docs_count = len(resultados.get('documents', [])) if resultados else 0
                    print(f"DEBUG - Filtro {i+1}/{len(filtros)}: {filtro} -> {docs_count} docs")
                    
                    if resultados and resultados.get('documents'):
                        docs = [
                            Document(page_content=d, metadata=m) 
                            for d, m in zip(resultados['documents'], resultados['metadatas'])
                        ]
                        documentos.extend(docs)
                except Exception as e:
                    print(f"DEBUG - Erro no filtro {filtro}: {e}")
                    logger.warning(f"Erro no filtro {filtro}: {e}")
                    
        except Exception as e:
            logger.warning(f"Erro na busca por filtros: {e}")
        
        # Estratégia 2: Busca semântica
        if len(documentos) < 3:
            try:
                retriever = self.vectorstore.as_retriever(
                    search_type="similarity", 
                    search_kwargs={'k': 10}
                )
                
                queries = [
                    f"tabela parâmetros {zona_limpa} coeficiente aproveitamento taxa ocupação",
                    f"{zona_limpa} altura recuos afastamentos",
                    f"zona {zona_limpa} uso ocupação solo"
                ]
                
                docs_unicos = {hash(d.page_content) for d in documentos}
                
                for query in queries:
                    try:
                        docs = retriever.get_relevant_documents(query)
                        for doc in docs:
                            if zona_limpa.lower() in doc.page_content.lower():
                                doc_hash = hash(doc.page_content)
                                if doc_hash not in docs_unicos:
                                    documentos.append(doc)
                                    docs_unicos.add(doc_hash)
                    except Exception as e:
                        logger.warning(f"Erro na query '{query}': {e}")
                        
            except Exception as e:
                logger.warning(f"Erro na busca semântica: {e}")
        
        # Remover duplicatas e ordenar por relevância
        docs_finais = self._remove_duplicates_and_rank(documentos, zona_limpa)
        return docs_finais[:self.max_docs]
    
    def _gerar_variacoes_zona(self, zona: str) -> List[str]:
        """
        Gera todas as variações possíveis de uma zona para busca robusta
        Baseado na análise das 39 zonas encontradas na base de dados
        """
        import re
        
        variacoes = set([zona])  # Sempre inclui a zona original
        
        # Padrões identificados na base:
        # ZR1, ZR2, ZR3, ZR-4, ZR3-T
        # ZS-1, ZS-2
        # ZUM-1, ZUM-2, ZUM-3
        # ECO-1, ECO-2, ECO-3, ECO-4
        # ZH-1, ZH-2
        # ZCC (sem .4)
        # EAC, EACB, EACF, EMF, EMLV, EE, ENC
        # ZC, ZE, ZI, ZM, ZT, ZSF, ZSM, ZCSF, ZCUM, ZPS, ZROC, ZROI, ZUMVP
        # SEHIS, SEPE
        
        # 1. Variações com/sem hífen
        if '-' in zona:
            # ZR-4 → ZR4
            variacoes.add(zona.replace('-', ''))
            # ZR-4 → ZR4, ZR_4
            variacoes.add(zona.replace('-', '_'))
        else:
            # ZR4 → ZR-4
            # Procura padrões como ZR4, ZS2, ZUM3, ECO1, etc.
            match = re.match(r'^([A-Z]+)(\d+)$', zona)
            if match:
                prefixo, numero = match.groups()
                variacoes.add(f"{prefixo}-{numero}")
                variacoes.add(f"{prefixo}_{numero}")
        
        # 2. Variações com/sem ponto
        if '.' in zona:
            # ZCC.4 → ZCC, ZCC4, ZCC-4
            base = zona.split('.')[0]
            numero = zona.split('.')[1] if len(zona.split('.')) > 1 else ''
            variacoes.add(base)  # ZCC.4 → ZCC (padrão da base!)
            if numero:
                variacoes.add(f"{base}{numero}")      # ZCC.4 → ZCC4
                variacoes.add(f"{base}-{numero}")     # ZCC.4 → ZCC-4
                variacoes.add(f"{base}_{numero}")     # ZCC.4 → ZCC_4
        else:
            # ZCC → ZCC.4 (caso contrário)
            # Para zonas que podem ter subtipos
            if zona in ['ZCC', 'ZR', 'ZS', 'ZUM', 'ECO', 'ZH']:
                for i in range(1, 6):  # Tenta números 1-5
                    variacoes.add(f"{zona}.{i}")
                    variacoes.add(f"{zona}{i}")
                    variacoes.add(f"{zona}-{i}")
        
        # 3. Variações especiais conhecidas
        especiais = {
            # Zonas residenciais
            'ZR1': ['ZR-1', 'ZR_1', 'ZR.1', 'ZONA-RESIDENCIAL-1'],
            'ZR2': ['ZR-2', 'ZR_2', 'ZR.2', 'ZONA-RESIDENCIAL-2'],
            'ZR3': ['ZR-3', 'ZR_3', 'ZR.3', 'ZONA-RESIDENCIAL-3'],
            'ZR-4': ['ZR4', 'ZR_4', 'ZR.4', 'ZONA-RESIDENCIAL-4'],
            'ZR3-T': ['ZR3T', 'ZR3_T', 'ZR-3-T', 'ZR-3T'],
            'ZROC': ['ZR-OC', 'ZR_OC', 'ZONA-RESIDENCIAL-OC'],
            'ZROI': ['ZR-OI', 'ZR_OI', 'ZONA-RESIDENCIAL-OI'],
            
            # Zona Centro Cívico (caso especial!)
            'ZCC.4': ['ZCC', 'ZCC4', 'ZCC-4', 'ZCC_4', 'ZONA-CENTRO-CIVICO'],
            'ZCC': ['ZCC.4', 'ZCC4', 'ZCC-4', 'ZCC_4', 'ZONA-CENTRO-CIVICO'],
            
            # Zonas centrais
            'ZC': ['ZONA-CENTRAL', 'CENTRO'],
            'ZCSF': ['ZC-SF', 'ZC_SF', 'ZONA-CENTRAL-SF'],
            'ZCUM': ['ZC-UM', 'ZC_UM', 'ZONA-CENTRAL-UM'],
            
            # Zonas de serviço
            'ZS-1': ['ZS1', 'ZS_1', 'ZS.1', 'ZONA-SERVICOS-1'],
            'ZS-2': ['ZS2', 'ZS_2', 'ZS.2', 'ZONA-SERVICOS-2'],
            'ZSF': ['ZS-F', 'ZS_F', 'ZONA-SERVICOS-F'],
            'ZSM': ['ZS-M', 'ZS_M', 'ZONA-SERVICOS-M'],
            
            # Zonas de uso misto
            'ZUM-1': ['ZUM1', 'ZUM_1', 'ZUM.1', 'ZONA-USO-MISTO-1'],
            'ZUM-2': ['ZUM2', 'ZUM_2', 'ZUM.2', 'ZONA-USO-MISTO-2'],
            'ZUM-3': ['ZUM3', 'ZUM_3', 'ZUM.3', 'ZONA-USO-MISTO-3'],
            'ZUMVP': ['ZUM-VP', 'ZUM_VP', 'ZONA-USO-MISTO-VP'],
            
            # Zonas habitacionais
            'ZH-1': ['ZH1', 'ZH_1', 'ZH.1', 'ZONA-HABITACIONAL-1'],
            'ZH-2': ['ZH2', 'ZH_2', 'ZH.2', 'ZONA-HABITACIONAL-2'],
            
            # Zonas ecológicas
            'ECO-1': ['ECO1', 'ECO_1', 'ECO.1', 'ZONA-ECOLOGICA-1'],
            'ECO-2': ['ECO2', 'ECO_2', 'ECO.2', 'ZONA-ECOLOGICA-2'],
            'ECO-3': ['ECO3', 'ECO_3', 'ECO.3', 'ZONA-ECOLOGICA-3'],
            'ECO-4': ['ECO4', 'ECO_4', 'ECO.4', 'ZONA-ECOLOGICA-4'],
            
            # Eixos e setores especiais
            'EAC': ['E-AC', 'E_AC', 'EIXO-AC'],
            'EACB': ['E-ACB', 'E_ACB', 'EIXO-ACB'],
            'EACF': ['E-ACF', 'E_ACF', 'EIXO-ACF'],
            'EMF': ['E-MF', 'E_MF', 'EIXO-MF'],
            'EMLV': ['E-MLV', 'E_MLV', 'EIXO-MLV'],
            'EE': ['E-E', 'E_E', 'EIXO-E'],
            'ENC': ['E-NC', 'E_NC', 'EIXO-NC'],
            
            # Setores especiais
            'SEHIS': ['SE-HIS', 'SE_HIS', 'SETOR-ESPECIAL-HIS'],
            'SEPE': ['SE-PE', 'SE_PE', 'SETOR-ESPECIAL-PE'],
            
            # Outras zonas
            'ZE': ['ZONA-ESPECIAL', 'Z-E', 'Z_E'],
            'ZI': ['ZONA-INDUSTRIAL', 'Z-I', 'Z_I'],
            'ZM': ['ZONA-MISTA', 'Z-M', 'Z_M'],
            'ZT': ['ZONA-TRANSICAO', 'Z-T', 'Z_T'],
            'ZPS': ['ZP-S', 'ZP_S', 'ZONA-PRESERVACAO-S'],
        }
        
        if zona in especiais:
            variacoes.update(especiais[zona])
        
        # 4. Variações genéricas adicionais
        # Remove espaços, underscores, hífens
        base_limpa = zona.replace('-', '').replace('_', '').replace('.', '').replace(' ', '')
        variacoes.add(base_limpa)
        
        # Adiciona versões com espaços
        if '-' in zona:
            variacoes.add(zona.replace('-', ' '))
        if '_' in zona:
            variacoes.add(zona.replace('_', ' '))
        if '.' in zona:
            variacoes.add(zona.replace('.', ' '))
        
        # Converte para lista e remove duplicatas
        lista_final = sorted(list(variacoes))
        
        print(f"DEBUG _gerar_variacoes_zona - '{zona}' gerou {len(lista_final)} variações")
        
        return lista_final
    
    def _remove_duplicates_and_rank(self, docs: List[Document], zona: str) -> List[Document]:
        """Remove duplicatas e ordena por relevância"""
        docs_unicos = []
        conteudos_vistos = set()
        
        for doc in docs:
            conteudo_hash = hash(doc.page_content[:500])  # Hash dos primeiros 500 chars
            if conteudo_hash not in conteudos_vistos:
                conteudos_vistos.add(conteudo_hash)
                docs_unicos.append(doc)
        
        # Ordenar por relevância
        def score_relevance(doc):
            score = 0
            content = doc.page_content.upper()
            meta = doc.metadata
            
            # Pontuação por zona específica
            if meta.get('zona_especifica') == zona:
                score += 10
            elif zona in content:
                score += 5
            
            # Pontuação por tipo de conteúdo
            if meta.get('tipo_conteudo') == 'parametros_urbanisticos':
                score += 8
            elif meta.get('contem_tabela'):
                score += 4
            
            # Pontuação por densidade de informação relevante
            palavras_chave = ['coeficiente', 'taxa', 'altura', 'recuo', 'afastamento']
            score += sum(2 for palavra in palavras_chave if palavra in content.lower())
            
            return score
        
        docs_unicos.sort(key=score_relevance, reverse=True)
        return docs_unicos

class ReportGenerator:
    """Gerador otimizado de relatórios"""
    
    TEMPLATE = """
    Você é um especialista em análise de conformidade urbanística com 20 anos de experiência.
    
    CONTEXTO DA LEGISLAÇÃO:
    {context}
    
    ANÁLISE SOLICITADA:
    {question}
    
    INSTRUÇÕES CRÍTICAS:
    1. Extraia EXATAMENTE os valores do projeto do memorial fornecido
    2. Identifique os limites da legislação nos documentos de contexto
    3. Compare numericamente cada parâmetro
    4. IMPORTANTE - Para ALTURA DA EDIFICAÇÃO: Se a legislação especifica limite em pavimentos e o projeto em metros (ou vice-versa), use a conversão: 1 pavimento = 3,0 metros (padrão técnico)
    5. Use APENAS "[OK] Conforme" ou "[ERROR] Não Conforme" na coluna Conformidade
    6. Seja CONCLUSIVO no parecer final sobre aprovação/reprovação
    7. Na coluna "Observação" para altura, sempre explicite a conversão feita (ex: "8,5m = 2,8 pavimentos")
    
    FORMATO OBRIGATÓRIO:
    
    ## 1. Identificação do Projeto
    - **Endereço:** [endereço]
    - **Zona de Uso:** [zona]
    - **Data da Análise:** {data_analise}
    
    ## 2. Análise dos Parâmetros
    
    | Parâmetro | Valor no Projeto | Valor Máximo Permitido | Conformidade | Observação |
    |---|---|---|---|---|
    | Taxa de Ocupação | [valor]% | [valor]% | [OK]/[ERROR] | [obs] |
    | Coeficiente de Aproveitamento | [valor] | [valor] | [OK]/[ERROR] | [obs] |
    | Altura da Edificação | [valor]m | [valor]m | [OK]/[ERROR] | [obs] |
    | Recuo Frontal | [valor]m | [valor]m | [OK]/[ERROR] | [obs] |
    | Recuos Laterais | [valor]m | [valor]m | [OK]/[ERROR] | [obs] |
    | Recuo de Fundos | [valor]m | [valor]m | [OK]/[ERROR] | [obs] |
    | Área Permeável | [valor]% | [valor]% | [OK]/[ERROR] | [obs] |
    
    ## 3. Parecer Final
    [Conclusão sobre conformidade - APROVADO ou REPROVADO]
    
    ## 4. Recomendações
    [Ajustes necessários ou "Nenhuma recomendação necessária"]
    """
    
    def __init__(self, llm):
        self.llm = llm
        self.prompt = PromptTemplate(
            template=self.TEMPLATE,
            input_variables=["context", "question", "data_analise"]
        )
        self.chain = load_qa_chain(llm, chain_type="stuff", prompt=self.prompt)
    
    def generate(self, documents: List[Document], query: str) -> str:
        """Gera relatório com retry automático"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                resultado = self.chain.invoke({
                    "input_documents": documents,
                    "question": query,
                    "data_analise": datetime.now().strftime("%d/%m/%Y")
                }, return_only_outputs=True)
                
                return resultado['output_text']
                
            except Exception as e:
                logger.warning(f"Tentativa {attempt + 1} falhou: {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)  # Backoff exponencial

class AnalysisEngine:
    """Engine principal de análise"""
    
    def __init__(self):
        self.extractor = ParameterExtractor()
        self.enhanced_official = EnhancedOfficialSystem()
    
    def run_analysis(self, cidade: str, endereco: str, memorial: str, 
                    zona_manual: Optional[str] = None, usar_zona_manual: bool = False,
                    inscricao: Optional[str] = None) -> Dict[str, Any]:
        """Execução otimizada da análise"""
        
        try:
            # 1. Carregar recursos
            resources = resource_manager.get_resources(cidade)
            
            # 2. Identificar zona com sistema GIS profissional
            if usar_zona_manual and zona_manual:
                zona = zona_manual
                zona_info = f"{zona} (INFORMADA MANUALMENTE)"
                detection_details = "Zona informada pelo usuário"
            else:
                # Usar sistema oficial aprimorado (Shapefile + Web Scraper + Sistema Local)
                enhanced_result = self.enhanced_official.detect_zone_enhanced_official(endereco or "", inscricao or "")
                zona = enhanced_result.zona
                
                # Criar informações detalhadas da detecção oficial aprimorada
                if enhanced_result.confidence in ["OFICIAL_SHAPEFILE", "DUPLA_CONFIRMACAO"]:
                    zona_info = f"{zona} (DETECTADA OFICIALMENTE)"
                    detection_details = f"Zona oficial via {enhanced_result.source} - {enhanced_result.details}"
                elif enhanced_result.confidence in ["SEHIS_CONFIRMADO", "SEHIS_CORRIGIDO"]:
                    zona_info = f"{zona} (SEHIS CONFIRMADO)"
                    detection_details = f"SEHIS detectado via {enhanced_result.consolidation_method} - {enhanced_result.details}"
                elif enhanced_result.confidence in ["OFICIAL_WEB", "ESTIMADO_LOCAL"]:
                    zona_info = f"{zona} (DETECTADA AUTOMATICAMENTE)"
                    detection_details = f"Zona detectada via {enhanced_result.consolidation_method} - {enhanced_result.details}"
                else:
                    zona_info = f"{zona} (VERIFICAÇÃO RECOMENDADA)"
                    detection_details = f"Zona com baixa confiança - {enhanced_result.details}"
                
                print(f"DEBUG SISTEMA OFICIAL - Zona final: {zona} | Confiança: {enhanced_result.confidence} | Método: {enhanced_result.consolidation_method}")
                print(f"DEBUG SISTEMA OFICIAL - Fonte: {enhanced_result.source}")
                if enhanced_result.official_zone:
                    print(f"DEBUG SISTEMA OFICIAL - Shapefile oficial: {enhanced_result.official_zone} ({enhanced_result.official_name})")
                if enhanced_result.web_scraper_zone:
                    print(f"DEBUG SISTEMA OFICIAL - Web scraper: {enhanced_result.web_scraper_zone}")
                if enhanced_result.local_zone:
                    print(f"DEBUG SISTEMA OFICIAL - Sistema local: {enhanced_result.local_zone}")
            
            # Salvar informações de detecção para uso posterior
            zona_detection_info = zona_info
            zona_detection_details = detection_details
            
            # 3. Extrair parâmetros
            parametros = self.extractor.extract(memorial)
            
            # 4. Buscar documentos
            retriever = DocumentRetriever(resources["vectorstore"])
            documentos = retriever.search(zona, list(parametros.keys()))
            
            print(f"DEBUG DocumentRetriever - Total documentos encontrados: {len(documentos)}")
            for i, doc in enumerate(documentos[:3]):  # Mostra apenas os 3 primeiros
                print(f"DEBUG Doc {i+1} metadata: {doc.metadata}")
                print(f"DEBUG Doc {i+1} content preview: {doc.page_content[:200]}...")
            
            if not documentos:
                print(f"DEBUG - Busca falhou para zona: {zona}")
                vectorstore = resources["vectorstore"]
                
                # Check if vectorstore is completely unavailable (neither ChromaDB nor fallback)
                if not hasattr(vectorstore, 'available') or not vectorstore.available:
                    raise ValueError(f"Base de dados não está disponível. Sistema de fallback também não foi carregado.")
                
                # If vectorstore is available but no documents found, provide helpful message
                if hasattr(vectorstore, 'fallback_retriever') and vectorstore.fallback_retriever:
                    print("DEBUG - Using fallback retriever, checking available zones...")
                    # Get a sample of available zones from fallback data
                    sample_docs = vectorstore.fallback_retriever.get(limit=10)
                    available_zones = set()
                    for metadata in sample_docs.get('metadatas', []):
                        if 'zona_especifica' in metadata and metadata['zona_especifica']:
                            available_zones.add(metadata['zona_especifica'])
                    
                    if available_zones:
                        zones_str = ', '.join(sorted(available_zones))
                        raise ValueError(f"Nenhum documento encontrado para a zona {zona}. Zonas disponíveis no sistema: {zones_str}")
                    else:
                        raise ValueError(f"Nenhum documento encontrado para a zona {zona}. Sistema funcionando mas sem dados de zona.")
                else:
                    raise ValueError(f"Nenhum documento encontrado para a zona {zona}. Verifique se a zona está correta ou se os dados foram processados.")
            
            # 5. Gerar relatório
            generator = ReportGenerator(resources["llm"])
            query = self._build_query(endereco, cidade, zona, memorial, parametros)
            relatorio = generator.generate(documentos, query)
            
            return {
                'resultado': relatorio,
                'documentos': documentos,
                'memorial': memorial,
                'zona': zona,
                'zona_info': zona_detection_info,
                'zona_detection_details': zona_detection_details,
                'parametros': parametros,
                'info_projeto': {
                    'Endereço': endereco if endereco else 'NÃO INFORMADO',
                    'Zona_de_Uso': zona_detection_info,
                    'Sistema_Detecção': zona_detection_details,
                    'Município': cidade.capitalize(),
                    'Data_da_Análise': datetime.now().strftime("%d/%m/%Y")
                }
            }
            
        except Exception as e:
            logger.error(f"Erro na análise: {e}")
            raise
    
    def _build_query(self, endereco: str, cidade: str, zona: str, memorial: str, parametros: dict = None) -> str:
        """Constrói query otimizada"""
        query = f"""
        DADOS DO PROJETO:
        - Endereço: {endereco}
        - Município: {cidade.capitalize()}
        - Zona de Uso: {zona}
        
        MEMORIAL DESCRITIVO:
        {memorial}
        """
        
        # Adiciona informações de conversão de altura se disponível
        if parametros and parametros.get('altura_edificacao') is not None:
            altura_m = parametros.get('altura_metros', parametros['altura_edificacao'])
            altura_pav = parametros.get('altura_pavimentos', HeightConverter.metros_para_pavimentos(parametros['altura_edificacao']))
            unidade_orig = parametros.get('altura_unidade_original', 'metros')
            
            query += f"""
        
        INFORMAÇÕES ADICIONAIS SOBRE ALTURA:
        - Altura informada no memorial: {parametros['altura_edificacao']} {unidade_orig}
        - Equivalência: {altura_m:.1f} metros = {altura_pav:.1f} pavimentos
        - Conversão baseada no padrão técnico: 1 pavimento = 3,0 metros
        """
        
        query += f"""
        
        TAREFA: Analise a conformidade do projeto acima com os parâmetros da zona {zona}.
        """
        
        return query

# UI Functions (otimizadas)
def configurar_pagina():
    """Configuração otimizada da página"""
    st.set_page_config(
        page_title="Assistente Regulatório v6.0",
        page_icon="[BUILD]",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # CSS customizado para aumentar largura da sidebar apenas em desktop
    st.markdown("""
    <style>
        /* Aumentar largura da sidebar para desktop (tela >= 768px) */
        @media (min-width: 768px) {
            .css-1d391kg {
                width: 400px !important;
            }
            .css-1outpf7 {
                padding-left: 420px !important;
            }
            section[data-testid="stSidebar"] > div {
                width: 400px !important;
            }
            section[data-testid="stSidebar"] {
                width: 400px !important;
                min-width: 400px !important;
            }
        }
        
        /* Manter responsividade para mobile (tela < 768px) */
        @media (max-width: 767px) {
            section[data-testid="stSidebar"] > div {
                width: 100% !important;
            }
            section[data-testid="stSidebar"] {
                width: 100% !important;
            }
        }
    </style>
    """, unsafe_allow_html=True)

@lru_cache(maxsize=10)
def get_cidades_disponiveis():
    """Cache das cidades disponíveis"""
    return [d.name for d in CONFIG.PASTA_DADOS_RAIZ.iterdir() if d.is_dir()]

def extrair_texto_pdf(arquivo):
    """Extração otimizada de PDF"""
    try:
        leitor = pypdf.PdfReader(arquivo)
        return "".join(pagina.extract_text() + "\n" for pagina in leitor.pages)
    except Exception as e:
        logger.error(f"Erro ao extrair PDF: {e}")
        raise ValueError("Erro ao processar o arquivo PDF")

def criar_formulario_estruturado():
    """Cria formulário estruturado para coleta de dados do projeto"""
    
    # Inicializar estado da sessão
    if 'dados_projeto' not in st.session_state:
        st.session_state.dados_projeto = {}
    
    # SOLUÇÃO GEMINI: Inicializar cidade com valor padrão PRIMEIRO
    cidade = "curitiba"  # Valor padrão sempre definido
    
    try:
        cidades = get_cidades_disponiveis()
        if not cidades:
            cidades = ["curitiba"]  # Fallback padrão
    except Exception as e:
        st.sidebar.error(f"Erro ao carregar cidades: {e}")
        cidades = ["curitiba"]  # Fallback em caso de erro
    
    # =============================================
    # SEÇÃO 1: Identificação do Projeto
    # =============================================
    st.sidebar.title("[BUILD] Assistente Regulamentação Civil")
    st.sidebar.header("[LOCATION] 1. Identificação do Projeto")
    
    # Obter cidade do selectbox de forma direta e simples
    cidade_selecionada = st.sidebar.selectbox(
        "Prefeitura:", 
        cidades,
        help="Selecione a prefeitura responsável pela análise"
    )
    
    # Usar cidade selecionada ou manter padrão
    if cidade_selecionada:
        cidade = cidade_selecionada
    
    endereco = st.sidebar.text_input(
        "Endereço Completo do Imóvel:",
        placeholder="Ex: Rua das Flores, 123, Centro, Curitiba-PR",
        help="Digite o endereço completo com logradouro, número, bairro e cidade"
    )
    
    inscricao_imobiliaria = st.sidebar.text_input(
        "Inscrição Imobiliária:",
        placeholder="Ex: 03000180090017",
        help="Digite o número da inscrição imobiliária do imóvel (opcional)"
    )
    
    # =============================================
    # SEÇÃO 2: Dados do Lote
    # =============================================
    st.sidebar.header("[MEASURE] 2. Dados do Lote")
    
    area_lote = st.sidebar.number_input(
        "Área Total do Lote (m²):",
        min_value=0.0,
        step=1.0,
        help="Área total do terreno em metros quadrados"
    )
    
    uso_pretendido = st.sidebar.selectbox(
        "Uso Pretendido da Edificação:",
        [
            "Selecione...",
            "Residencial Unifamiliar",
            "Residencial Multifamiliar",
            "Comercial",
            "Serviços",
            "Industrial",
            "Institucional",
            "Misto (Residencial + Comercial)",
            "Outros"
        ],
        help="Selecione o uso principal da edificação"
    )
    
    # =============================================
    # SEÇÃO 3: Restrições do Lote
    # =============================================
    st.sidebar.header("[RESTRICT] 3. Restrições do Lote")
    
    # APP - Área de Preservação Permanente
    possui_app = st.sidebar.checkbox(
        "Possui Área de Preservação Permanente (APP)?",
        help="Marque se o lote possui área de APP que não pode ser ocupada"
    )
    
    area_app = 0.0
    if possui_app:
        area_app = st.sidebar.number_input(
            "Área de APP (m²):",
            min_value=0.0,
            step=1.0,
            help="Área de preservação permanente em metros quadrados"
        )
    
    # Drenagem
    possui_drenagem = st.sidebar.checkbox(
        "Possui Área não Edificável de Drenagem?",
        help="Marque se o lote possui área reservada para drenagem urbana"
    )
    
    area_drenagem = 0.0
    if possui_drenagem:
        area_drenagem = st.sidebar.number_input(
            "Área de Drenagem (m²):",
            min_value=0.0,
            step=1.0,
            help="Área não edificável de drenagem em metros quadrados"
        )
    
    # =============================================
    # SEÇÃO 4: Parâmetros da Edificação Projetada
    # =============================================
    st.sidebar.header("[HOUSE] 4. Parâmetros da Edificação")
    
    area_projecao = st.sidebar.number_input(
        "Área da Projeção da Edificação (m²):",
        min_value=0.0,
        step=1.0,
        help="Área ocupada pela projeção horizontal da edificação"
    )
    
    area_construida = st.sidebar.number_input(
        "Área Construída Total (m²):",
        min_value=0.0,
        step=1.0,
        help="Somatório das áreas de todos os pavimentos"
    )
    
    altura_edificacao = st.sidebar.number_input(
        "Altura Total da Edificação (m):",
        min_value=0.0,
        step=0.1,
        help="Altura total da edificação em metros"
    )
    
    num_pavimentos = st.sidebar.number_input(
        "Número de Pavimentos:",
        min_value=1,
        step=1,
        help="Quantidade total de pavimentos da edificação"
    )
    
    # =============================================
    # SEÇÃO 5: Afastamentos (Recuos)
    # =============================================
    st.sidebar.header("[SPACING] 5. Afastamentos (Recuos)")
    
    recuo_frontal = st.sidebar.number_input(
        "Recuo Frontal (m):",
        min_value=0.0,
        step=0.1,
        help="Distância da edificação até a divisa frontal do lote"
    )
    
    recuo_lateral_dir = st.sidebar.number_input(
        "Recuo Lateral Direito (m):",
        min_value=0.0,
        step=0.1,
        help="Distância da edificação até a divisa lateral direita"
    )
    
    recuo_lateral_esq = st.sidebar.number_input(
        "Recuo Lateral Esquerdo (m):",
        min_value=0.0,
        step=0.1,
        help="Distância da edificação até a divisa lateral esquerda"
    )
    
    recuo_fundos = st.sidebar.number_input(
        "Recuo de Fundos (m):",
        min_value=0.0,
        step=0.1,
        help="Distância da edificação até a divisa de fundos"
    )
    
    # =============================================
    # SEÇÃO 6: Parâmetros Adicionais
    # =============================================
    st.sidebar.header("[ENVIRON] 6. Parâmetros Adicionais")
    
    area_permeavel = st.sidebar.number_input(
        "Área Permeável (m²):",
        min_value=0.0,
        step=1.0,
        help="Área do lote que permanece permeável (jardins, gramados, etc.)"
    )
    
    num_vagas = st.sidebar.number_input(
        "Número de Vagas de Estacionamento:",
        min_value=0,
        step=1,
        help="Quantidade de vagas de estacionamento previstas"
    )
    
    # =============================================
    # OPÇÕES AVANÇADAS
    # =============================================
    with st.sidebar.expander("[CONFIG] Opções Avançadas"):
        zona_manual = st.sidebar.text_input(
            "Zona Manual:",
            placeholder="Ex: ZR-4, ZCC.4",
            help="Informe a zona se conhecida (opcional)"
        )
        usar_zona_manual = st.sidebar.checkbox(
            "Usar zona informada manualmente",
            help="Marque para usar a zona informada ao invés da detecção automática"
        )
    
    # =============================================
    # VALIDAÇÕES E CÁLCULOS
    # =============================================
    
    # Verificar se pelo menos um campo principal está preenchido
    campos_principais = [
        endereco, area_lote > 0, uso_pretendido != "Selecione...", 
        area_projecao > 0, area_construida > 0, altura_edificacao > 0,
        inscricao_imobiliaria
    ]
    
    pelo_menos_um_campo = any(campo for campo in campos_principais)
    
    # Validações lógicas
    validacoes_ok = True
    mensagens_erro = []
    
    if area_lote > 0:
        if area_projecao > area_lote:
            validacoes_ok = False
            mensagens_erro.append("Área de projeção não pode ser maior que a área do lote")
        
        if (area_app + area_drenagem) > area_lote:
            validacoes_ok = False
            mensagens_erro.append("Soma das áreas de APP e drenagem não pode ser maior que a área do lote")
        
        if area_permeavel > area_lote:
            validacoes_ok = False
            mensagens_erro.append("Área permeável não pode ser maior que a área do lote")
    
    if area_construida < area_projecao and area_construida > 0:
        validacoes_ok = False
        mensagens_erro.append("Área construída total deve ser maior ou igual à área de projeção")
    
    # Cálculos automáticos
    taxa_ocupacao = 0.0
    coeficiente_aproveitamento = 0.0
    
    if area_lote > 0:
        taxa_ocupacao = (area_projecao / area_lote) * 100
        coeficiente_aproveitamento = area_construida / area_lote
    
    # Mostrar validações
    if mensagens_erro:
        for erro in mensagens_erro:
            st.sidebar.error(f"[WARNING] {erro}")
    
    # =============================================
    # BOTÃO DE ANÁLISE
    # =============================================
    st.sidebar.markdown("---")
    
    # Botão habilitado se pelo menos um campo estiver preenchido e sem erros críticos
    pode_analisar = pelo_menos_um_campo and validacoes_ok
    
    if not pode_analisar:
        if not pelo_menos_um_campo:
            st.sidebar.warning("[WARNING] Preencha pelo menos um campo para análise")
        elif not validacoes_ok:
            st.sidebar.warning("[WARNING] Corrija os erros de validação acima")
    
    analisar = st.sidebar.button(
        "[SEARCH] Analisar Conformidade",
        type="primary",
        use_container_width=True,
        disabled=not pode_analisar,
        help="Clique para iniciar a análise de conformidade urbanística"
    )
    
    # =============================================
    # INFORMAÇÕES DO SISTEMA
    # =============================================
    st.sidebar.markdown("---")
    st.sidebar.markdown("### [INFO] Cálculos Automáticos")
    
    if area_lote > 0:
        col1, col2 = st.sidebar.columns(2)
        col1.metric("Taxa de Ocupação", f"{taxa_ocupacao:.1f}%")
        col2.metric("Coef. Aproveitamento", f"{coeficiente_aproveitamento:.2f}")
    
    st.sidebar.info(f"""
    **Sistema:** v{CONFIG.VERSAO_APP}  
    **Cidade:** Curitiba  
    **Status:** [OK] Operacional
    """)
    
    # Validação final: se por algum motivo cidade ficou vazia, restaurar padrão
    if not cidade or cidade == "":
        cidade = "curitiba"
    
    # Retornar dados coletados
    return {
        'cidade': cidade,
        'endereco': endereco,
        'inscricao_imobiliaria': inscricao_imobiliaria,
        'area_lote': area_lote,
        'uso_pretendido': uso_pretendido,
        'possui_app': possui_app,
        'area_app': area_app,
        'possui_drenagem': possui_drenagem,
        'area_drenagem': area_drenagem,
        'area_projecao': area_projecao,
        'area_construida': area_construida,
        'altura_edificacao': altura_edificacao,
        'num_pavimentos': num_pavimentos,
        'recuo_frontal': recuo_frontal,
        'recuo_lateral_dir': recuo_lateral_dir,
        'recuo_lateral_esq': recuo_lateral_esq,
        'recuo_fundos': recuo_fundos,
        'area_permeavel': area_permeavel,
        'num_vagas': num_vagas,
        'zona_manual': zona_manual,
        'usar_zona_manual': usar_zona_manual,
        'taxa_ocupacao': taxa_ocupacao,
        'coeficiente_aproveitamento': coeficiente_aproveitamento,
        'pode_analisar': pode_analisar,
        'analisar': analisar
    }

def main():
    """Aplicação principal com formulário estruturado"""
    configurar_pagina()
    
    # Initialize engine
    if 'engine' not in st.session_state:
        st.session_state.engine = AnalysisEngine()
    
    if 'analysis_result' not in st.session_state:
        st.session_state.analysis_result = None
    
    # Criar formulário estruturado
    dados = criar_formulario_estruturado()
    
    # Processo de análise
    if dados['analisar']:
        # Criar memorial descritivo estruturado a partir dos dados (com tratamento de campos vazios)
        memorial = f"""
DADOS DO PROJETO URBANÍSTICO

1. IDENTIFICAÇÃO:
- Endereço: {dados['endereco'] if dados['endereco'] else 'NÃO INFORMADO'}
- Inscrição Imobiliária: {dados['inscricao_imobiliaria'] if dados['inscricao_imobiliaria'] else 'NÃO INFORMADA'}
- Uso Pretendido: {dados['uso_pretendido'] if dados['uso_pretendido'] != 'Selecione...' else 'NÃO INFORMADO'}

2. DADOS DO LOTE:
- Área Total: {dados['area_lote']:.2f} m² {('(NÃO INFORMADA)' if dados['area_lote'] == 0 else '')}
- Área de APP: {dados['area_app']:.2f} m² ({('SIM' if dados['possui_app'] else 'NÃO')})
- Área de Drenagem: {dados['area_drenagem']:.2f} m² ({('SIM' if dados['possui_drenagem'] else 'NÃO')})
- Área Permeável: {dados['area_permeavel']:.2f} m² {('(NÃO INFORMADA)' if dados['area_permeavel'] == 0 else '')}

3. PARÂMETROS DA EDIFICAÇÃO:
- Área de Projeção: {dados['area_projecao']:.2f} m² {('(NÃO INFORMADA)' if dados['area_projecao'] == 0 else '')}
- Área Construída Total: {dados['area_construida']:.2f} m² {('(NÃO INFORMADA)' if dados['area_construida'] == 0 else '')}
- Altura da Edificação: {dados['altura_edificacao']:.2f} m {('(NÃO INFORMADA)' if dados['altura_edificacao'] == 0 else '')}
- Número de Pavimentos: {dados['num_pavimentos']} {('(NÃO INFORMADO)' if dados['num_pavimentos'] == 1 else '')}
- Vagas de Estacionamento: {dados['num_vagas']} {('(NÃO INFORMADO)' if dados['num_vagas'] == 0 else '')}

4. AFASTAMENTOS (RECUOS):
- Recuo Frontal: {dados['recuo_frontal']:.2f} m {('(NÃO INFORMADO)' if dados['recuo_frontal'] == 0 else '')}
- Recuo Lateral Direito: {dados['recuo_lateral_dir']:.2f} m {('(NÃO INFORMADO)' if dados['recuo_lateral_dir'] == 0 else '')}
- Recuo Lateral Esquerdo: {dados['recuo_lateral_esq']:.2f} m {('(NÃO INFORMADO)' if dados['recuo_lateral_esq'] == 0 else '')}
- Recuo de Fundos: {dados['recuo_fundos']:.2f} m {('(NÃO INFORMADO)' if dados['recuo_fundos'] == 0 else '')}

5. ÍNDICES CALCULADOS:
- Taxa de Ocupação: {dados['taxa_ocupacao']:.2f}% {('(IMPOSSÍVEL CALCULAR - DADOS INSUFICIENTES)' if dados['area_lote'] == 0 else '')}
- Coeficiente de Aproveitamento: {dados['coeficiente_aproveitamento']:.2f} {('(IMPOSSÍVEL CALCULAR - DADOS INSUFICIENTES)' if dados['area_lote'] == 0 else '')}

OBSERVAÇÃO: Dados não informados serão considerados como FALTANTES na análise de conformidade.
"""
        
        # Executar análise
        try:
            # Validação adicional de segurança
            cidade_analise = dados.get('cidade', 'curitiba')
            if not cidade_analise or cidade_analise is None:
                cidade_analise = 'curitiba'
                
            with st.spinner("Executando análise de conformidade urbanística..."):
                resultado = st.session_state.engine.run_analysis(
                    cidade=cidade_analise,
                    endereco=dados['endereco'],
                    memorial=memorial,
                    zona_manual=dados['zona_manual'],
                    usar_zona_manual=dados['usar_zona_manual'],
                    inscricao=dados['inscricao_imobiliaria']
                )
                
                # Adicionar dados do formulário ao resultado
                resultado['dados_formulario'] = dados
                st.session_state.analysis_result = resultado
                st.rerun()
                
        except Exception as e:
            st.error(f"[ERROR] Erro na análise: {str(e)}")
            logger.error(f"Erro completo: {e}", exc_info=True)
    
    # Exibir resultados
    if st.session_state.analysis_result:
        resultado = st.session_state.analysis_result
        
        # Header com status aprimorado
        zona_display = resultado.get('zona_info', resultado['zona'])
        st.header(f"[REPORT] Relatório: Zona {zona_display}")
        
        # Mostrar informações de detecção se disponível
        if 'zona_detection_details' in resultado:
            with st.expander("[SEARCH] Informações da Detecção de Zona", expanded=False):
                st.info(resultado['zona_detection_details'])
                
                # Mostrar coordenadas se disponível (buscar no log)
                if "Coordenadas GPS" in resultado['zona_detection_details']:
                    st.success("[OK] **Detecção Oficial:** Zona identificada com precisão geográfica usando sistema GIS profissional")
                elif "análise textual" in resultado['zona_detection_details'].lower():
                    st.warning("[WARNING] **Zona Estimada:** Baseada em análise textual do endereço")
                elif "padrão" in resultado['zona_detection_details'].lower():
                    st.info("[REFRESH] **Zona Padrão:** Sistema utilizou zona residencial padrão para análise")
                elif "manual" in resultado['zona_detection_details'].lower():
                    st.success("[OK] **Zona Manual:** Informada pelo usuário")
        
        parecer = resultado['resultado']
        if "não conformidade" in parecer.lower() or "reprovado" in parecer.lower():
            st.error("[ERROR] **Projeto REPROVADO**")
        elif "conformidade" in parecer.lower() or "aprovado" in parecer.lower():
            st.success("[OK] **Projeto APROVADO**")
        else:
            st.warning("[WARNING] **Análise Pendente**")
        
        # Tabs do resultado
        tab1, tab2, tab3 = st.tabs(["[CHART] Relatório", "[DOCS] Documentos", "[DEBUG] Debug"])
        
        with tab1:
            st.markdown(resultado['resultado'])
            
            # Downloads
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    "[DOWNLOAD] Download TXT",
                    resultado['resultado'],
                    f"relatorio_{resultado['zona']}.txt",
                    "text/plain"
                )
            with col2:
                if st.button("[REFRESH] Nova Análise"):
                    st.session_state.analysis_result = None
                    st.rerun()
        
        with tab2:
            st.subheader("Documentos Consultados")
            for i, doc in enumerate(resultado['documentos']):
                with st.expander(f"Documento {i+1}: {doc.metadata.get('fonte', 'N/A')}"):
                    st.text_area("Conteúdo", doc.page_content, height=200, key=f"doc_{i}")
        
        with tab3:
            st.json(resultado['parametros'])
            st.json(resultado['info_projeto'])
    
    else:
        # Welcome page
        st.title("[BUILD] Assistente Regulatório v6.0")
        st.markdown("### Análise inteligente de conformidade urbanística")
        st.markdown("---")
        st.info("[REPORT] Configure a análise na barra lateral para começar")
        
        # Info compacta
        cidade = dados.get('cidade', '')
        if cidade and (CONFIG.PASTA_DADOS_RAIZ / cidade.lower()).exists():
            st.markdown("---")
            st.markdown(f"[CHART] {cidade.title()} • v{CONFIG.VERSAO_APP} • [OK] Ativo")

if __name__ == "__main__":
    load_dotenv()
    main()