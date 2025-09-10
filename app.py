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

# SOLUÇÃO DEFINITIVA LAYER 36 - ZONEAMENTO LEI 15.511/2019
from geocuritiba_layer36_solution import detect_zone_professional

from zoneamento_integration import enhanced_zone_lookup
from zoneamento_curitiba import DetectorZoneamento
from geocuritiba_integration import GeoCuritibaAPI, integrar_geocuritiba_app

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

# Instância global do detector de zoneamento
detector_zoneamento = DetectorZoneamento()

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

@dataclass
class ParameterLimit:
    """Representa um limite de parâmetro com min/max"""
    name: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    unit: str = ""
    
    def validate(self, project_value: float) -> Tuple[bool, str]:
        """Valida se valor do projeto está dentro dos limites"""
        errors = []
        
        if self.min_value is not None and project_value < self.min_value:
            errors.append(f"Valor abaixo do mínimo ({self.min_value}{self.unit})")
        
        if self.max_value is not None and project_value > self.max_value:
            errors.append(f"Valor acima do máximo ({self.max_value}{self.unit})")
        
        is_conform = len(errors) == 0
        observation = " | ".join(errors) if errors else "Dentro dos limites"
        
        return is_conform, observation
    
    def get_limit_display(self) -> str:
        """Retorna string formatada do limite para exibição"""
        if self.min_value is not None and self.max_value is not None:
            return f"{self.min_value}{self.unit} a {self.max_value}{self.unit}"
        elif self.min_value is not None:
            return f"Mín: {self.min_value}{self.unit}"
        elif self.max_value is not None:
            return f"Máx: {self.max_value}{self.unit}"
        else:
            return "Não especificado"

class HeightConverter:
    """Conversor inteligente entre metros e pavimentos"""
    
    # Padrões típicos de altura por pavimento
    ALTURA_PADRAO_PAVIMENTO = 3.0  # metros (conforme prática de mercado)
    ALTURA_MINIMA_PAVIMENTO = 2.4  # metros (mínimo legal típico)
    ALTURA_MAXIMA_PAVIMENTO = 4.0  # metros (máximo razoável)
    
    @staticmethod
    def metros_para_pavimentos(metros: float, altura_pav: float = None) -> float:
        """Converte metros para número de pavimentos"""
        altura_ref = altura_pav or HeightConverter.ALTURA_PADRAO_PAVIMENTO
        return metros / altura_ref
    
    @staticmethod
    def pavimentos_para_metros(pavimentos: float, altura_pav: float = None) -> float:
        """Converte pavimentos para metros"""
        altura_ref = altura_pav or HeightConverter.ALTURA_PADRAO_PAVIMENTO
        return pavimentos * altura_ref
    
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
        # Padrões existentes (gerais) - por padrão tratados como máximos
        "taxa_ocupacao": re.compile(r"taxa\s+de\s+ocupa[çc][ãa]o\s*(?:máxima)?[:\s]*(\d+[.,]?\d*)\s*%", re.IGNORECASE),
        "coeficiente_aproveitamento": re.compile(r"coeficiente\s+de\s+aproveitamento\s*(?:máximo)?[:\s]*(\d+[.,]?\d*)", re.IGNORECASE),
        "altura_edificacao": re.compile(r"altura\s+(?:da\s+edificação|máxima)[:\s]*(\d+[.,]?\d*)\s*m", re.IGNORECASE),
        "recuo_frontal": re.compile(r"recuo\s+frontal[:\s]*(\d+[.,]?\d*)\s*m", re.IGNORECASE),
        "recuos_laterais": re.compile(r"recuos?\s+laterais?[:\s]*(\d+[.,]?\d*)\s*m", re.IGNORECASE),
        "recuo_fundos": re.compile(r"recuos?\s+(?:de\s+)?fundos?[:\s]*(\d+[.,]?\d*)\s*m", re.IGNORECASE),
        "area_permeavel": re.compile(r"[áa]rea\s+perm[eé][aá]vel[:\s]*(\d+[.,]?\d*)\s*%", re.IGNORECASE),
        
        # NOVOS PADRÕES para valores mínimos
        "taxa_ocupacao_min": re.compile(r"taxa\s+de\s+ocupa[çc][ãa]o\s+mínima[:\s]*(\d+[.,]?\d*)\s*%", re.IGNORECASE),
        "coeficiente_aproveitamento_min": re.compile(r"coeficiente\s+de\s+aproveitamento\s+mínimo[:\s]*(\d+[.,]?\d*)", re.IGNORECASE),
        "altura_edificacao_min": re.compile(r"altura\s+mínima[:\s]*(\d+[.,]?\d*)\s*m", re.IGNORECASE),
        "recuo_frontal_min": re.compile(r"recuo\s+frontal\s+mínimo[:\s]*(\d+[.,]?\d*)\s*m", re.IGNORECASE),
        "recuos_laterais_min": re.compile(r"recuos?\s+laterais?\s+mínimo[s]?[:\s]*(\d+[.,]?\d*)\s*m", re.IGNORECASE),
        "recuo_fundos_min": re.compile(r"recuos?\s+(?:de\s+)?fundos?\s+mínimo[:\s]*(\d+[.,]?\d*)\s*m", re.IGNORECASE),
        "area_permeavel_min": re.compile(r"[áa]rea\s+perm[eé][aá]vel\s+mínima[:\s]*(\d+[.,]?\d*)\s*%", re.IGNORECASE),
        
        # NOVOS PADRÕES para valores máximos (explícitos)
        "taxa_ocupacao_max": re.compile(r"taxa\s+de\s+ocupa[çc][ãa]o\s+máxima[:\s]*(\d+[.,]?\d*)\s*%", re.IGNORECASE),
        "coeficiente_aproveitamento_max": re.compile(r"coeficiente\s+de\s+aproveitamento\s+máximo[:\s]*(\d+[.,]?\d*)", re.IGNORECASE),
        "altura_edificacao_max": re.compile(r"altura\s+máxima[:\s]*(\d+[.,]?\d*)\s*m", re.IGNORECASE),
        "recuo_frontal_max": re.compile(r"recuo\s+frontal\s+máximo[:\s]*(\d+[.,]?\d*)\s*m", re.IGNORECASE),
        "recuos_laterais_max": re.compile(r"recuos?\s+laterais?\s+máximo[s]?[:\s]*(\d+[.,]?\d*)\s*m", re.IGNORECASE),
        "recuo_fundos_max": re.compile(r"recuos?\s+(?:de\s+)?fundos?\s+máximo[:\s]*(\d+[.,]?\d*)\s*m", re.IGNORECASE),
        "area_permeavel_max": re.compile(r"[áa]rea\s+perm[eé][aá]vel\s+máxima[:\s]*(\d+[.,]?\d*)\s*%", re.IGNORECASE),
        
        # Padrões para faixas (ex: "entre X e Y", "de X a Y")
        "taxa_ocupacao_faixa": re.compile(r"taxa\s+de\s+ocupa[çc][ãa]o\s+(?:entre|de)\s+(\d+[.,]?\d*)\s*%?\s+(?:e|a|até)\s+(\d+[.,]?\d*)\s*%", re.IGNORECASE),
        "coeficiente_aproveitamento_faixa": re.compile(r"coeficiente\s+de\s+aproveitamento\s+(?:entre|de)\s+(\d+[.,]?\d*)\s+(?:e|a|até)\s+(\d+[.,]?\d*)", re.IGNORECASE),
        "altura_edificacao_faixa": re.compile(r"altura\s+(?:entre|de)\s+(\d+[.,]?\d*)\s*m?\s+(?:e|a|até)\s+(\d+[.,]?\d*)\s*m", re.IGNORECASE),
        "area_permeavel_faixa": re.compile(r"[áa]rea\s+perm[eé][aá]vel\s+(?:entre|de)\s+(\d+[.,]?\d*)\s*%?\s+(?:e|a|até)\s+(\d+[.,]?\d*)\s*%", re.IGNORECASE),
        
        # NOVOS PADRÕES específicos para dados de Curitiba encontrados no Excel
        
        # Padrões especiais para taxa de ocupação com exceções
        "taxa_ocupacao_com_excecao": re.compile(r"(\d+)%\s*\(.*?(\d+)%.*?(lote|menor)", re.IGNORECASE),
        
        # Padrões específicos encontrados nos dados oficiais
        "taxa_ocupacao_embasamento": re.compile(r"(\d+)%\s*\(.*?(\d+)%.*?embasamento", re.IGNORECASE),
        "taxa_ocupacao_subsolo_terreo": re.compile(r"(\d+)%\s*\(subsolo.*?t[eé]rreo.*?2.*?\).*?(\d+)%.*?demais", re.IGNORECASE),
        "taxa_ocupacao_faixa_historica": re.compile(r"(\d+)[-–](\d+)%", re.IGNORECASE),
        "taxa_ocupacao_multiplos_pavimentos": re.compile(r"(\d+)%.*?\(.*?(\d+)%.*?(subsolo|t[eé]rreo|pavimento)", re.IGNORECASE),
        
        # Padrões para zonas especiais
        "norma_propria": re.compile(r"definido\s+por\s+norma\s+pr[óo]pria", re.IGNORECASE),
        "ate_100_embasamento": re.compile(r"at[eé]\s+100%.*?embasamento", re.IGNORECASE),
        "ate_100_no_embasamento": re.compile(r"at[eé]\s+100%\s+no\s+embasamento", re.IGNORECASE),
        
        # Padrões para altura em pavimentos específicos
        "altura_pavimentos": re.compile(r"(?:até\s+)?(\d+)\s+pav", re.IGNORECASE),
        "altura_pavimentos_max": re.compile(r"até\s+(\d+)\s+pav", re.IGNORECASE),
        "altura_pavimentos_excecao": re.compile(r"(\d+)\s+pav.*?(\d+)\s+pav.*?(frente|enc|arterial)", re.IGNORECASE),
        
        # Padrões para "conforme quadro" e referências
        "conforme_quadro": re.compile(r"conforme\s+quadro", re.IGNORECASE),
        "quadro_proprio": re.compile(r"quadro\s+pr[óo]prio", re.IGNORECASE),
        
        # Padrões para altura livre e alta verticalização
        "altura_livre": re.compile(r"altura\s+livre", re.IGNORECASE),
        "alta_verticalizacao": re.compile(r"alta\s+verticaliza[çc][ãa]o", re.IGNORECASE),
        
        # Padrões para afastamentos especiais (H/6, H/5, etc.)
        "afastamento_h_formula": re.compile(r"H/(\d+)", re.IGNORECASE),
        
        # Padrões para usos mistos e especiais
        "uso_misto": re.compile(r"uso\s+misto", re.IGNORECASE),
        "comercio_servico": re.compile(r"com[eé]rcio.*?servi[çc]o", re.IGNORECASE),
        "habitacao_unifamiliar": re.compile(r"habita[çc][ãa]o\s+unifamiliar", re.IGNORECASE),
        "habitacao_coletiva": re.compile(r"habita[çc][ãa]o\s+coletiva", re.IGNORECASE),
        
        # Padrões para lotes especiais
        "lote_dimensoes": re.compile(r"(\d+(?:[.,]\d+)?)\s*m?\s*x\s*(\d+(?:[.,]\d+)?)\s*m", re.IGNORECASE),
        
        # Padrões para porte em m²
        "porte_m2": re.compile(r"(\d+(?:[.,]\d+)?)\s*m[²2]", re.IGNORECASE),
        "porte_m2_comercio": re.compile(r"(\d+(?:[.,]\d+)?)\s*m[²2].*?(com[eé]rcio|servi[çc]o)", re.IGNORECASE),
        
        # Padrões para densidade
        "media_densidade": re.compile(r"m[eé]dia\s+densidade", re.IGNORECASE),
        "baixa_densidade": re.compile(r"baixa\s+densidade", re.IGNORECASE),
        "alta_densidade": re.compile(r"alta\s+densidade", re.IGNORECASE),
    }
    
    @classmethod
    def extract(cls, texto: str) -> Dict[str, Optional[float]]:
        parametros = {}
        
        for param, pattern in cls.PATTERNS.items():
            match = pattern.search(texto)
            if match:
                try:
                    # Tratamento especial para padrões de faixa (têm 2 grupos)
                    if "_faixa" in param:
                        valor_min = float(match.group(1).replace(',', '.'))
                        valor_max = float(match.group(2).replace(',', '.'))
                        
                        # Extrair nome base do parâmetro
                        base_param = param.replace("_faixa", "")
                        
                        # Definir valores min e max
                        parametros[f"{base_param}_min"] = valor_min
                        parametros[f"{base_param}_max"] = valor_max
                        parametros[f"{base_param}_faixa_detectada"] = True
                        
                    else:
                        # Padrões normais (1 grupo)
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
                if "_faixa" not in param:  # Só define None para padrões não-faixa
                    parametros[param] = None
        
        return parametros

