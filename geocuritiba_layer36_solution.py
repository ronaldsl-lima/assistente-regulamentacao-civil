import requests
import json
import re
import logging
import os

# Configuração do logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- ESTRUTURA DE DADOS PARA CONFIGURAÇÃO DAS CAMADAS ---
LAYERS_CONFIG = [
    # --- PRIORIDADE 1: RESTRIÇÕES AMBIENTAIS ---
    {
        "nome": "APA do Iguaçu", "layer_id": 27, "prioridade": 1,
        "parametros_fixos": {
            'sigla_zona': "APA-IGUAÇU", 'nome_zona': "ÁREA DE PROTEÇÃO AMBIENTAL DO IGUAÇU",
            'observacao': "Restrições ambientais severas. Parâmetros construtivos definidos por legislação específica da APA."
        }
    },
    {
        "nome": "APA do Passaúna", "layer_id": 28, "prioridade": 1,
        "parametros_fixos": {
            'sigla_zona': "APA-PASSAÚNA", 'nome_zona': "ÁREA DE PROTEÇÃO AMBIENTAL DO PASSAÚNA",
            'observacao': "Restrições ambientais severas. Parâmetros construtivos definidos por legislação específica da APA."
        }
    },
    # --- PRIORIDADE 2: SETORES ESPECIAIS ---
    {
        "nome": "SEHIS", "layer_id": 26, "prioridade": 2,
        "parametros_fixos": {
            'sigla_zona': "SEHIS", 'nome_zona': 'SETOR ESPECIAL DE HABITAÇÃO DE INTERESSE SOCIAL',
            'coef_aproveitamento_basico': 2.0, 'taxa_ocupacao_maxima': 70.0, 'altura_maxima_pavimentos': 4,
            'recuo_frontal_minimo': 0.0, 'taxa_permeabilidade_minima': 10.0,
            'observacao': 'Parâmetros baseados em regulamentação específica para SEHIS. Consultar decreto.'
        }
    },
    {
        "nome": "Setor Especial Parque Tanguá", "layer_id": 32, "prioridade": 2,
        "parametros_fixos": { 'sigla_zona': "SE-TANGUÁ", 'nome_zona': "SETOR ESPECIAL DO PARQUE TANGUÁ", 'observacao': "Parâmetros definidos por norma própria." }
    },
    {
        "nome": "Setor Especial Vila de Ofícios", "layer_id": 33, "prioridade": 2,
         "parametros_fixos": { 'sigla_zona': "SE-OFÍCIOS", 'nome_zona': "SETOR ESPECIAL VILA DE OFÍCIOS", 'observacao': "Parâmetros definidos por norma própria." }
    },
    {
        "nome": "Setor Especial Preferencial de Pedestre", "layer_id": 30, "prioridade": 2,
        "parametros_fixos": { 'sigla_zona': "SE-PEDESTRE", 'nome_zona': "SETOR ESPECIAL PREFERENCIAL DE PEDESTRE", 'observacao': "Parâmetros definidos por norma própria." }
    },
    {
        "nome": "Setor Especial Pontos Panorâmicos", "layer_id": 31, "prioridade": 2,
        "parametros_fixos": { 'sigla_zona': "SE-PANORÂMICO", 'nome_zona': "SETOR ESPECIAL DOS PONTOS PANORÂMICOS", 'observacao': "Parâmetros definidos por norma própria." }
    },
    # --- PRIORIDADE 3: OPERAÇÕES URBANAS ---
    {
        "nome": "Operação Urbana Linha Verde", "layer_id": 29, "prioridade": 3,
        "parametros_fixos": {
            'sigla_zona': "OUC-LV", 'nome_zona': 'OPERAÇÃO URBANA CONSORCIADA LINHA VERDE',
            'coef_aproveitamento_basico': 1.0, 'coef_aproveitamento_maximo': 4.0, 'taxa_ocupacao_maxima': 50.0,
            'altura_maxima_pavimentos': 8, 'recuo_frontal_minimo': 5.0, 'taxa_permeabilidade_minima': 25.0,
            'observacao': 'Potencial adicional via CEPACs.'
        }
    },
    # --- PRIORIDADE 4: DIRETRIZES VIÁRIAS (INFORMATIVO) ---
    {
        "nome": "Sistema Viário", "layer_id": 34, "prioridade": 4, "parametros_dinamicos": True,
        "campos_dinamicos": { "sigla_zona": "TIPO_HIERARQUIA", "nome_zona": "NOME_RUA" },
        'observacao_base': 'Lote confronta com via do Sistema Viário Classificado. Verificar legislação específica.'
    },
    # --- PRIORIDADE 99: ZONEAMENTO BASE (FALLBACK) ---
    { "nome": "Zoneamento Base", "layer_id": 36, "prioridade": 99, "parametros_dinamicos": True }
]
URL_BASE_MAPA_CADASTRAL = "https://geocuritiba.ippuc.org.br/server/rest/services/GeoCuritiba/Publico_GeoCuritiba_MapaCadastral/MapServer"

