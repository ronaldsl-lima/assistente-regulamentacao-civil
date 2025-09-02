# config.py - Configurações Centralizadas Otimizadas

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import logging
from enum import Enum

# Configuração de ambiente
ENV = os.getenv("ENVIRONMENT", "development")
PROJECT_ROOT = Path(__file__).parent

class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

@dataclass
class DatabaseConfig:
    """Configurações do banco vetorial"""
    persist_directory: Path = PROJECT_ROOT / "db"
    collection_prefix: str = "regulamentacao"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chunk_size: int = 1500
    chunk_overlap: int = 300
    max_docs_per_query: int = 7
    similarity_threshold: float = 0.7

@dataclass
class LLMConfig:
    """Configurações do modelo de linguagem"""
    model_name: str = "gemini-1.5-pro-latest"
    temperature: float = 0.1
    max_tokens: int = 4096
    timeout: int = 60
    max_retries: int = 3
    retry_delay: float = 1.0

@dataclass
class GeoConfig:
    """Configurações geoespaciais"""
    cache_dir: Path = PROJECT_ROOT / "cache" / "geo"
    nominatim_user_agent: str = "assistente_regulatorio_v6"
    request_timeout: int = 10
    max_retries: int = 3
    backoff_factor: float = 0.3
    cache_expiry_hours: int = 168  # 1 semana

@dataclass
class ProcessingConfig:
    """Configurações de processamento"""
    max_workers: int = 4
    batch_size: int = 50
    memory_limit_mb: int = 2048
    pdf_extraction_timeout: int = 300
    enable_ocr: bool = False
    ocr_languages: List[str] = field(default_factory=lambda: ['por'])

@dataclass
class CacheConfig:
    """Configurações de cache"""
    enable_memory_cache: bool = True
    enable_disk_cache: bool = True
    memory_cache_size: int = 1000
    disk_cache_dir: Path = PROJECT_ROOT / "cache" / "app"
    cache_ttl_seconds: int = 3600  # 1 hora
    cleanup_interval_hours: int = 24

@dataclass
class SecurityConfig:
    """Configurações de segurança"""
    max_file_size_mb: int = 50
    allowed_file_types: List[str] = field(default_factory=lambda: ['.pdf'])
    rate_limit_per_minute: int = 60
    enable_request_logging: bool = True

@dataclass
class UIConfig:
    """Configurações da interface"""
    page_title: str = "Assistente Regulatório v6.0"
    page_icon: str = "🏗️"
    layout: str = "wide"
    theme: Dict[str, str] = field(default_factory=lambda: {
        'primaryColor': '#FF6B6B',
        'backgroundColor': '#FFFFFF',
        'secondaryBackgroundColor': '#F0F2F6',
        'textColor': '#262730'
    })

@dataclass
class MonitoringConfig:
    """Configurações de monitoramento"""
    enable_metrics: bool = True
    metrics_file: Path = PROJECT_ROOT / "logs" / "metrics.json"
    log_level: LogLevel = LogLevel.INFO
    log_file: Path = PROJECT_ROOT / "logs" / "app.log"
    enable_performance_tracking: bool = True