class ParameterLimitExtractor:
    """Extrai limites min/max dos documentos"""
    
    @staticmethod
    def extract_limits(text: str) -> Dict[str, ParameterLimit]:
        """Extrai todos os limites de parâmetros do texto"""
        limits = {}
        
        # Taxa de Ocupação
        limits['taxa_ocupacao'] = ParameterLimitExtractor._extract_parameter_limit(
            text, 'taxa_ocupacao', '%'
        )
        
        # Coeficiente de Aproveitamento  
        limits['coeficiente_aproveitamento'] = ParameterLimitExtractor._extract_parameter_limit(
            text, 'coeficiente_aproveitamento', ''
        )
        
        # Área Permeável
        limits['area_permeavel'] = ParameterLimitExtractor._extract_parameter_limit(
            text, 'area_permeavel', '%'
        )
        
        # Altura da Edificação
        limits['altura_edificacao'] = ParameterLimitExtractor._extract_parameter_limit(
            text, 'altura_edificacao', 'm'
        )
        
        # Recuo Frontal
        limits['recuo_frontal'] = ParameterLimitExtractor._extract_parameter_limit(
            text, 'recuo_frontal', 'm'
        )
        
        # Recuos Laterais
        limits['recuos_laterais'] = ParameterLimitExtractor._extract_parameter_limit(
            text, 'recuos_laterais', 'm'
        )
        
        # Recuo de Fundos
        limits['recuo_fundos'] = ParameterLimitExtractor._extract_parameter_limit(
            text, 'recuo_fundos', 'm'
        )
        
        return limits
    
    @staticmethod
    def _extract_parameter_limit(text: str, param_name: str, unit: str) -> ParameterLimit:
        """Extrai limite min/max de um parâmetro específico"""
        # Extrair parâmetros do texto
        parametros = ParameterExtractor.extract(text)
        
        # Buscar valores min e max específicos
        min_key = f"{param_name}_min"
        max_key = f"{param_name}_max"
        
        min_val = parametros.get(min_key)
        max_val = parametros.get(max_key)
        
        # Se não encontrou min/max específicos, usar padrão geral
        if min_val is None and max_val is None:
            general_val = parametros.get(param_name)
            if general_val is not None:
                max_val = general_val  # Por padrão, valor geral é tratado como máximo
        
        return ParameterLimit(
            name=param_name,
            min_value=min_val,
            max_value=max_val,
            unit=unit
        )