def _make_api_request(url: str, params: dict, timeout: int = 25) -> dict:
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, params=params, timeout=timeout, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as req_err:
        raise ConnectionError(f"Erro na requisição à API: {req_err}")

def _geocode_address(address: str) -> dict:
    """Converte um endereço em coordenadas usando a nova API de geocodificação."""
    logger.info(f"A geocodificar o endereço: {address}")

    # Tentar primeiro com a nova API
    try:
        return _try_new_geocoding_api(address)
    except Exception as e:
        logger.warning(f"Erro na nova API: {e}. Tentando Nominatim...")
        return _try_nominatim(address)

def _try_new_geocoding_api(address: str) -> dict:
    """Tenta geocodificar usando a API PositionStack."""
    # Lê a chave de API das variáveis de ambiente do sistema
    api_key = os.getenv('POSITIONSTACK_API_KEY')

    if not api_key:
        # Fallback para desenvolvimento local
        api_key = "5d74e43398ad3ab452ad6472deb2d155"

    url = "http://api.positionstack.com/v1/forward"
    params = {
        'query': f"{address}, Curitiba, Brazil",
        'access_key': api_key,  # PositionStack usa 'access_key' como parâmetro
        'limit': 1,
        'country': 'BR'
    }

    logger.info(f"Testando PositionStack com parâmetros: {params}")
    data = _make_api_request(url, params)

    if not data.get('data'):
        raise ValueError("Não foi possível encontrar coordenadas para este endereço.")

    result = data['data'][0]

    return {
        'lat': float(result['latitude']),
        'lon': float(result['longitude']),
        'wkid': 4326  # WGS 84 (padrão de GPS)
    }

def _try_nominatim(address: str) -> dict:
    """Fallback: usa Nominatim (OpenStreetMap) como backup."""
    url = "https://nominatim.openstreetmap.org/search"
    params = {'q': f"{address}, Curitiba, Brazil", 'format': 'json', 'limit': 1}
    data = _make_api_request(url, params)
    if not data:
        raise ValueError("Não foi possível encontrar coordenadas para este endereço.")

    return {
        'lat': float(data[0]['lat']),
        'lon': float(data[0]['lon']),
        'wkid': 4326  # WGS 84 (padrão de GPS)
    }

def _get_lot_geometry_by_coords(coords: dict) -> dict:
    """Usa coordenadas para identificar a geometria do lote na API do GeoCuritiba."""
    logger.info(f"A identificar lote nas coordenadas: {coords}")

    url_identify = f"{URL_BASE_MAPA_CADASTRAL}/identify"

    # Tentar diferentes tolerâncias e sistemas de coordenadas
    tolerances = [50, 100, 200]  # Aumentar tolerância
    coordinate_systems = [4326, 31982]  # WGS84 e SIRGAS2000 UTM 22S

    for tolerance in tolerances:
        for sr in coordinate_systems:
            try:
                map_extent = f"{coords['lon']-0.01},{coords['lat']-0.01},{coords['lon']+0.01},{coords['lat']+0.01}"

                params = {
                    'f': 'json',
                    'geometry': f"{coords['lon']},{coords['lat']}",
                    'geometryType': 'esriGeometryPoint',
                    'sr': sr,
                    'layers': 'all',  # Tentar todas as camadas
                    'tolerance': tolerance,
                    'mapExtent': map_extent,
                    'imageDisplay': '400,400,96',
                    'returnGeometry': 'true'
                }

                logger.info(f"Tentando com tolerância {tolerance} e SR {sr}")
                data = _make_api_request(url_identify, params)

                if data.get('results'):
                    logger.info(f"Lote encontrado com tolerância {tolerance} e SR {sr}")
                    return data['results'][0].get('geometry')

            except Exception as e:
                logger.warning(f"Erro com tolerância {tolerance} e SR {sr}: {e}")
                continue

    # Se não encontrou nada, tentar busca mais ampla
    logger.warning("Lote não encontrado com parâmetros padrão, tentando busca ampla...")
    return None