@dataclass
class AppConfig:
    """Configuração principal da aplicação"""
    version: str = "6.0"
    environment: str = ENV
    debug: bool = ENV == "development"
    
    # Sub-configurações
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    geo: GeoConfig = field(default_factory=GeoConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    
    # Diretórios principais
    data_dir: Path = PROJECT_ROOT / "dados"
    maps_dir: Path = PROJECT_ROOT / "mapas"
    logs_dir: Path = PROJECT_ROOT / "logs"
    
    def __post_init__(self):
        """Inicialização pós-criação"""
        # Cria diretórios necessários
        self._create_directories()
        
        # Configura logging
        self._setup_logging()
        
        # Valida configurações
        self._validate_config()
    
    def _create_directories(self):
        """Cria diretórios necessários"""
        directories = [
            self.database.persist_directory,
            self.geo.cache_dir,
            self.cache.disk_cache_dir,
            self.logs_dir,
            self.data_dir,
            self.maps_dir
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _setup_logging(self):
        """Configura sistema de logging"""
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # Handler para arquivo
        file_handler = logging.FileHandler(self.monitoring.log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(log_format))
        
        # Handler para console
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(log_format))
        
        # Configuração do logger principal
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.monitoring.log_level.value))
        
        # Remove handlers existentes para evitar duplicação
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
    
    def _validate_config(self):
        """Valida configurações"""
        errors = []
        
        # Validações básicas
        if self.database.chunk_size <= 0:
            errors.append("chunk_size deve ser positivo")
        
        if self.llm.temperature < 0 or self.llm.temperature > 1:
            errors.append("temperature deve estar entre 0 e 1")
        
        if not self.data_dir.exists():
            logging.warning(f"Diretório de dados não encontrado: {self.data_dir}")
        
        if errors:
            raise ValueError(f"Configurações inválidas: {'; '.join(errors)}")
    
    def get_city_config(self, city: str) -> Dict[str, Any]:
        """Retorna configurações específicas para uma cidade"""
        city_lower = city.lower()
        
        # Configurações específicas por cidade (pode ser carregado de arquivo)
        city_configs = {
            "curitiba": {
                "shapefile": "feature_20250828120625247331.shp",
                "encoding": "utf-8",
                "zone_column": "ZONA",
                "special_rules": {}
            },
            "default": {
                "shapefile": "default.shp",
                "encoding": "utf-8", 
                "zone_column": "zona",
                "special_rules": {}
            }
        }
        
        return city_configs.get(city_lower, city_configs["default"])
    
    def get_database_url(self, city: str) -> str:
        """Retorna URL do banco para uma cidade"""
        collection_name = f"{self.database.collection_prefix}_{city.lower()}"
        return str(self.database.persist_directory / collection_name)
    
    def get_shapefile_path(self, city: str) -> Path:
        """Retorna caminho do shapefile para uma cidade"""
        city_config = self.get_city_config(city)
        return self.maps_dir / city_config["shapefile"]
    
    @classmethod
    def from_env(cls) -> 'AppConfig':
        """Carrega configurações de variáveis de ambiente"""
        config = cls()
        
        # Sobrescreve configurações com variáveis de ambiente
        if os.getenv("GEMINI_API_KEY"):
            os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")
        
        if os.getenv("EMBEDDING_MODEL"):
            config.database.embedding_model = os.getenv("EMBEDDING_MODEL")
        
        if os.getenv("LLM_MODEL"):
            config.llm.model_name = os.getenv("LLM_MODEL")
        
        if os.getenv("CHUNK_SIZE"):
            config.database.chunk_size = int(os.getenv("CHUNK_SIZE"))
        
        if os.getenv("MAX_WORKERS"):
            config.processing.max_workers = int(os.getenv("MAX_WORKERS"))
        
        if os.getenv("ENABLE_DEBUG"):
            config.debug = os.getenv("ENABLE_DEBUG").lower() == "true"
        
        if os.getenv("LOG_LEVEL"):
            try:
                config.monitoring.log_level = LogLevel(os.getenv("LOG_LEVEL").upper())
            except ValueError:
                pass
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte configuração para dicionário"""
        def convert_value(value):
            if isinstance(value, Path):
                return str(value)
            elif isinstance(value, Enum):
                return value.value
            elif hasattr(value, '__dict__'):
                return {k: convert_value(v) for k, v in value.__dict__.items()}
            return value
        
        return {k: convert_value(v) for k, v in self.__dict__.items()}

# Configurações de perfil de performance
PERFORMANCE_PROFILES = {
    "development": {
        "max_workers": 2,
        "chunk_size": 1000,
        "enable_cache": True,
        "log_level": LogLevel.DEBUG
    },
    "production": {
        "max_workers": 8,
        "chunk_size": 1500,
        "enable_cache": True,
        "log_level": LogLevel.INFO
    },
    "memory_optimized": {
        "max_workers": 1,
        "chunk_size": 800,
        "batch_size": 20,
        "memory_limit_mb": 1024
    },
    "speed_optimized": {
        "max_workers": 12,
        "chunk_size": 2000,
        "batch_size": 100,
        "enable_cache": True
    }
}

def get_config(profile: Optional[str] = None) -> AppConfig:
    """Factory function para obter configuração"""
    config = AppConfig.from_env()
    
    # Aplica perfil se especificado
    if profile and profile in PERFORMANCE_PROFILES:
        profile_config = PERFORMANCE_PROFILES[profile]
        
        # Aplica configurações do perfil
        if "max_workers" in profile_config:
            config.processing.max_workers = profile_config["max_workers"]
        
        if "chunk_size" in profile_config:
            config.database.chunk_size = profile_config["chunk_size"]
        
        if "batch_size" in profile_config:
            config.processing.batch_size = profile_config["batch_size"]
        
        if "memory_limit_mb" in profile_config:
            config.processing.memory_limit_mb = profile_config["memory_limit_mb"]
        
        if "enable_cache" in profile_config:
            config.cache.enable_memory_cache = profile_config["enable_cache"]
            config.cache.enable_disk_cache = profile_config["enable_cache"]
        
        if "log_level" in profile_config:
            config.monitoring.log_level = profile_config["log_level"]
    
    return config

# Configurações de zona específicas (pode ser movido para arquivo JSON)
ZONE_PARAMETERS = {
    "ZR1": {
        "name": "Zona Residencial 1",
        "description": "Zona de baixa densidade",
        "parameters": {
            "taxa_ocupacao_max": 50.0,
            "coeficiente_aproveitamento_max": 1.0,
            "altura_max": 7.5,
            "recuo_frontal_min": 4.0,
            "recuos_laterais_min": 1.5,
            "recuo_fundos_min": 3.0,
            "area_permeavel_min": 30.0
        }
    },
    "ZR2": {
        "name": "Zona Residencial 2", 
        "description": "Zona de média densidade",
        "parameters": {
            "taxa_ocupacao_max": 60.0,
            "coeficiente_aproveitamento_max": 1.5,
            "altura_max": 12.0,
            "recuo_frontal_min": 4.0,
            "recuos_laterais_min": 1.5,
            "recuo_fundos_min": 3.0,
            "area_permeavel_min": 25.0
        }
    },
    "ZR3": {
        "name": "Zona Residencial 3",
        "description": "Zona de alta densidade",
        "parameters": {
            "taxa_ocupacao_max": 70.0,
            "coeficiente_aproveitamento_max": 2.5,
            "altura_max": 24.0,
            "recuo_frontal_min": 4.0,
            "recuos_laterais_min": 1.5,
            "recuo_fundos_min": 3.0,
            "area_permeavel_min": 20.0
        }
    },
    "ZC": {
        "name": "Zona Central",
        "description": "Zona comercial central",
        "parameters": {
            "taxa_ocupacao_max": 80.0,
            "coeficiente_aproveitamento_max": 4.0,
            "altura_max": 48.0,
            "recuo_frontal_min": 0.0,
            "recuos_laterais_min": 0.0,
            "recuo_fundos_min": 3.0,
            "area_permeavel_min": 15.0
        }
    },
    "ZS": {
        "name": "Zona de Serviços",
        "description": "Zona de atividades de serviços",
        "parameters": {
            "taxa_ocupacao_max": 70.0,
            "coeficiente_aproveitamento_max": 2.0,
            "altura_max": 16.0,
            "recuo_frontal_min": 4.0,
            "recuos_laterais_min": 1.5,
            "recuo_fundos_min": 3.0,
            "area_permeavel_min": 20.0
        }
    }
}

# Templates de prompts otimizados
PROMPT_TEMPLATES = {
    "analysis_standard": """
    Você é um especialista em análise de conformidade urbanística com 20 anos de experiência.
    
    CONTEXTO DA LEGISLAÇÃO:
    {context}
    
    ANÁLISE SOLICITADA:
    {question}
    
    INSTRUÇÕES CRÍTICAS:
    1. Extraia EXATAMENTE os valores do projeto do memorial fornecido
    2. Identifique os limites da legislação nos documentos de contexto
    3. Compare numericamente cada parâmetro
    4. Use APENAS "✅ Conforme" ou "❌ Não Conforme" na coluna Conformidade
    5. Seja CONCLUSIVO no parecer final sobre aprovação/reprovação
    
    FORMATO OBRIGATÓRIO:
    
    ## 1. Identificação do Projeto
    - **Endereço:** {endereco}
    - **Zona de Uso:** {zona}
    - **Data da Análise:** {data_analise}
    
    ## 2. Análise dos Parâmetros
    
    | Parâmetro | Valor no Projeto | Valor Máximo Permitido | Conformidade | Observação |
    |---|---|---|---|---|
    | Taxa de Ocupação | [valor]% | [valor]% | ✅/❌ | [obs] |
    | Coeficiente de Aproveitamento | [valor] | [valor] | ✅/❌ | [obs] |
    | Altura da Edificação | [valor]m | [valor]m | ✅/❌ | [obs] |
    | Recuo Frontal | [valor]m | [valor]m | ✅/❌ | [obs] |
    | Recuos Laterais | [valor]m | [valor]m | ✅/❌ | [obs] |
    | Recuo de Fundos | [valor]m | [valor]m | ✅/❌ | [obs] |
    | Área Permeável | [valor]% | [valor]% | ✅/❌ | [obs] |
    
    ## 3. Parecer Final
    [Conclusão sobre conformidade - APROVADO ou REPROVADO]
    
    ## 4. Recomendações
    [Ajustes necessários ou "Nenhuma recomendação necessária"]
    """,
    
    "analysis_detailed": """
    Você é um consultor sênior em regulamentação urbanística com expertise em análise técnica detalhada.
    
    DOCUMENTOS DA LEGISLAÇÃO:
    {context}
    
    PROJETO PARA ANÁLISE:
    {question}
    
    EXECUTE UMA ANÁLISE TÉCNICA COMPLETA:
    
    1. **IDENTIFICAÇÃO TÉCNICA**
       - Localização e zoneamento
       - Classificação do uso pretendido
       - Normativas aplicáveis
    
    2. **ANÁLISE PARAMÉTRICA DETALHADA**
       - Cálculos de verificação
       - Margem de segurança
       - Pontos críticos identificados
    
    3. **AVALIAÇÃO JURÍDICA**
       - Base legal de cada parâmetro
       - Interpretação normativa
       - Precedentes relevantes
    
    4. **PARECER TÉCNICO CONCLUSIVO**
       - Conformidade geral
       - Riscos identificados
       - Recomendações específicas
       
    5. **DOCUMENTAÇÃO ADICIONAL**
       - Referências normativas
       - Cálculos detalhados
       - Sugestões de adequação
    
    [Desenvolva cada seção com rigor técnico e embase legal]
    """
}

# Configurações de exportação
EXPORT_FORMATS = {
    "pdf": {
        "enabled": True,
        "template": "report_template.html",
        "options": {
            "page_size": "A4",
            "margin_top": "2cm",
            "margin_bottom": "2cm",
            "margin_left": "2cm", 
            "margin_right": "2cm",
            "encoding": "UTF-8"
        }
    },
    "docx": {
        "enabled": True,
        "template": "report_template.docx",
        "options": {
            "style": "Normal",
            "font_name": "Calibri",
            "font_size": 11
        }
    },
    "excel": {
        "enabled": True,
        "sheets": ["Resumo", "Parametros", "Detalhado"],
        "options": {
            "auto_adjust_width": True,
            "freeze_panes": True
        }
    }
}

# Configurações de integração
INTEGRATION_CONFIG = {
    "apis": {
        "ibge": {
            "base_url": "https://servicodados.ibge.gov.br/api/v1",
            "timeout": 10,
            "cache_hours": 168
        },
        "nominatim": {
            "base_url": "https://nominatim.openstreetmap.org",
            "timeout": 10,
            "rate_limit": 1  # requests per second
        }
    },
    "external_services": {
        "enable_weather": False,
        "enable_traffic": False,
        "enable_demographics": True
    }
}

# Configurações de qualidade de dados
DATA_QUALITY_CONFIG = {
    "pdf_validation": {
        "min_pages": 1,
        "max_pages": 1000,
        "min_content_length": 100,
        "required_keywords": ["taxa", "ocupação", "aproveitamento"]
    },
    "address_validation": {
        "min_length": 5,
        "required_parts": ["rua", "numero"],
        "normalize": True
    },
    "parameter_validation": {
        "ranges": {
            "taxa_ocupacao": (0, 100),
            "coeficiente_aproveitamento": (0, 10),
            "altura_edificacao": (0, 200),
            "recuo_frontal": (0, 50),
            "recuos_laterais": (0, 20),
            "recuo_fundos": (0, 30),
            "area_permeavel": (0, 100)
        }
    }
}

# Instância global de configuração
_config_instance = None

def get_global_config() -> AppConfig:
    """Retorna instância singleton da configuração global"""
    global _config_instance
    if _config_instance is None:
        profile = os.getenv("PERFORMANCE_PROFILE")
        _config_instance = get_config(profile)
    return _config_instance

def reload_config():
    """Recarrega configuração global"""
    global _config_instance
    _config_instance = None
    return get_global_config()

# Context manager para configuração temporária
class ConfigOverride:
    """Context manager para sobrescrever configurações temporariamente"""
    
    def __init__(self, **overrides):
        self.overrides = overrides
        self.original_values = {}
    
    def __enter__(self):
        config = get_global_config()
        
        # Salva valores originais e aplica overrides
        for key, value in self.overrides.items():
            if hasattr(config, key):
                self.original_values[key] = getattr(config, key)
                setattr(config, key, value)
        
        return config
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        config = get_global_config()
        
        # Restaura valores originais
        for key, value in self.original_values.items():
            setattr(config, key, value)