class ZoneDataManager:
    """Gerenciador de dados oficiais de zoneamento"""
    
    def __init__(self, json_file_path: str = None, ocupacao_file_path: str = None):
        self.json_file_path = json_file_path or "zoneamento_curitiba_completo.json"
        self.ocupacao_file_path = ocupacao_file_path or "taxa_ocupacao_detalhada.json"
        self.zones_data = self._load_zones_data()
        self.ocupacao_data = self._load_ocupacao_data()
    
    def _load_zones_data(self) -> Dict[str, Any]:
        """Carrega dados de zoneamento do arquivo JSON"""
        try:
            if not pathlib.Path(self.json_file_path).exists():
                logger.warning(f"Arquivo {self.json_file_path} não encontrado")
                return {}
            
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Erro ao carregar dados de zoneamento: {e}")
            return {}
    
    def _load_ocupacao_data(self) -> Dict[str, Any]:
        """Carrega dados detalhados de taxa de ocupação"""
        try:
            if not pathlib.Path(self.ocupacao_file_path).exists():
                logger.warning(f"Arquivo {self.ocupacao_file_path} não encontrado")
                return {}
            
            with open(self.ocupacao_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Erro ao carregar dados de ocupação: {e}")
            return {}
    
    def get_zone_data(self, zona_name: str) -> Dict[str, Any]:
        """Obtém dados oficiais de uma zona específica, incorporando dados de ocupação detalhados"""
        # Normalizar nome da zona para busca
        zona_normalized = self._normalize_zone_name(zona_name)
        
        # Busca direta nos dados principais
        zone_data = {}
        if zona_normalized in self.zones_data:
            zone_data = self.zones_data[zona_normalized].copy()
        else:
            # Busca por variações
            for zone_key in self.zones_data.keys():
                if self._zones_match(zona_normalized, zone_key):
                    zone_data = self.zones_data[zone_key].copy()
                    break
        
        # Incorporar dados detalhados de taxa de ocupação se disponíveis
        ocupacao_detalhada = self.get_ocupacao_data(zona_normalized)
        if ocupacao_detalhada:
            # Substituir dados básicos de TO pelos dados detalhados
            zone_data['taxa_ocupacao_detalhada'] = ocupacao_detalhada['taxa_ocupacao']
            zone_data['grupo_ocupacao'] = ocupacao_detalhada.get('grupo', '')
            zone_data['observacoes_ocupacao'] = ocupacao_detalhada.get('observacoes', [])
            
            # Atualizar dados básicos de taxa de ocupação
            if 'taxa_ocupacao' in zone_data:
                # Manter estrutura original mas adicionar dados enriquecidos
                zone_data['taxa_ocupacao']['dados_detalhados'] = ocupacao_detalhada['taxa_ocupacao']
        
        return zone_data
    
    def get_ocupacao_data(self, zona_name: str) -> Dict[str, Any]:
        """Obtém dados detalhados de taxa de ocupação para uma zona"""
        zona_normalized = self._normalize_zone_name(zona_name)
        
        # Busca direta
        if zona_normalized in self.ocupacao_data:
            return self.ocupacao_data[zona_normalized]
        
        # Busca por variações
        for zone_key in self.ocupacao_data.keys():
            if self._zones_match(zona_normalized, zone_key):
                return self.ocupacao_data[zone_key]
        
        return {}
    
    def _normalize_zone_name(self, zona_name: str) -> str:
        """Normaliza nome da zona para busca"""
        if not zona_name:
            return ""
        
        # Remover espaços e converter para maiúsculo
        normalized = zona_name.upper().strip()
        
        # Variações conhecidas
        zone_mappings = {
            'ZCC.4': 'ZCC',
            'ZR1': 'ZR-1', 'ZR2': 'ZR-2', 'ZR3': 'ZR-3', 'ZR4': 'ZR-4',
            'ZS1': 'ZS-1', 'ZS2': 'ZS-2',
            'ZUM1': 'ZUM-1', 'ZUM2': 'ZUM-2', 'ZUM3': 'ZUM-3',
            'ECO1': 'ECO-1', 'ECO2': 'ECO-2', 'ECO3': 'ECO-3', 'ECO4': 'ECO-4',
            'ZH1': 'ZH-1', 'ZH2': 'ZH-2'
        }
        
        return zone_mappings.get(normalized, normalized)
    
    def _zones_match(self, zona1: str, zona2: str) -> bool:
        """Verifica se duas zonas são equivalentes"""
        return (zona1 == zona2 or 
                zona1.replace('-', '') == zona2.replace('-', '') or
                zona1.replace('.', '') == zona2.replace('.', ''))
    
    def get_parameter_limits(self, zona_name: str) -> Dict[str, ParameterLimit]:
        """Converte dados oficiais em objetos ParameterLimit"""
        zone_data = self.get_zone_data(zona_name)
        if not zone_data:
            return {}
        
        limits = {}
        
        # Taxa de Ocupação - usar dados detalhados se disponíveis
        if 'taxa_ocupacao_detalhada' in zone_data:
            ocupacao_detalhada = zone_data['taxa_ocupacao_detalhada']
            
            if ocupacao_detalhada['tipo'] == 'simples':
                # Valor simples (ex: 50%)
                limits['taxa_ocupacao'] = ParameterLimit(
                    name='taxa_ocupacao',
                    min_value=None,
                    max_value=ocupacao_detalhada['base'],
                    unit='%'
                )
            elif ocupacao_detalhada['tipo'] == 'faixa':
                # Faixa de valores (ex: 30-50%)
                base_data = ocupacao_detalhada['base']
                limits['taxa_ocupacao'] = ParameterLimit(
                    name='taxa_ocupacao',
                    min_value=base_data['min'],
                    max_value=base_data['max'],
                    unit='%'
                )
            elif ocupacao_detalhada['tipo'] == 'base_com_excecao':
                # Base com exceção (ex: 50% até 100% no embasamento)
                limits['taxa_ocupacao'] = ParameterLimit(
                    name='taxa_ocupacao',
                    min_value=None,
                    max_value=ocupacao_detalhada['base'],
                    unit='%'
                )
                # Criar limite adicional para exceção
                for excecao in ocupacao_detalhada['excecoes']:
                    if excecao['tipo'] == 'embasamento':
                        limits['taxa_ocupacao_embasamento'] = ParameterLimit(
                            name='taxa_ocupacao_embasamento',
                            min_value=None,
                            max_value=excecao['valor'],
                            unit='%'
                        )
            elif ocupacao_detalhada['tipo'] == 'multiplos_valores':
                # Múltiplos valores por pavimento (ex: ZC Central)
                limits['taxa_ocupacao'] = ParameterLimit(
                    name='taxa_ocupacao',
                    min_value=None,
                    max_value=ocupacao_detalhada['base'],  # Valor para demais pavimentos
                    unit='%'
                )
                # Criar limite para pavimentos especiais
                for excecao in ocupacao_detalhada['excecoes']:
                    if excecao['tipo'] == 'pavimentos_especificos':
                        limits['taxa_ocupacao_especial'] = ParameterLimit(
                            name='taxa_ocupacao_especial',
                            min_value=None,
                            max_value=excecao['valor'],
                            unit='%'
                        )
        elif 'taxa_ocupacao' in zone_data and zone_data['taxa_ocupacao']['limits']:
            # Fallback para dados básicos se detalhados não disponíveis
            limits_data = zone_data['taxa_ocupacao']['limits']
            limits['taxa_ocupacao'] = ParameterLimit(
                name='taxa_ocupacao',
                min_value=limits_data.get('min'),
                max_value=limits_data.get('max'),
                unit='%'
            )
        
        # Coeficiente de Aproveitamento
        if 'coeficiente_aproveitamento' in zone_data and zone_data['coeficiente_aproveitamento']['limits']:
            limits_data = zone_data['coeficiente_aproveitamento']['limits']
            limits['coeficiente_aproveitamento'] = ParameterLimit(
                name='coeficiente_aproveitamento',
                min_value=limits_data.get('min'),
                max_value=limits_data.get('max'),
                unit=''
            )
        
        # Altura/Pavimentos
        if 'altura_pavimentos' in zone_data and zone_data['altura_pavimentos']['limits']:
            limits_data = zone_data['altura_pavimentos']['limits']
            limits['altura_edificacao'] = ParameterLimit(
                name='altura_edificacao',
                min_value=limits_data.get('min'),
                max_value=limits_data.get('max'),
                unit='pav'
            )
        
        # Taxa Permeável
        if 'taxa_permeavel' in zone_data and zone_data['taxa_permeavel']['limits']:
            limits_data = zone_data['taxa_permeavel']['limits']
            limits['area_permeavel'] = ParameterLimit(
                name='area_permeavel',
                min_value=limits_data.get('min'),
                max_value=limits_data.get('max'),
                unit='%'
            )
        
        # Recuo Frontal
        if 'recuo_frontal' in zone_data and zone_data['recuo_frontal']['limits']:
            limits_data = zone_data['recuo_frontal']['limits']
            limits['recuo_frontal'] = ParameterLimit(
                name='recuo_frontal',
                min_value=limits_data.get('min'),
                max_value=limits_data.get('max'),
                unit='m'
            )
        
        return limits
    
    def get_zone_summary(self, zona_name: str) -> str:
        """Gera resumo estruturado dos parâmetros da zona"""
        zone_data = self.get_zone_data(zona_name)
        if not zone_data:
            return f"Dados não encontrados para a zona {zona_name}"
        
        zona_nome = zone_data.get('zona_oficial', zona_name)
        summary_parts = [f"ZONA {zona_nome}:"]
        
        # Taxa de Ocupação - usar dados detalhados se disponíveis
        if 'taxa_ocupacao_detalhada' in zone_data:
            ocupacao = zone_data['taxa_ocupacao_detalhada']
            taxa_texto = self._format_ocupacao_display(ocupacao)
            summary_parts.append(f"- Taxa de Ocupação: {taxa_texto}")
            
            # Adicionar observações específicas de ocupação
            if zone_data.get('observacoes_ocupacao'):
                for obs in zone_data['observacoes_ocupacao']:
                    summary_parts.append(f"  • {obs}")
        else:
            # Fallback para dados básicos
            if 'taxa_ocupacao' in zone_data and zone_data['taxa_ocupacao']['valor']:
                summary_parts.append(f"- Taxa de Ocupação: {zone_data['taxa_ocupacao']['valor']}")
        
        # Outros parâmetros principais
        params = [
            ('Coeficiente de Aproveitamento', 'coeficiente_aproveitamento'),
            ('Altura/Pavimentos', 'altura_pavimentos'),
            ('Taxa Permeável', 'taxa_permeavel'),
            ('Recuo Frontal', 'recuo_frontal')
        ]
        
        for param_name, param_key in params:
            if param_key in zone_data and zone_data[param_key]['valor']:
                summary_parts.append(f"- {param_name}: {zone_data[param_key]['valor']}")
        
        # Informações adicionais
        if zone_data.get('grupo_ocupacao'):
            summary_parts.append(f"- Grupo: {zone_data['grupo_ocupacao']}")
            
        if zone_data.get('usos_permitidos'):
            summary_parts.append(f"- Usos Permitidos: {zone_data['usos_permitidos']}")
        
        if zone_data.get('notas_tecnicas'):
            summary_parts.append(f"- Notas Técnicas: {zone_data['notas_tecnicas']}")
        
        return "\n".join(summary_parts)
    
    def _format_ocupacao_display(self, ocupacao_data: Dict[str, Any]) -> str:
        """Formata dados de ocupação para exibição legível"""
        if ocupacao_data['tipo'] == 'simples':
            return f"{ocupacao_data['base']}%"
        
        elif ocupacao_data['tipo'] == 'faixa':
            base = ocupacao_data['base']
            return f"{base['min']}% a {base['max']}%"
        
        elif ocupacao_data['tipo'] == 'base_com_excecao':
            texto = f"{ocupacao_data['base']}%"
            for excecao in ocupacao_data['excecoes']:
                if excecao['tipo'] == 'embasamento':
                    texto += f" (até {excecao['valor']}% {excecao['condicao']})"
            return texto
        
        elif ocupacao_data['tipo'] == 'multiplos_valores':
            texto = f"{ocupacao_data['base']}% demais pavimentos"
            for excecao in ocupacao_data['excecoes']:
                if excecao['tipo'] == 'pavimentos_especificos':
                    texto += f"; {excecao['valor']}% ({excecao['condicao']})"
            return texto
        
        elif ocupacao_data['tipo'] == 'norma_propria':
            return "Definido por norma própria"
        
        else:
            return ocupacao_data.get('original', 'N/A')
    
    def get_available_zones(self) -> List[str]:
        """Retorna lista de zonas disponíveis"""
        return list(self.zones_data.keys())

# Instância global do gerenciador de dados de zona
zone_data_manager = ZoneDataManager()

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
    2. Identifique os limites da legislação nos documentos de contexto - ATENÇÃO aos valores mínimos E máximos
    3. Compare numericamente cada parâmetro considerando faixas de valores
    4. IMPORTANTE - Para ALTURA DA EDIFICAÇÃO: Se a legislação especifica limite em pavimentos e o projeto em metros (ou vice-versa), use a conversão: 1 pavimento = 3,0 metros (padrão técnico)
    5. Use APENAS "✅ Conforme" ou "❌ Não Conforme" na coluna Conformidade
    6. Seja CONCLUSIVO no parecer final sobre aprovação/reprovação
    7. Na coluna "Observação" para altura, sempre explicite a conversão feita (ex: "8,5m = 2,8 pavimentos")
    8. IMPORTANTE - Para cada parâmetro, identifique se a legislação estabelece:
       - APENAS valor máximo (ex: "taxa de ocupação máxima: 50%")
       - APENAS valor mínimo (ex: "área permeável mínima: 20%") 
       - AMBOS min e máx (ex: "coeficiente entre 0,5 e 2,0")
    9. Na validação, considere:
       - Valor ACIMA do máximo = ❌ Não Conforme
       - Valor ABAIXO do mínimo = ❌ Não Conforme
       - Valor dentro da faixa = ✅ Conforme
    
    FORMATO OBRIGATÓRIO:
    
    ## 1. Identificação do Projeto
    - **Endereço:** [endereço]
    - **Zona de Uso:** [zona]
    - **Data da Análise:** {data_analise}
    
    ## 2. Análise dos Parâmetros
    
    | Parâmetro | Valor no Projeto | Limite da Legislação | Conformidade | Observação |
    |---|---|---|---|---|
    | Taxa de Ocupação | [valor]% | [limite] | ✅/❌ | [obs] |
    | Coeficiente de Aproveitamento | [valor] | [limite] | ✅/❌ | [obs] |
    | Altura da Edificação | [valor]m | [limite] | ✅/❌ | [obs] |
    | Recuo Frontal | [valor]m | [limite] | ✅/❌ | [obs] |
    | Recuos Laterais | [valor]m | [limite] | ✅/❌ | [obs] |
    | Recuo de Fundos | [valor]m | [limite] | ✅/❌ | [obs] |
    | Área Permeável | [valor]% | [limite] | ✅/❌ | [obs] |
    
    FORMATO DA COLUNA "Limite da Legislação":
    - "Máx: 50%" (apenas máximo)
    - "Mín: 20%" (apenas mínimo)  
    - "0,5 a 2,0" (faixa completa)
    - "Não especificado" (se não encontrar)
    
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
    
    def run_analysis(self, cidade: str, endereco: str, memorial: str, 
                     zona_manual: Optional[str] = None, usar_zona_manual: bool = False,
                     parametros_avancados: dict = None, dados_formulario: dict = None) -> Dict[str, Any]:
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
                # Usar sistema GIS profissional com LAYER 36 - LEI 15.511/2019
                inscricao = dados_formulario.get('inscricao_imobiliaria', '') if dados_formulario else ''
                detection_result = detect_zone_professional(endereco or "", inscricao)
                zona = detection_result.zona
                
                # Criar informações detalhadas da detecção
                if detection_result.confidence == "OFICIAL":
                    zona_info = f"{zona} (DETECTADA AUTOMATICAMENTE)"
                    detection_details = f"Zona detectada oficialmente via {detection_result.source}: {detection_result.details}"
                elif detection_result.confidence == "ESTIMADA":
                    zona_info = f"{zona} (ZONA ESTIMADA)"
                    detection_details = f"Zona estimada via {detection_result.source}: {detection_result.details}"
                else:
                    zona_info = f"{zona} (ZONA PADRÃO)"
                    detection_details = f"Zona padrão utilizada: {detection_result.details}"
                
                print(f"DEBUG GIS - Zona detectada: {zona} | Confiança: {detection_result.confidence} | Fonte: {detection_result.source}")
                if detection_result.coordinates:
                    print(f"DEBUG GIS - Coordenadas: {detection_result.coordinates}")
                    
                # Mostrar informação compacta de detecção
                st.info(f"🎯 **Zona detectada**: {zona} via {detection_result.source} (confiança: {detection_result.confidence})")
            
            # Salvar informações de detecção para uso posterior
            zona_detection_info = zona_info
            zona_detection_details = detection_details
            
            # Enriquecer com parâmetros oficiais de zoneamento usando ZoneDataManager
            zone_data = zone_data_manager.get_zone_data(zona)
            zone_limits = zone_data_manager.get_parameter_limits(zona)
            
            if zone_data:
                zona_params_oficiais = zone_data
                zona_info += f" - DADOS OFICIAIS CARREGADOS ({len(zone_limits)} parâmetros)"
                print(f"DEBUG ZONEAMENTO - Dados oficiais carregados para {zona}: {list(zone_limits.keys())}")
                
                # Adicionar resumo da zona aos detalhes
                zone_summary = zone_data_manager.get_zone_summary(zona)
                zona_detection_details += f"\n\nDados Oficiais da Zona:\n{zone_summary}"
            else:
                zona_params_oficiais = {}
                zona_info += f" - DADOS OFICIAIS NÃO ENCONTRADOS"
                print(f"DEBUG ZONEAMENTO - Nenhum dado oficial encontrado para {zona}")
                
                # Tentar fallback com sistema antigo se disponível
                try:
                    from zoneamento_integration import enhanced_zone_lookup
                    zone_params = enhanced_zone_lookup(zona)
                    if zone_params.get('zona_encontrada'):
                        zona_params_oficiais = zone_params.get('parametros', {})
                        print(f"DEBUG ZONEAMENTO - Usando fallback: parâmetros carregados para {zona}")
                except ImportError:
                    print(f"DEBUG ZONEAMENTO - Sistema de fallback não disponível")
            
            # Validação com parâmetros da zona detectada pelo sistema robusto
            validacoes_robustas = []
            if dados_formulario and dados_formulario.get('zona_parametros'):
                zona_parametros = dados_formulario['zona_parametros']
                validacoes_robustas = self._validar_conformidade_robusta(dados_formulario, zona_parametros)
                print(f"DEBUG ROBUST - Validações realizadas: {len(validacoes_robustas)} itens")
            
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
            query = self._build_query(endereco, cidade, zona, memorial, parametros, zona_params_oficiais, parametros_avancados)
            relatorio = generator.generate(documentos, query)
            
            return {
                'resultado': relatorio,
                'documentos': documentos,
                'memorial': memorial,
                'zona': zona,
                'zona_info': zona_detection_info,
                'zona_detection_details': zona_detection_details,
                'parametros': parametros,
                'validacoes_robustas': validacoes_robustas,
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
    
    def _build_query(self, endereco: str, cidade: str, zona: str, memorial: str, parametros: dict = None, zona_params_oficiais: dict = None, parametros_avancados: dict = None) -> str:
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
            
            # Usar altura personalizada se disponível
            altura_pav_personalizada = parametros_avancados.get('altura_personalizada_pav', 3.0) if parametros_avancados else 3.0
            altura_pav = parametros.get('altura_pavimentos', HeightConverter.metros_para_pavimentos(parametros['altura_edificacao'], altura_pav_personalizada))
            unidade_orig = parametros.get('altura_unidade_original', 'metros')
            
            # Considerar ático se especificado
            incluir_atico = parametros_avancados.get('incluir_atico', False) if parametros_avancados else False
            atico_info = " (incluindo ático/cobertura)" if incluir_atico else ""
            
            # Garantir que valores não sejam None para formatação
            altura_m = altura_m if altura_m is not None else 0.0
            altura_pav = altura_pav if altura_pav is not None else 0.0
            
            query += f"""
        
        INFORMAÇÕES ADICIONAIS SOBRE ALTURA:
        - Altura informada no memorial: {parametros['altura_edificacao']} {unidade_orig}{atico_info}
        - Equivalência: {altura_m:.1f} metros = {altura_pav:.1f} pavimentos
        - Conversão baseada em altura personalizada: 1 pavimento = {altura_pav_personalizada:.1f} metros
        """
        
        # Adicionar dados oficiais da zona usando o novo formato estruturado
        if zona_params_oficiais:
            query += f"""
        
        DADOS OFICIAIS DA ZONA {zona}:
        """
            
            # Processar parâmetros estruturados
            params_formatados = []
            
            if zona_params_oficiais.get('taxa_ocupacao', {}).get('valor'):
                params_formatados.append(f"- Taxa de Ocupação: {zona_params_oficiais['taxa_ocupacao']['valor']}")
                
            if zona_params_oficiais.get('coeficiente_aproveitamento', {}).get('valor'):
                params_formatados.append(f"- Coeficiente de Aproveitamento: {zona_params_oficiais['coeficiente_aproveitamento']['valor']}")
                
            if zona_params_oficiais.get('altura_pavimentos', {}).get('valor'):
                params_formatados.append(f"- Altura/Pavimentos: {zona_params_oficiais['altura_pavimentos']['valor']}")
                
            if zona_params_oficiais.get('taxa_permeavel', {}).get('valor'):
                params_formatados.append(f"- Taxa Permeável: {zona_params_oficiais['taxa_permeavel']['valor']}")
                
            if zona_params_oficiais.get('recuo_frontal', {}).get('valor'):
                params_formatados.append(f"- Recuo Frontal: {zona_params_oficiais['recuo_frontal']['valor']}")
                
            if zona_params_oficiais.get('afastamento_divisas', {}).get('valor'):
                params_formatados.append(f"- Afastamento Divisas: {zona_params_oficiais['afastamento_divisas']['valor']}")
                
            if zona_params_oficiais.get('lote_padrao', {}).get('valor'):
                params_formatados.append(f"- Lote Padrão: {zona_params_oficiais['lote_padrao']['valor']}")
                
            if zona_params_oficiais.get('usos_permitidos'):
                params_formatados.append(f"- Usos Permitidos: {zona_params_oficiais['usos_permitidos']}")
                
            if zona_params_oficiais.get('notas_tecnicas'):
                params_formatados.append(f"- Notas Técnicas: {zona_params_oficiais['notas_tecnicas']}")
            
            query += "\n".join(params_formatados)
            
            # Adicionar informações sobre limites específicos obtidos do ZoneDataManager
            zone_limits = zone_data_manager.get_parameter_limits(zona)
            if zone_limits:
                query += f"""
        
        LIMITES ESPECÍFICOS EXTRAÍDOS:
        """
                for param_name, limit in zone_limits.items():
                    if limit.min_value is not None or limit.max_value is not None:
                        query += f"- {param_name.replace('_', ' ').title()}: {limit.get_limit_display()}\n"
        
        query += f"""
        
        TAREFA ESPECÍFICA: 
        Analise cada parâmetro identificando se a legislação da zona {zona} estabelece:
        
        1. VALORES MÍNIMOS (ex: "área permeável mínima", "coeficiente mínimo")
        2. VALORES MÁXIMOS (ex: "taxa máxima", "altura máxima") 
        3. FAIXAS DE VALORES (ex: "entre X e Y", "de X até Y")
        
        Para cada parâmetro encontrado:
        - Se apenas máximo: compare se projeto ≤ máximo
        - Se apenas mínimo: compare se projeto ≥ mínimo  
        - Se faixa: compare se mínimo ≤ projeto ≤ máximo
        
        Use os PARÂMETROS OFICIAIS DA ZONA listados acima como referência principal, mas também
        analise os documentos de contexto para identificar limites mínimos e máximos específicos.
        """
        
        # Adicionar informações sobre parâmetros específicos avançados se disponíveis
        if parametros_avancados:
            query += f"""
        
        PARÂMETROS ESPECÍFICOS DE ANÁLISE:
        - Altura por pavimento personalizada: {parametros_avancados.get('altura_personalizada_pav', 3.0):.1f}m
        - Incluir ático/cobertura: {'Sim' if parametros_avancados.get('incluir_atico', False) else 'Não'}
        - Considerar varandas descobertas: {'Sim' if parametros_avancados.get('incluir_varandas', False) else 'Não'}
        - Considerar pavimento permeável: {'Sim' if parametros_avancados.get('pavimento_permeavel', False) else 'Não'}
        - Tipo de recuo: {parametros_avancados.get('tipo_recuo', 'Recuos mínimos')}
        - Considerar marquises/beirais: {'Sim' if parametros_avancados.get('considerar_marquises', False) else 'Não'}
        
        INSTRUÇÕES ESPECÍFICAS:
        - Para área permeável: {'incluir varandas descobertas e ' if parametros_avancados.get('incluir_varandas', False) else ''}{'considerar pavimentos permeáveis' if parametros_avancados.get('pavimento_permeavel', False) else 'usar critérios padrão'}
        - Para recuos: usar {'valores mínimos obrigatórios' if parametros_avancados.get('tipo_recuo') == 'Recuos obrigatórios' else 'valores mínimos recomendados'}{' e considerar marquises/beirais nos cálculos' if parametros_avancados.get('considerar_marquises', False) else ''}
        """
        
        return query
    
    def _validar_conformidade_robusta(self, dados_formulario: dict, zona_parametros) -> List[Dict[str, Any]]:
        """Validação detalhada com parâmetros da zona detectada pelo sistema robusto"""
        validacoes = []
        
        # Taxa de Ocupação
        if dados_formulario.get('area_lote', 0) > 0 and dados_formulario.get('area_projecao', 0) > 0:
            taxa_projeto = (dados_formulario['area_projecao'] / dados_formulario['area_lote']) * 100
            taxa_permitida = zona_parametros.taxa_ocupacao_maxima
            
            validacoes.append({
                'parametro': 'Taxa de Ocupação',
                'valor_projeto': f"{taxa_projeto:.1f}%",
                'valor_permitido': f"{taxa_permitida}%",
                'conforme': taxa_projeto <= taxa_permitida,
                'observacao': f"Projeto: {taxa_projeto:.1f}% | Máximo: {taxa_permitida}%"
            })
        
        # Coeficiente de Aproveitamento
        if dados_formulario.get('area_lote', 0) > 0 and dados_formulario.get('area_construida', 0) > 0:
            ca_projeto = dados_formulario['area_construida'] / dados_formulario['area_lote']
            ca_basico = zona_parametros.coef_aproveitamento_basico
            ca_maximo = zona_parametros.coef_aproveitamento_maximo or ca_basico
            
            # Verificar se usa potencial adicional
            utiliza_potencial = dados_formulario.get('utiliza_potencial_adicional', False)
            
            if utiliza_potencial:
                limite_aplicavel = ca_maximo
                observacao = f"Projeto: {ca_projeto:.2f} | Máximo com potencial adicional: {ca_maximo}"
            else:
                limite_aplicavel = ca_basico
                observacao = f"Projeto: {ca_projeto:.2f} | Básico: {ca_basico}"
            
            validacoes.append({
                'parametro': 'Coeficiente de Aproveitamento',
                'valor_projeto': f"{ca_projeto:.2f}",
                'valor_permitido': f"{limite_aplicavel:.2f}",
                'conforme': ca_projeto <= limite_aplicavel,
                'observacao': observacao
            })
        
        # Altura da Edificação
        if dados_formulario.get('num_pavimentos', 0) > 0:
            altura_projeto = dados_formulario['num_pavimentos']
            altura_maxima = zona_parametros.altura_maxima
            
            validacoes.append({
                'parametro': 'Altura da Edificação',
                'valor_projeto': f"{altura_projeto} pavimentos",
                'valor_permitido': f"{altura_maxima} pavimentos",
                'conforme': altura_projeto <= altura_maxima,
                'observacao': f"Projeto: {altura_projeto} | Máximo: {altura_maxima} pavimentos"
            })
        
        # Afastamentos (Recuos)
        if zona_parametros.recuo_frontal_minimo > 0:
            recuo_frontal = dados_formulario.get('recuo_frontal', 0)
            recuo_minimo = zona_parametros.recuo_frontal_minimo
            
            validacoes.append({
                'parametro': 'Recuo Frontal',
                'valor_projeto': f"{recuo_frontal}m",
                'valor_permitido': f"≥ {recuo_minimo}m",
                'conforme': recuo_frontal >= recuo_minimo,
                'observacao': f"Projeto: {recuo_frontal}m | Mínimo: {recuo_minimo}m"
            })
        
        # Taxa de Permeabilidade
        if dados_formulario.get('area_lote', 0) > 0 and zona_parametros.taxa_permeabilidade_minima > 0:
            area_permeavel_projeto = dados_formulario.get('area_permeavel', 0)
            taxa_projeto = (area_permeavel_projeto / dados_formulario['area_lote']) * 100
            taxa_minima = zona_parametros.taxa_permeabilidade_minima
            
            validacoes.append({
                'parametro': 'Taxa de Permeabilidade',
                'valor_projeto': f"{taxa_projeto:.1f}%",
                'valor_permitido': f"≥ {taxa_minima}%",
                'conforme': taxa_projeto >= taxa_minima,
                'observacao': f"Projeto: {taxa_projeto:.1f}% | Mínimo: {taxa_minima}%"
            })
        
        # Densidade Populacional (se aplicável a uso residencial)
        categoria_uso = dados_formulario.get('categoria_uso', '').lower()
        if 'residencial' in categoria_uso and zona_parametros.densidade_maxima > 0:
            num_unidades = dados_formulario.get('num_unidades_habitacionais', 0)
            area_lote_ha = dados_formulario.get('area_lote', 0) / 10000  # converter m² para ha
            
            if area_lote_ha > 0 and num_unidades > 0:
                # Assumir 2.5 habitantes por unidade habitacional (padrão IBGE)
                densidade_projeto = (num_unidades * 2.5) / area_lote_ha
                densidade_maxima = zona_parametros.densidade_maxima
                
                validacoes.append({
                    'parametro': 'Densidade Populacional',
                    'valor_projeto': f"{densidade_projeto:.0f} hab/ha",
                    'valor_permitido': f"≤ {densidade_maxima} hab/ha",
                    'conforme': densidade_projeto <= densidade_maxima,
                    'observacao': f"Projeto: {densidade_projeto:.0f} hab/ha | Máximo: {densidade_maxima} hab/ha"
                })
        
        return validacoes

# UI Functions (otimizadas)
def configurar_pagina():
    """Configuração otimizada da página"""
    st.set_page_config(
        page_title="Assistente Regulatório v6.0",
        page_icon="🏗️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # CSS básico para estilos
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
        
        /* Estilos para os resultados */
        .resultado-aprovado {
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            border-radius: 0.5rem;
            padding: 1rem;
            margin: 1rem 0;
        }
        
        .resultado-reprovado {
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            border-radius: 0.5rem;
            padding: 1rem;
            margin: 1rem 0;
        }
        
        /* Melhora visual dos botões */
        .stButton > button {
            transition: all 0.2s ease;
            border-radius: 0.5rem;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        
        /* Responsividade para downloads */
        @media (max-width: 640px) {
            .stColumns {
                flex-direction: column;
            }
            
            .stColumns > div {
                width: 100% !important;
                margin-bottom: 0.5rem;
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
    
    cidades = get_cidades_disponiveis()
    
    # =============================================
    # SEÇÃO 1: Identificação do Projeto
    # =============================================
    st.sidebar.title("🏗️ Assistente Regulamentação Civil")
    st.sidebar.header("📍 1. Identificação do Projeto")
    
    cidade = st.sidebar.selectbox(
        "Prefeitura:", 
        cidades,
        help="Selecione a prefeitura responsável pela análise"
    )
    
    endereco = st.sidebar.text_input(
        "📍 Endereço Completo do Imóvel: *",
        placeholder="Ex: RUA PROFESSOR OSVALDO ORMIAMIN, 480",
        help="⚠️ OBRIGATÓRIO: Digite o endereço completo para detecção precisa da zona"
    )
    
    inscricao_imobiliaria = st.sidebar.text_input(
        "Inscrição Imobiliária: *",
        placeholder="Ex: 03000180090017",
        help="Digite o número da inscrição imobiliária do imóvel (obrigatório). Esta informação é encontrada no carnê do IPTU do proprietário do imóvel."
    )
    
    # =============================================
    # DETECÇÃO AUTOMÁTICA DE ZONA
    # =============================================
    zona_detectada = None
    zona_confianca = 0.0
    zona_metodo = ""
    zona_parametros = None
    
    if cidade == "Curitiba" and (endereco or inscricao_imobiliaria):
        # Opção de método de detecção
        metodo_deteccao = st.sidebar.radio(
            "Método de Detecção:",
            ["🎯 Sistema Robusto (Offline)", "🌐 GeoCuritiba IPPUC (Online)"],
            help="Escolha entre detecção offline (rápida) ou busca oficial (mais precisa)"
        )
        
        if metodo_deteccao == "🌐 GeoCuritiba IPPUC (Online)":
            # Integração com GeoCuritiba IPPUC
            col1, col2 = st.sidebar.columns([3, 1])
            with col2:
                buscar_ippuc = st.button("🔍", help="Buscar no GeoCuritiba IPPUC", key="buscar_ippuc")
            
            if buscar_ippuc:
                with st.spinner("Consultando GeoCuritiba IPPUC..."):
                    try:
                        dados_ippuc = integrar_geocuritiba_app(
                            indicacao=inscricao_imobiliaria,
                            endereco=endereco,
                            automatico=True
                        )
                        
                        if dados_ippuc and dados_ippuc.get('encontrado'):
                            zona_detectada = dados_ippuc.get('zoneamento')
                            zona_confianca = 100.0  # Dados oficiais = 100% confiança
                            zona_metodo = "GeoCuritiba IPPUC (Oficial)"
                            
                            # Criar objeto compatível com os parâmetros
                            if dados_ippuc.get('parametros'):
                                parametros_ippuc = dados_ippuc['parametros']
                                
                                # Converter para formato compatível
                                class ParametrosIppuc:
                                    def __init__(self, params):
                                        self.coef_aproveitamento_basico = params.get('coef_aproveitamento_basico', 1.0)
                                        self.coef_aproveitamento_maximo = params.get('coef_aproveitamento_maximo', 1.0)
                                        self.taxa_ocupacao_maxima = params.get('taxa_ocupacao_maxima', 60.0)
                                        self.taxa_permeabilidade_minima = params.get('taxa_permeabilidade_minima', 25.0)
                                        self.altura_maxima = params.get('altura_maxima', 15.0)
                                        self.recuo_frontal_minimo = params.get('recuo_frontal_minimo', 5.0)
                                        self.densidade_maxima = 200.0  # Padrão
                                
                                zona_parametros = ParametrosIppuc(parametros_ippuc)
                            
                            # Salvar dados completos
                            st.session_state['dados_geocuritiba'] = dados_ippuc
                            
                            # Exibir informações da detecção oficial
                            st.sidebar.success(f"🎯 Zona OFICIAL: **{zona_detectada}**")
                            st.sidebar.info(f"🏛️ Fonte: GeoCuritiba IPPUC | Confiança: 100%")
                            
                            if dados_ippuc.get('area_lote'):
                                st.sidebar.info(f"📐 Área do Lote: {dados_ippuc['area_lote']:.2f} m²")
                            
                            if zona_parametros:
                                with st.sidebar.expander("📋 Parâmetros Oficiais da Zona"):
                                    st.write(f"**{zona_detectada}** (Dados IPPUC)")
                                    st.write(f"CA Básico: {zona_parametros.coef_aproveitamento_basico}")
                                    st.write(f"CA Máximo: {zona_parametros.coef_aproveitamento_maximo}")
                                    st.write(f"TO Máxima: {zona_parametros.taxa_ocupacao_maxima}%")
                                    st.write(f"TP Mínima: {zona_parametros.taxa_permeabilidade_minima}%")
                                    st.write(f"Altura Máx.: {zona_parametros.altura_maxima}m")
                                    if zona_parametros.recuo_frontal_minimo > 0:
                                        st.write(f"Recuo Frontal Mín.: {zona_parametros.recuo_frontal_minimo}m")
                        else:
                            st.sidebar.error("❌ Dados não encontrados no GeoCuritiba")
                            st.sidebar.info("Verifique a inscrição imobiliária ou tente o método offline")
                    except Exception as e:
                        st.sidebar.error(f"⚠️ Erro na consulta GeoCuritiba: {str(e)}")
        
        else:
            # Sistema offline original
            try:
                resultado_deteccao = detector_zoneamento.detectar_zona(
                    endereco=endereco if endereco else None,
                    inscricao=inscricao_imobiliaria if inscricao_imobiliaria else None
                )
                
                if resultado_deteccao and resultado_deteccao['zona']:
                    zona_detectada = resultado_deteccao['zona']
                    zona_confianca = resultado_deteccao['confianca']
                    zona_metodo = resultado_deteccao['metodo']
                    zona_parametros = resultado_deteccao.get('parametros')
                    
                    # Exibir informações da detecção
                    st.sidebar.success(f"🎯 Zona detectada: **{zona_detectada}**")
                    st.sidebar.info(f"📊 Confiança: {zona_confianca:.0f}% | Método: {zona_metodo}")
                    
                    if zona_parametros:
                        with st.sidebar.expander("📋 Ver Parâmetros da Zona"):
                            st.write(f"**{zona_detectada}**")
                            st.write(f"Coeficiente Básico: {zona_parametros.coef_aproveitamento_basico}")
                            st.write(f"Taxa de Ocupação: {zona_parametros.taxa_ocupacao_maxima}%")
                            st.write(f"Altura Máxima: {zona_parametros.altura_maxima} pavimentos")
                            if zona_parametros.recuo_frontal_minimo > 0:
                                st.write(f"Recuo Frontal Mín.: {zona_parametros.recuo_frontal_minimo}m")
            except Exception as e:
                st.sidebar.warning(f"⚠️ Erro na detecção de zona: {str(e)}")
    
    # =============================================
    # SEÇÃO 2: Dados do Lote
    # =============================================
    st.sidebar.header("📐 2. Dados do Lote")
    
    area_lote = st.sidebar.number_input(
        "Área Total do Lote (m²):",
        min_value=0.0,
        step=1.0,
        help="Área total do terreno em metros quadrados"
    )
    
    # Característica do Lote
    lote_esquina = st.sidebar.checkbox(
        "O lote é de esquina?",
        help="Lotes de esquina possuem regras específicas de recuos e afastamentos, com dois recuos frontais"
    )
    
    # Tipo de Obra
    tipo_obra = st.sidebar.selectbox(
        "Tipo de Obra:",
        [
            "Selecione...",
            "Construção Nova",
            "Reforma com Ampliação",
            "Reforma sem Ampliação", 
            "Regularização",
            "Demolição e Reconstrução",
            "Outros"
        ],
        help="O tipo de obra pode influenciar na aplicação de certas regulamentações específicas"
    )
    
    # Topografia do Lote
    topografia_acidentada = st.sidebar.checkbox(
        "O lote possui aclive/declive acentuado?",
        help="Terrenos com topografia acidentada têm regras específicas para medição de altura e definição de subsolos"
    )
    
    # Uso da Edificação - Sistema hierárquico
    categoria_uso = st.sidebar.selectbox(
        "Categoria de Uso:",
        [
            "Selecione...",
            "Residencial",
            "Comercial",
            "Serviços",
            "Industrial",
            "Institucional",
            "Misto",
            "Outros"
        ],
        help="Categoria principal do uso da edificação"
    )
    
    # Subcategoria baseada na categoria principal
    uso_pretendido = "Selecione..."
    if categoria_uso == "Residencial":
        uso_pretendido = st.sidebar.selectbox(
            "Subcategoria Residencial:",
            [
                "Selecione...",
                "Unifamiliar",
                "Multifamiliar (até 4 unidades)",
                "Multifamiliar (mais de 4 unidades)",
                "Conjunto Habitacional",
                "Habitação de Interesse Social"
            ],
            help="Especifique o tipo de uso residencial"
        )
    elif categoria_uso == "Comercial":
        uso_pretendido = st.sidebar.selectbox(
            "Subcategoria Comercial:",
            [
                "Selecione...",
                "Comércio Vicinal (bairro)",
                "Comércio Setorial",
                "Centro Comercial/Shopping",
                "Atacado",
                "Outros"
            ],
            help="Especifique o tipo de comércio"
        )
    elif categoria_uso == "Serviços":
        uso_pretendido = st.sidebar.selectbox(
            "Subcategoria Serviços:",
            [
                "Selecione...",
                "Serviços Profissionais",
                "Serviços de Saúde",
                "Educação",
                "Hotelaria",
                "Outros"
            ],
            help="Especifique o tipo de serviço"
        )
    elif categoria_uso == "Misto":
        uso_pretendido = st.sidebar.selectbox(
            "Tipo de Uso Misto:",
            [
                "Selecione...",
                "Residencial + Comercial",
                "Residencial + Serviços",
                "Comercial + Serviços",
                "Outros"
            ],
            help="Especifique a combinação de usos"
        )
    elif categoria_uso not in ["Selecione...", "Outros"]:
        uso_pretendido = categoria_uso
    
    # =============================================
    # SEÇÃO 3: Restrições do Lote
    # =============================================
    st.sidebar.header("🚫 3. Restrições do Lote")
    
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
    st.sidebar.header("🏠 4. Parâmetros da Edificação")
    
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
        help="Somatório das áreas de todos os pavimentos. Inclui áreas cobertas como garagens e varandas conforme definição da prefeitura. Considere áreas não computáveis se aplicável."
    )
    
    altura_edificacao = st.sidebar.number_input(
        "Altura Total da Edificação (m):",
        min_value=0.0,
        step=0.1,
        help="Altura total medida a partir do nível médio do terreno (RN). Pode incluir platibanda e caixa d'água conforme regulamentação local."
    )
    
    num_pavimentos = st.sidebar.number_input(
        "Número de Pavimentos:",
        min_value=1,
        step=1,
        help="Quantidade total de pavimentos da edificação (incluindo subsolos se computáveis)"
    )
    
    # Número de Unidades
    st.sidebar.subheader("📊 Unidades da Edificação")
    
    num_unidades_habitacionais = st.sidebar.number_input(
        "Número de Unidades Habitacionais:",
        min_value=0,
        step=1,
        help="Quantidade de unidades residenciais (apartamentos, casas). Essencial para cálculo de vagas de estacionamento e densidade."
    )
    
    num_unidades_nao_habitacionais = st.sidebar.number_input(
        "Número de Unidades Não Habitacionais:",
        min_value=0,
        step=1,
        help="Quantidade de unidades comerciais, de serviços ou outras. Importante para cálculo de vagas e análise de uso misto."
    )
    
    # Potencial Construtivo Adicional
    utiliza_potencial_adicional = st.sidebar.checkbox(
        "Utilizará Potencial Construtivo Adicional?",
        help="Ex: Outorga Onerosa, Transferência do Direito de Construir. Permite área construída superior ao coeficiente básico."
    )
    
    if utiliza_potencial_adicional:
        tipo_potencial = st.sidebar.selectbox(
            "Tipo de Potencial Adicional:",
            [
                "Selecione...",
                "Outorga Onerosa do Direito de Construir",
                "Transferência do Direito de Construir (TDC)",
                "CEPAC (Curitiba)",
                "Outros"
            ],
            help="Especifique o instrumento urbanístico utilizado para obter potencial construtivo adicional"
        )
    
    # =============================================
    # SEÇÃO 5: Afastamentos (Recuos)
    # =============================================
    st.sidebar.header("↔️ 5. Afastamentos (Recuos)")
    
    # Campos dinâmicos baseados no tipo de lote
    if lote_esquina:
        st.sidebar.info("🔄 Lote de esquina detectado - Dois recuos frontais obrigatórios")
        
        recuo_frontal = st.sidebar.number_input(
            "Recuo Frontal Principal (m):",
            min_value=0.0,
            step=0.1,
            help="Distância da edificação até a divisa da via principal"
        )
        
        recuo_frontal_secundario = st.sidebar.number_input(
            "Recuo Frontal Secundário (m):",
            min_value=0.0,
            step=0.1,
            help="Distância da edificação até a divisa da via secundária (segundo recuo frontal)"
        )
        
        recuo_lateral_dir = st.sidebar.number_input(
            "Recuo Lateral (m):",
            min_value=0.0,
            step=0.1,
            help="Distância da edificação até a divisa lateral (lote de esquina tem apenas uma lateral)"
        )
        
        # Para lotes de esquina, não há recuo lateral esquerdo
        recuo_lateral_esq = 0.0
        
    else:
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
        
        # Para lotes normais, não há segundo recuo frontal
        recuo_frontal_secundario = 0.0
    
    recuo_fundos = st.sidebar.number_input(
        "Recuo de Fundos (m):",
        min_value=0.0,
        step=0.1,
        help="Distância da edificação até a divisa de fundos"
    )
    
    # =============================================
    # SEÇÃO 6: Parâmetros Adicionais
    # =============================================
    st.sidebar.header("🌱 6. Parâmetros Adicionais")
    
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
    # SEÇÃO 7: Opções Avançadas
    # =============================================
    st.sidebar.header("⚙️ 7. Opções Avançadas")
    
    # Zona Manual
    zona_manual = st.sidebar.text_input(
        "Zona Manual:",
        placeholder="Ex: ZR-4, ZCC.4",
        help="Informe a zona se conhecida (opcional)"
    )
    usar_zona_manual = st.sidebar.checkbox(
        "Usar zona informada manualmente",
        help="Marque para usar a zona informada ao invés da detecção automática"
    )
    
    st.sidebar.markdown("**🔧 Parâmetros Específicos**")
    
    # Conversão de altura personalizada
    st.sidebar.markdown("**Altura por Pavimento:**")
    altura_personalizada_pav = st.sidebar.number_input(
        "Altura por pavimento (m):",
        min_value=2.4,
        max_value=4.0,
        value=3.0,
        step=0.1,
        help="Altura personalizada para conversão metros ↔ pavimentos"
    )
    
    incluir_atico = st.sidebar.checkbox(
        "Incluir ático/cobertura no cálculo",
        help="Considera ático e cobertura no cálculo de altura total"
    )
    
    # Cálculo de área permeável
    st.sidebar.markdown("**Área Permeável:**")
    incluir_varandas = st.sidebar.checkbox(
        "Incluir varandas descobertas",
        help="Considera varandas descobertas como área permeável"
    )
    
    pavimento_permeavel = st.sidebar.checkbox(
        "Considerar pavimento permeável",
        help="Inclui pavimentos permeáveis no cálculo da taxa"
    )
    
    # Tratamento de recuos
    st.sidebar.markdown("**Recuos:**")
    tipo_recuo = st.sidebar.selectbox(
        "Tipo de recuo:",
        ["Recuos mínimos", "Recuos obrigatórios"],
        help="Define se usar valores mínimos ou obrigatórios da legislação"
    )
    
    considerar_marquises = st.sidebar.checkbox(
        "Considerar marquises e beirais",
        help="Inclui marquises e beirais no cálculo de recuos"
    )
    
    # =============================================
    # VALIDAÇÕES E CÁLCULOS
    # =============================================
    
    # VALIDAÇÕES OBRIGATÓRIAS: Endereço e Inscrição Imobiliária devem estar preenchidos
    endereco_obrigatorio = bool(endereco and endereco.strip())
    inscricao_obrigatoria = bool(inscricao_imobiliaria and inscricao_imobiliaria.strip())
    
    # Verificar se outros campos estão preenchidos (complementares)
    campos_complementares = [
        area_lote > 0, uso_pretendido != "Selecione...", 
        area_projecao > 0, area_construida > 0, altura_edificacao > 0,
        inscricao_imobiliaria
    ]
    
    pelo_menos_um_campo = endereco_obrigatorio and inscricao_obrigatoria and any(campo for campo in campos_complementares)
    
    # Validações lógicas
    validacoes_ok = True
    mensagens_erro = []
    
    # Validações críticas: endereço e inscrição imobiliária obrigatórios
    if not endereco_obrigatorio:
        validacoes_ok = False
    
    if not inscricao_obrigatoria:
        validacoes_ok = False
    
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
            st.sidebar.error(f"⚠️ {erro}")
    
    # =============================================
    # BOTÃO DE ANÁLISE
    # =============================================
    st.sidebar.markdown("---")
    
    # Botão habilitado se pelo menos um campo estiver preenchido e sem erros críticos
    pode_analisar = pelo_menos_um_campo and validacoes_ok
    
    if not pode_analisar:
        if not endereco_obrigatorio:
            st.sidebar.error("🚫 Endereço completo é OBRIGATÓRIO para análise!")
        elif not inscricao_obrigatoria:
            st.sidebar.error("🚫 Inscrição Imobiliária é OBRIGATÓRIA para análise!")
        elif not pelo_menos_um_campo:
            st.sidebar.warning("⚠️ Preencha pelo menos um campo complementar para análise")
        elif not validacoes_ok:
            st.sidebar.warning("⚠️ Corrija os erros de validação acima")
    
    analisar = st.sidebar.button(
        "🔍 Analisar Conformidade",
        type="primary",
        use_container_width=True,
        disabled=not pode_analisar,
        help="Clique para iniciar a análise de conformidade urbanística"
    )
    
    # =============================================
    # INFORMAÇÕES DO SISTEMA
    # =============================================
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ℹ️ Cálculos Automáticos")
    
    if area_lote > 0:
        col1, col2 = st.sidebar.columns(2)
        col1.metric("Taxa de Ocupação", f"{taxa_ocupacao:.1f}%")
        col2.metric("Coef. Aproveitamento", f"{coeficiente_aproveitamento:.2f}")
    
    st.sidebar.info(f"""
    **Sistema:** v{CONFIG.VERSAO_APP}  
    **Cidade:** {cidade}  
    **Status:** ✅ Operacional
    """)
    
    # Retornar dados coletados
    return {
        'cidade': cidade,
        'endereco': endereco,
        'inscricao_imobiliaria': inscricao_imobiliaria,
        'area_lote': area_lote,
        # Novas características do lote
        'lote_esquina': lote_esquina,
        'tipo_obra': tipo_obra,
        'topografia_acidentada': topografia_acidentada,
        # Uso melhorado
        'categoria_uso': categoria_uso,
        'uso_pretendido': uso_pretendido,
        'possui_app': possui_app,
        'area_app': area_app,
        'possui_drenagem': possui_drenagem,
        'area_drenagem': area_drenagem,
        'area_projecao': area_projecao,
        'area_construida': area_construida,
        'altura_edificacao': altura_edificacao,
        'num_pavimentos': num_pavimentos,
        # Novas informações de unidades
        'num_unidades_habitacionais': num_unidades_habitacionais,
        'num_unidades_nao_habitacionais': num_unidades_nao_habitacionais,
        # Potencial construtivo adicional
        'utiliza_potencial_adicional': utiliza_potencial_adicional,
        'tipo_potencial': tipo_potencial if utiliza_potencial_adicional else None,
        # Recuos adaptados para lote de esquina
        'recuo_frontal': recuo_frontal,
        'recuo_frontal_secundario': recuo_frontal_secundario if lote_esquina else 0.0,
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
        'analisar': analisar,
        # Parâmetros específicos avançados
        'altura_personalizada_pav': altura_personalizada_pav,
        'incluir_atico': incluir_atico,
        'incluir_varandas': incluir_varandas,
        'pavimento_permeavel': pavimento_permeavel,
        'tipo_recuo': tipo_recuo,
        'considerar_marquises': considerar_marquises,
        # Informações da zona detectada
        'zona_detectada': zona_detectada,
        'zona_confianca': zona_confianca,
        'zona_metodo': zona_metodo,
        'zona_parametros': zona_parametros
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
- Categoria de Uso: {dados['categoria_uso'] if dados['categoria_uso'] != 'Selecione...' else 'NÃO INFORMADA'}
- Uso Específico: {dados['uso_pretendido'] if dados['uso_pretendido'] != 'Selecione...' else 'NÃO INFORMADO'}
- Tipo de Obra: {dados['tipo_obra'] if dados['tipo_obra'] != 'Selecione...' else 'NÃO INFORMADO'}

2. DADOS DO LOTE:
- Área Total: {dados['area_lote']:.2f} m² {('(NÃO INFORMADA)' if dados['area_lote'] == 0 else '')}
- Lote de Esquina: {'SIM' if dados['lote_esquina'] else 'NÃO'}
- Topografia Acidentada: {'SIM' if dados['topografia_acidentada'] else 'NÃO'}
- Área de APP: {dados['area_app']:.2f} m² ({('SIM' if dados['possui_app'] else 'NÃO')})
- Área de Drenagem: {dados['area_drenagem']:.2f} m² ({('SIM' if dados['possui_drenagem'] else 'NÃO')})
- Área Permeável: {dados['area_permeavel']:.2f} m² {('(NÃO INFORMADA)' if dados['area_permeavel'] == 0 else '')}

3. PARÂMETROS DA EDIFICAÇÃO:
- Área de Projeção: {dados['area_projecao']:.2f} m² {('(NÃO INFORMADA)' if dados['area_projecao'] == 0 else '')}
- Área Construída Total: {dados['area_construida']:.2f} m² {('(NÃO INFORMADA)' if dados['area_construida'] == 0 else '')}
- Altura da Edificação: {dados['altura_edificacao']:.2f} m {('(NÃO INFORMADA)' if dados['altura_edificacao'] == 0 else '')}
- Número de Pavimentos: {dados['num_pavimentos']} {('(NÃO INFORMADO)' if dados['num_pavimentos'] == 1 else '')}
- Unidades Habitacionais: {dados['num_unidades_habitacionais']} {('(NÃO INFORMADO)' if dados['num_unidades_habitacionais'] == 0 else '')}
- Unidades Não Habitacionais: {dados['num_unidades_nao_habitacionais']} {('(NÃO INFORMADO)' if dados['num_unidades_nao_habitacionais'] == 0 else '')}
- Potencial Construtivo Adicional: {'SIM' if dados['utiliza_potencial_adicional'] else 'NÃO'}{(' (' + str(dados['tipo_potencial']) + ')') if dados['utiliza_potencial_adicional'] and dados['tipo_potencial'] and dados['tipo_potencial'] != 'Selecione...' else ''}
- Vagas de Estacionamento: {dados['num_vagas']} {('(NÃO INFORMADO)' if dados['num_vagas'] == 0 else '')}

4. AFASTAMENTOS (RECUOS):
{('- Recuo Frontal Principal: ' + str(dados['recuo_frontal']) + ' m ' + ('(NÃO INFORMADO)' if dados['recuo_frontal'] == 0 else '') + chr(10) + '- Recuo Frontal Secundário: ' + str(dados['recuo_frontal_secundario']) + ' m ' + ('(NÃO INFORMADO)' if dados['recuo_frontal_secundario'] == 0 else '') + chr(10) + '- Recuo Lateral: ' + str(dados['recuo_lateral_dir']) + ' m ' + ('(NÃO INFORMADO)' if dados['recuo_lateral_dir'] == 0 else '')) if dados['lote_esquina'] else ('- Recuo Frontal: ' + str(dados['recuo_frontal']) + ' m ' + ('(NÃO INFORMADO)' if dados['recuo_frontal'] == 0 else '') + chr(10) + '- Recuo Lateral Direito: ' + str(dados['recuo_lateral_dir']) + ' m ' + ('(NÃO INFORMADO)' if dados['recuo_lateral_dir'] == 0 else '') + chr(10) + '- Recuo Lateral Esquerdo: ' + str(dados['recuo_lateral_esq']) + ' m ' + ('(NÃO INFORMADO)' if dados['recuo_lateral_esq'] == 0 else ''))}
- Recuo de Fundos: {dados['recuo_fundos']:.2f} m {('(NÃO INFORMADO)' if dados['recuo_fundos'] == 0 else '')}

5. ÍNDICES CALCULADOS:
- Taxa de Ocupação: {dados['taxa_ocupacao']:.2f}% {('(IMPOSSÍVEL CALCULAR - DADOS INSUFICIENTES)' if dados['area_lote'] == 0 else '')}
- Coeficiente de Aproveitamento: {dados['coeficiente_aproveitamento']:.2f} {('(IMPOSSÍVEL CALCULAR - DADOS INSUFICIENTES)' if dados['area_lote'] == 0 else '')}

OBSERVAÇÃO: Dados não informados serão considerados como FALTANTES na análise de conformidade.
"""
        
        # Executar análise
        try:
            with st.spinner("Executando análise de conformidade urbanística..."):
                # Coletar parâmetros avançados
                parametros_avancados = {
                    'altura_personalizada_pav': dados.get('altura_personalizada_pav', 3.0),
                    'incluir_atico': dados.get('incluir_atico', False),
                    'incluir_varandas': dados.get('incluir_varandas', False),
                    'pavimento_permeavel': dados.get('pavimento_permeavel', False),
                    'tipo_recuo': dados.get('tipo_recuo', 'Recuos mínimos'),
                    'considerar_marquises': dados.get('considerar_marquises', False)
                }
                
                resultado = st.session_state.engine.run_analysis(
                    cidade=dados['cidade'],
                    endereco=dados['endereco'],
                    memorial=memorial,
                    zona_manual=dados['zona_manual'],
                    usar_zona_manual=dados['usar_zona_manual'],
                    parametros_avancados=parametros_avancados,
                    dados_formulario=dados
                )
                
                # Adicionar dados do formulário ao resultado
                resultado['dados_formulario'] = dados
                st.session_state.analysis_result = resultado
                st.rerun()
                
        except Exception as e:
            st.error(f"❌ Erro na análise: {str(e)}")
            logger.error(f"Erro completo: {e}", exc_info=True)
    
    # Container para resultados com classe CSS responsiva
    st.markdown('<div class="report-container">', unsafe_allow_html=True)
    
    # Exibir resultados
    if st.session_state.analysis_result:
        resultado = st.session_state.analysis_result
        
        # Header com status aprimorado
        zona_display = resultado.get('zona_info', resultado['zona'])
        
        st.header(f"📋 Relatório: Zona {zona_display}")
        
        # Mostrar informações de detecção se disponível
        if 'zona_detection_details' in resultado:
            with st.expander("🔍 Informações da Detecção de Zona", expanded=False):
                st.info(resultado['zona_detection_details'])
                
                # Mostrar coordenadas se disponível (buscar no log)
                if "Coordenadas GPS" in resultado['zona_detection_details']:
                    st.success("✅ **Detecção Oficial:** Zona identificada com precisão geográfica usando sistema GIS profissional")
                elif "análise textual" in resultado['zona_detection_details'].lower():
                    st.warning("⚠️ **Zona Estimada:** Baseada em análise textual do endereço")
                elif "padrão" in resultado['zona_detection_details'].lower():
                    st.info("🔄 **Zona Padrão:** Sistema utilizou zona residencial padrão para análise")
                elif "manual" in resultado['zona_detection_details'].lower():
                    st.success("✅ **Zona Manual:** Informada pelo usuário")
        
        # Exibir validações robustas se disponível
        if 'validacoes_robustas' in resultado and resultado['validacoes_robustas']:
            with st.expander("🎯 Validações Diretas - Sistema Robusto", expanded=True):
                st.info("📋 Análise automática baseada nos parâmetros oficiais da zona detectada")
                
                validacoes = resultado['validacoes_robustas']
                for validacao in validacoes:
                    if validacao['conforme']:
                        st.success(f"✅ **{validacao['parametro']}**: CONFORME")
                        st.write(f"   {validacao['observacao']}")
                    else:
                        st.error(f"❌ **{validacao['parametro']}**: NÃO CONFORME")
                        st.write(f"   {validacao['observacao']}")
                
                # Resumo das validações
                total_validacoes = len(validacoes)
                validacoes_aprovadas = len([v for v in validacoes if v['conforme']])
                validacoes_reprovadas = total_validacoes - validacoes_aprovadas
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total", total_validacoes)
                with col2:
                    st.metric("✅ Conformes", validacoes_aprovadas)
                with col3:
                    st.metric("❌ Não Conformes", validacoes_reprovadas)
                
                if validacoes_reprovadas == 0:
                    st.balloons()
                    st.success("🎉 **PARABÉNS!** Todos os parâmetros analisados estão em conformidade!")
                else:
                    st.warning(f"⚠️ **ATENÇÃO:** {validacoes_reprovadas} parâmetro(s) apresenta(m) não conformidade")
        
        # Status do projeto com containers estilizados
        parecer = resultado['resultado']
        if "não conformidade" in parecer.lower() or "reprovado" in parecer.lower():
            st.markdown('<div class="resultado-reprovado">', unsafe_allow_html=True)
            st.error("❌ **Projeto REPROVADO**")
            st.markdown('</div>', unsafe_allow_html=True)
        elif "conformidade" in parecer.lower() or "aprovado" in parecer.lower():
            st.markdown('<div class="resultado-aprovado">', unsafe_allow_html=True)
            st.success("✅ **Projeto APROVADO**")
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("⚠️ **Análise Pendente**")
        
        # Tabs do resultado
        tab1, tab2, tab3 = st.tabs(["📊 Relatório", "📄 Documentos", "🔧 Debug"])
        
        with tab1:
            st.markdown(resultado['resultado'])
            
            # Downloads responsivos
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    "📥 Download TXT",
                    resultado['resultado'],
                    f"relatorio_{resultado['zona']}.txt",
                    "text/plain",
                    use_container_width=True
                )
            with col2:
                if st.button("🔄 Nova Análise", use_container_width=True):
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
        st.title("🏗️ Assistente Regulatório v6.0")
        st.markdown("### Análise inteligente de conformidade urbanística")
        st.markdown("---")
        st.info("📋 Configure a análise na barra lateral para começar")
        
        # Info compacta
        cidade = dados.get('cidade', '')
        if cidade and (CONFIG.PASTA_DADOS_RAIZ / cidade.lower()).exists():
            st.markdown("---")
            st.markdown(f"📊 {cidade.title()} • v{CONFIG.VERSAO_APP} • ✅ Ativo")
    
    # Fechar container responsivo
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    load_dotenv()
    main()