def buscar_zoneamento_definitivo(endereco: str) -> dict:
    try:
        # 1. Geocodificar o endereço para obter coordenadas
        coordenadas = _geocode_address(endereco)

        # 2. Usar as coordenadas para obter a geometria do lote
        geometria_lote = _get_lot_geometry_by_coords(coordenadas)

        # Se não encontrou geometria específica, usar ponto das coordenadas
        if not geometria_lote:
            logger.warning("Usando coordenadas pontuais para consulta de zoneamento")
            geometria_lote = {
                "x": coordenadas['lon'],
                "y": coordenadas['lat'],
                "spatialReference": {"wkid": 4326}
            }
        
        zonas_encontradas = []

        # 3. Iterar sobre as camadas configuradas para encontrar sobreposições
        for layer_info in sorted(LAYERS_CONFIG, key=lambda x: x['prioridade']):
            url_camada = f"{URL_BASE_MAPA_CADASTRAL}/{layer_info['layer_id']}/query"
            # Determinar tipo de geometria baseado na estrutura
            if 'x' in geometria_lote and 'y' in geometria_lote:
                # É um ponto
                geometry_type = 'esriGeometryPoint'
                spatial_rel = 'esriSpatialRelIntersects'
                in_sr = '4326'
            else:
                # É um polígono
                geometry_type = 'esriGeometryPolygon'
                spatial_rel = 'esriSpatialRelIntersects'
                in_sr = '31982'

            params_camada = {
                'f': 'json', 'geometry': json.dumps(geometria_lote),
                'geometryType': geometry_type, 'spatialRel': spatial_rel,
                'inSR': in_sr, 'outFields': '*', 'returnGeometry': 'false'
            }
            camada_data = _make_api_request(url_camada, params_camada)

            if camada_data.get('features'):
                for feature in camada_data['features']:
                    attributes = feature['attributes']
                    parametros = {}
                    
                    if layer_info.get('parametros_fixos'):
                        parametros = layer_info['parametros_fixos'].copy()
                    elif layer_info.get('parametros_dinamicos'):
                        if layer_info['nome'] == 'Zoneamento Base':
                            parametros = {
                                'sigla_zona': attributes.get('sg_zona', 'N/A'),
                                'nome_zona': attributes.get('nm_zona', 'Não especificado'),
                                'coef_aproveitamento_basico': attributes.get('cd_ca_basico'),
                                'taxa_ocupacao_maxima': attributes.get('cd_to_maxima'),
                                'altura_maxima_pavimentos': attributes.get('cd_alt_max_pav'),
                                'recuo_frontal_minimo': attributes.get('cd_rec_frontal'),
                                'taxa_permeabilidade_minima': attributes.get('cd_tx_permea')
                            }
                        elif layer_info['nome'] == 'Sistema Viário':
                             parametros = {
                                'sigla_zona': attributes.get(layer_info['campos_dinamicos']['sigla_zona'], 'VIÁRIO'),
                                'nome_zona': attributes.get(layer_info['campos_dinamicos']['nome_zona'], 'Via Classificada'),
                                'observacao': layer_info['observacao_base']
                            }
                    
                    if parametros:
                        zonas_encontradas.append({
                            "nome_camada": layer_info["nome"],
                            "prioridade": layer_info["prioridade"],
                            "parametros": parametros
                        })

        if not zonas_encontradas:
            return {'sucesso': False, 'erro': 'Nenhum zoneamento foi encontrado para este lote.'}

        # 4. Determinar a zona principal e preparar o resultado
        zona_principal = min(zonas_encontradas, key=lambda x: x['prioridade'])
        info_zonas_incidentes = [f"{z['parametros'].get('sigla_zona', z['nome_camada'])} ({z['nome_camada']})" for z in zonas_encontradas]

        return {
            'sucesso': True, 'erro': None,
            'parametros': zona_principal['parametros'],
            'zona_principal': zona_principal['parametros'].get('sigla_zona', zona_principal['nome_camada']),
            'fonte': f"Camada Prioritária: {zona_principal['nome_camada']}",
            'todas_zonas_incidentes': info_zonas_incidentes,
            'coordenadas': f"{coordenadas['lat']:.6f}, {coordenadas['lon']:.6f}"
        }

    except (ConnectionError, ValueError) as e:
        return {'sucesso': False, 'erro': str(e)}
    except Exception as e:
        logger.error(f"Um erro inesperado ocorreu: {e}", exc_info=True)
        return {'sucesso': False, 'erro': 'Um erro inesperado ocorreu durante a análise.'}

