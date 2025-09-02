# utils_melhorado.py - Utilitários Otimizados

import os, re, json, logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from functools import lru_cache
from dataclasses import dataclass
import hashlib
import pickle

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

@dataclass
class GeoConfig:
    CACHE_FILE: Path = Path("cache/geo_cache.pkl")
    NOMINATIM_USER_AGENT: str = "assistente_regulatorio_v2"
    REQUEST_TIMEOUT: int = 10
    MAX_RETRIES: int = 3
    BACKOFF_FACTOR: float = 0.3

CONFIG = GeoConfig()

class OptimizedGeocoder:
    """Geocoder otimizado com cache persistente e fallbacks"""
    
    def __init__(self):
        self.cache = self._load_cache()
        self.geolocator = self._setup_geolocator()
        self.session = self._setup_session()
        self.stats = {'cache_hits': 0, 'api_calls': 0, 'errors': 0}
    
    def _load_cache(self) -> Dict:
        """Carrega cache de geocoding do disco"""
        if CONFIG.CACHE_FILE.exists():
            try:
                with open(CONFIG.CACHE_FILE, 'rb') as f:
                    cache = pickle.load(f)
                logger.info(f"Cache carregado: {len(cache)} entradas")
                return cache
            except Exception as e:
                logger.warning(f"Erro ao carregar cache: {e}")
        
        # Cria diretório se não existir
        CONFIG.CACHE_FILE.parent.mkdir(exist_ok=True)
        return {}
    
    def _save_cache(self):
        """Salva cache no disco"""
        try:
            with open(CONFIG.CACHE_FILE, 'wb') as f:
                pickle.dump(self.cache, f)
        except Exception as e:
            logger.warning(f"Erro ao salvar cache: {e}")
    
    def _setup_geolocator(self):
        """Configura geolocator com retry"""
        return Nominatim(
            user_agent=CONFIG.NOMINATIM_USER_AGENT,
            timeout=CONFIG.REQUEST_TIMEOUT
        )
    
    def _setup_session(self):
        """Configura sessão HTTP com retry"""
        session = requests.Session()
        retry_strategy = Retry(
            total=CONFIG.MAX_RETRIES,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            backoff_factor=CONFIG.BACKOFF_FACTOR
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
    
    def geocode(self, address: str) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        """Geocoding otimizado com cache e fallbacks"""
        # Normaliza endereço para cache
        cache_key = self._normalize_address(address)
        
        # Verifica cache
        if cache_key in self.cache:
            self.stats['cache_hits'] += 1
            cached = self.cache[cache_key]
            return cached.get('lat'), cached.get('lon'), cached.get('error')
        
        # Tenta geocoding
        self.stats['api_calls'] += 1
        
        # Estratégia 1: Nominatim
        lat, lon, error = self._try_nominatim(address)
        
        # Estratégia 2: Fallback para API do Brasil (se Nominatim falhar)
        if lat is None and "brasil" in address.lower():
            lat, lon, error = self._try_brasil_api(address)
        
        # Cache resultado (mesmo se erro)
        self.cache[cache_key] = {
            'lat': lat,
            'lon': lon,
            'error': error,
            'address_original': address
        }
        
        # Salva cache periodicamente
        if len(self.cache) % 10 == 0:
            self._save_cache()
        
        if error:
            self.stats['errors'] += 1
        
        return lat, lon, error
    
    def _normalize_address(self, address: str) -> str:
        """Normaliza endereço para chave de cache"""
        normalized = address.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)  # Remove espaços extras
        normalized = re.sub(r'[^\w\s,-]', '', normalized)  # Remove pontuação
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _try_nominatim(self, address: str) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        """Tenta geocoding com Nominatim"""
        try:
            # Adiciona contexto brasileiro se não especificado
            if "brasil" not in address.lower() and "brazil" not in address.lower():
                address_with_context = f"{address}, Brasil"
            else:
                address_with_context = address
            
            location = self.geolocator.geocode(address_with_context)
            
            if location:
                return location.latitude, location.longitude, None
            else:
                return None, None, "Endereço não encontrado"
                
        except (GeocoderTimedOut, GeocoderUnavailable) as e:
            return None, None, f"Erro de geocoding: {str(e)}"
        except Exception as e:
            logger.warning(f"Erro inesperado no geocoding: {e}")
            return None, None, f"Erro inesperado: {str(e)}"
    
    def _try_brasil_api(self, address: str) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        """Fallback usando API do Brasil (exemplo)"""
        try:
            # Extrai cidade do endereço
            city_match = re.search(r',\s*([^,]+),?\s*(?:brasil|brazil)?$', address.lower())
            if city_match:
                city = city_match.group(1).strip()
                
                # API pública do IBGE para coordenadas de municípios
                url = f"https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
                response = self.session.get(url, timeout=CONFIG.REQUEST_TIMEOUT)
                
                if response.status_code == 200:
                    municipios = response.json()
                    
                    for municipio in municipios:
                        if city.lower() in municipio['nome'].lower():
                            # Retorna coordenadas aproximadas do centro do município
                            # (Para implementação completa, seria necessário outra API)
                            logger.info(f"Município encontrado: {municipio['nome']}")
                            # Placeholder - implementar busca de coordenadas específicas
                            return None, None, "Fallback não implementado completamente"
            
            return None, None, "Cidade não encontrada no fallback"
            
        except Exception as e:
            return None, None, f"Erro no fallback: {str(e)}"
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas de uso"""
        return self.stats.copy()
    
    def __del__(self):
        """Salva cache ao destruir o objeto"""
        if hasattr(self, 'cache'):
            self._save_cache()

class OptimizedZoneFinder:
    """Finder de zonas otimizado com cache espacial"""
    
    def __init__(self, shapefile_path: Path):
        self.shapefile_path = Path(shapefile_path)
        self.gdf = None
        self.spatial_index = None
        self.geocoder = OptimizedGeocoder()
        self._load_shapefile()
    
    def _load_shapefile(self):
        """Carrega shapefile com cache"""
        cache_key = f"shapefile_{self.shapefile_path.stat().st_mtime}"
        
        try:
            if not self.shapefile_path.exists():
                raise FileNotFoundError(f"Shapefile não encontrado: {self.shapefile_path}")
            
            logger.info(f"Carregando shapefile: {self.shapefile_path}")
            self.gdf = gpd.read_file(self.shapefile_path)
            
            # Verifica sistema de coordenadas
            if self.gdf.crs is None:
                logger.warning("CRS não definido, assumindo EPSG:4326")
                self.gdf.set_crs(epsg=4326, inplace=True)
            elif self.gdf.crs != 'EPSG:4326':
                logger.info(f"Convertendo CRS de {self.gdf.crs} para EPSG:4326")
                self.gdf = self.gdf.to_crs('EPSG:4326')
            
            # Cria índice espacial para consultas rápidas
            self.spatial_index = self.gdf.sindex
            
            # Identifica coluna de zona
            self.zone_column = self._identify_zone_column()
            
            logger.info(f"Shapefile carregado: {len(self.gdf)} zonas, coluna: {self.zone_column}")
            
        except Exception as e:
            logger.error(f"Erro ao carregar shapefile: {e}")
            raise
    
    def _identify_zone_column(self) -> str:
        """Identifica automaticamente a coluna que contém as zonas"""
        possible_columns = ['zona', 'zone', 'zoneamento', 'uso', 'tipo', 'class', 'classificacao']
        
        for col in self.gdf.columns:
            col_lower = col.lower()
            
            # Verifica se é uma das colunas esperadas
            if any(pc in col_lower for pc in possible_columns):
                # Verifica se contém valores que parecem zonas
                sample_values = self.gdf[col].dropna().astype(str).head(10)
                if any(re.search(r'\b(ZR|ZS|ZC|ZT|ZONA)', val.upper()) for val in sample_values):
                    return col
        
        # Fallback: primeira coluna que contém texto parecido com zona
        for col in self.gdf.columns:
            if self.gdf[col].dtype == 'object':
                sample_values = self.gdf[col].dropna().astype(str).head(5)
                if any(re.search(r'\b(Z[RSC]|ZONA)', val.upper()) for val in sample_values):
                    return col
        
        # Último fallback: primeira coluna de texto
        for col in self.gdf.columns:
            if self.gdf[col].dtype == 'object':
                return col
        
        raise ValueError("Não foi possível identificar a coluna de zonas no shapefile")
    
    @lru_cache(maxsize=1000)
    def find_zone(self, lat: float, lon: float) -> Tuple[Optional[str], Optional[str]]:
        """Encontra zona de um ponto com cache LRU"""
        try:
            point = Point(lon, lat)
            
            # Consulta espacial otimizada usando índice
            possible_matches_index = list(self.spatial_index.intersection(point.bounds))
            possible_matches = self.gdf.iloc[possible_matches_index]
            
            # Verifica containment exato
            for idx, row in possible_matches.iterrows():
                if row.geometry.contains(point):
                    zone_value = row[self.zone_column]
                    if pd.notna(zone_value):
                        return str(zone_value).strip(), None
            
            # Se não encontrou containment exato, tenta nearest
            if len(possible_matches) > 0:
                distances = possible_matches.geometry.distance(point)
                nearest_idx = distances.idxmin()
                nearest_zone = possible_matches.loc[nearest_idx, self.zone_column]
                
                if pd.notna(nearest_zone):
                    distance_m = distances.min() * 111000  # Aproximação lat/lon para metros
                    if distance_m < 100:  # Se está muito próximo (< 100m)
                        return str(nearest_zone).strip(), f"Zona aproximada (distância: {distance_m:.0f}m)"
            
            return None, "Ponto fora das zonas mapeadas"
            
        except Exception as e:
            logger.error(f"Erro na consulta espacial: {e}")
            return None, f"Erro na consulta espacial: {str(e)}"
    
    def get_zone_info(self, zone_name: str) -> Dict[str, Any]:
        """Retorna informações detalhadas sobre uma zona"""
        try:
            zone_matches = self.gdf[self.gdf[self.zone_column].astype(str).str.contains(
                zone_name, case=False, na=False
            )]
            
            if len(zone_matches) == 0:
                return {"error": f"Zona {zone_name} não encontrada"}
            
            # Agrega informações se múltiplas geometrias
            total_area = zone_matches.geometry.area.sum()
            centroid = zone_matches.geometry.unary_union.centroid
            
            info = {
                "zona": zone_name,
                "geometrias": len(zone_matches),
                "area_total": total_area,
                "centroid": {"lat": centroid.y, "lon": centroid.x},
                "bbox": zone_matches.total_bounds.tolist()
            }
            
            # Adiciona outras colunas disponíveis
            for col in self.gdf.columns:
                if col != self.zone_column and col != 'geometry':
                    values = zone_matches[col].dropna().unique()
                    if len(values) > 0:
                        info[col] = values.tolist() if len(values) > 1 else values[0]
            
            return info
            
        except Exception as e:
            return {"error": f"Erro ao buscar informações da zona: {str(e)}"}
    
    def list_zones(self) -> List[str]:
        """Lista todas as zonas disponíveis"""
        try:
            zones = self.gdf[self.zone_column].dropna().astype(str).unique()
            return sorted(zones)
        except Exception as e:
            logger.error(f"Erro ao listar zonas: {e}")
            return []

# Instância global do finder (será inicializada quando necessário)
_zone_finder = None

def get_zone_finder(shapefile_path: Path) -> OptimizedZoneFinder:
    """Retorna instância singleton do zone finder"""
    global _zone_finder
    if _zone_finder is None:
        _zone_finder = OptimizedZoneFinder(shapefile_path)
    return _zone_finder

def encontrar_zona_por_endereco(endereco: str, caminho_shapefile: Path) -> Tuple[Optional[str], Optional[str]]:
    """Função principal otimizada para encontrar zona por endereço"""
    try:
        # Validação de entrada
        if not endereco or not endereco.strip():
            return None, "Endereço não fornecido"
        
        if not caminho_shapefile.exists():
            return None, f"Arquivo de mapa não encontrado: {caminho_shapefile}"
        
        # Instancia finder
        finder = get_zone_finder(caminho_shapefile)
        
        # Geocoding
        lat, lon, geo_error = finder.geocoder.geocode(endereco)
        
        if lat is None or lon is None:
            return None, geo_error or "Não foi possível geocodificar o endereço"
        
        logger.info(f"Coordenadas encontradas: {lat}, {lon}")
        
        # Busca zona
        zona, zone_error = finder.find_zone(lat, lon)
        
        if zona:
            logger.info(f"Zona encontrada: {zona}")
            return zona, zone_error  # zone_error pode ser None ou warning
        else:
            return None, zone_error or "Zona não encontrada"
    
    except Exception as e:
        logger.error(f"Erro geral na busca de zona: {e}")
        return None, f"Erro interno: {str(e)}"

class ZoneParameterValidator:
    """Validador de parâmetros por zona com regras configuráveis"""
    
    def __init__(self, rules_file: Optional[Path] = None):
        self.rules = self._load_rules(rules_file)
    
    def _load_rules(self, rules_file: Optional[Path]) -> Dict:
        """Carrega regras de validação"""
        default_rules = {
            "ZR1": {
                "taxa_ocupacao_max": 50,
                "coeficiente_aproveitamento_max": 1.0,
                "altura_max": 7.5,
                "recuo_frontal_min": 4.0,
                "recuos_laterais_min": 1.5,
                "recuo_fundos_min": 3.0,
                "area_permeavel_min": 30
            },
            "ZR2": {
                "taxa_ocupacao_max": 60,
                "coeficiente_aproveitamento_max": 1.5,
                "altura_max": 12.0,
                "recuo_frontal_min": 4.0,
                "recuos_laterais_min": 1.5,
                "recuo_fundos_min": 3.0,
                "area_permeavel_min": 25
            },
            # Adicionar mais zonas conforme necessário
        }
        
        if rules_file and rules_file.exists():
            try:
                with open(rules_file, 'r', encoding='utf-8') as f:
                    loaded_rules = json.load(f)
                    default_rules.update(loaded_rules)
                logger.info(f"Regras carregadas de: {rules_file}")
            except Exception as e:
                logger.warning(f"Erro ao carregar regras: {e}")
        
        return default_rules
    
    def validate_parameters(self, zona: str, parametros: Dict[str, float]) -> Dict[str, Any]:
        """Valida parâmetros contra regras da zona"""
        zona_clean = zona.upper().replace("-", "").replace(" ", "")
        
        # Busca regras da zona (com fallbacks)
        zone_rules = None
        for zone_key in self.rules:
            if zone_key.upper().replace("-", "").replace(" ", "") == zona_clean:
                zone_rules = self.rules[zone_key]
                break
        
        if not zone_rules:
            return {
                "valid": False,
                "error": f"Regras não encontradas para zona {zona}",
                "available_zones": list(self.rules.keys())
            }
        
        # Executa validações
        validation_results = {
            "valid": True,
            "zona": zona,
            "violations": [],
            "warnings": [],
            "summary": {}
        }
        
        for param, value in parametros.items():
            if value is None:
                continue
            
            result = self._validate_single_parameter(param, value, zone_rules)
            validation_results["summary"][param] = result
            
            if not result["valid"]:
                validation_results["valid"] = False
                validation_results["violations"].append(result)
            elif result.get("warning"):
                validation_results["warnings"].append(result)
        
        return validation_results
    
    def _validate_single_parameter(self, param: str, value: float, rules: Dict) -> Dict[str, Any]:
        """Valida um parâmetro individual"""
        result = {
            "parameter": param,
            "value": value,
            "valid": True,
            "message": "OK"
        }
        
        # Mapeamento de parâmetros para regras
        param_mapping = {
            "taxa_ocupacao": "taxa_ocupacao_max",
            "coeficiente_aproveitamento": "coeficiente_aproveitamento_max", 
            "altura_edificacao": "altura_max",
            "recuo_frontal": "recuo_frontal_min",
            "recuos_laterais": "recuos_laterais_min",
            "recuo_fundos": "recuo_fundos_min",
            "area_permeavel": "area_permeavel_min"
        }
        
        rule_key = param_mapping.get(param)
        if not rule_key or rule_key not in rules:
            result["warning"] = f"Regra não encontrada para {param}"
            return result
        
        limit_value = rules[rule_key]
        
        # Valida conforme tipo de regra
        if "max" in rule_key:
            if value > limit_value:
                result["valid"] = False
                result["message"] = f"Valor {value} excede limite máximo de {limit_value}"
            else:
                result["message"] = f"OK (máximo: {limit_value})"
        
        elif "min" in rule_key:
            if value < limit_value:
                result["valid"] = False
                result["message"] = f"Valor {value} abaixo do mínimo de {limit_value}"
            else:
                result["message"] = f"OK (mínimo: {limit_value})"
        
        result["limit"] = limit_value
        return result

# Cache para validador
_validator = None

def get_parameter_validator(rules_file: Optional[Path] = None) -> ZoneParameterValidator:
    """Retorna instância singleton do validador"""
    global _validator
    if _validator is None:
        _validator = ZoneParameterValidator(rules_file)
    return _validator

def validate_project_parameters(zona: str, parametros: Dict[str, float]) -> Dict[str, Any]:
    """Função utilitária para validação de parâmetros"""
    validator = get_parameter_validator()
    return validator.validate_parameters(zona, parametros)

# Função para limpeza de cache
def clear_caches():
    """Limpa todos os caches em memória"""
    global _zone_finder, _validator
    
    if _zone_finder:
        _zone_finder.find_zone.cache_clear()
    
    _zone_finder = None
    _validator = None
    
    logger.info("Caches limpos")

# Função para estatísticas
def get_geocoding_stats() -> Dict[str, int]:
    """Retorna estatísticas de geocoding"""
    global _zone_finder
    if _zone_finder and hasattr(_zone_finder, 'geocoder'):
        return _zone_finder.geocoder.get_stats()
    return {"cache_hits": 0, "api_calls": 0, "errors": 0}

# Context manager para gerenciamento de recursos
class GeoResourceManager:
    """Context manager para gerenciar recursos geoespaciais"""
    
    def __init__(self, shapefile_path: Path):
        self.shapefile_path = shapefile_path
        self.finder = None
    
    def __enter__(self):
        self.finder = OptimizedZoneFinder(self.shapefile_path)
        return self.finder
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.finder and hasattr(self.finder.geocoder, '_save_cache'):
            self.finder.geocoder._save_cache()
        clear_caches()