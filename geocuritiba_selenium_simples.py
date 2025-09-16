# Versão simplificada que acessa diretamente a API do GeoCuritiba via Selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def geocodificar_endereco(endereco: str) -> dict:
    """Usa a API do Nominatim para geocodificar o endereço"""
    try:
        # URL da API de geocodificação do OpenStreetMap Nominatim
        url = f"https://nominatim.openstreetmap.org/search"
        params = {
            'q': f"{endereco}, Curitiba, Paraná, Brasil",
            'format': 'json',
            'limit': 1
        }
        
        headers = {
            'User-Agent': 'GeoCuritibaScraper/1.0'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()
        
        if data:
            lat = float(data[0]['lat'])
            lon = float(data[0]['lon'])
            
            # Converter para coordenadas UTM usando pyproj
            from pyproj import Proj, transform
            
            # WGS84 (EPSG:4326) para SIRGAS 2000 UTM Zone 22S (EPSG:31982)
            wgs84 = Proj(init='epsg:4326')
            utm22s = Proj(init='epsg:31982')
            
            x_utm, y_utm = transform(wgs84, utm22s, lon, lat)
            
            logger.info(f"Coordenadas encontradas: Lat={lat}, Lon={lon} -> X={x_utm}, Y={y_utm}")
            
            return {
                'sucesso': True,
                'lat': lat,
                'lon': lon,
                'x_utm': x_utm,
                'y_utm': y_utm
            }
    except Exception as e:
        logger.error(f"Erro na geocodificação: {e}")
    
    return {'sucesso': False, 'erro': 'Não foi possível geocodificar o endereço'}

def consultar_api_geocuritiba_selenium(x: float, y: float) -> dict:
    """Usa Selenium para acessar a API do GeoCuritiba"""
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    
    # Configurações específicas para produção (Streamlit Cloud)
    import os
    if os.getenv('STREAMLIT_SERVER_PORT'):  # Ambiente de produção
        options.binary_location = '/usr/bin/chromium'
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-images')
        options.add_argument('--disable-javascript')
        options.add_argument('--disable-plugins')
    
    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        
        # URL da API Layer 36 do GeoCuritiba - MapaCadastral
        url = "https://geocuritiba.ippuc.org.br/server/rest/services/GeoCuritiba/Publico_GeoCuritiba_MapaCadastral/MapServer/36/query"
        
        # Parâmetros da consulta
        params = {
            'f': 'json',
            'geometry': f'{{"x":{x},"y":{y},"spatialReference":{{"wkid":31982}}}}',
            'geometryType': 'esriGeometryPoint', 
            'spatialRel': 'esriSpatialRelIntersects',
            'outFields': '*',
            'returnGeometry': 'false'
        }
        
        # Construir URL completa
        param_string = '&'.join([f'{k}={v}' for k, v in params.items()])
        url_completa = f"{url}?{param_string}"
        
        logger.info(f"Acessando API: {url_completa}")
        
        # Navegar para a URL
        driver.get(url_completa)
        
        # Aguardar e extrair o JSON com timeout mais robusto
        import time
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By
        
        # Aguardar até que a página carregue completamente
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "pre"))
            )
        except:
            time.sleep(5)  # Fallback
        
        # Pegar o conteúdo da página
        page_source = driver.page_source
        
        # Log do conteúdo para debug
        logger.info(f"Conteúdo da página: {page_source[:500]}...")
        
        # Extrair JSON do <pre> tag
        if '<pre>' in page_source and '</pre>' in page_source:
            json_start = page_source.find('<pre>') + 5
            json_end = page_source.find('</pre>')
            json_text = page_source[json_start:json_end].strip()
            
            logger.info(f"JSON extraído: {json_text}")
            
            try:
                api_response = json.loads(json_text)
                return {'sucesso': True, 'dados': api_response}
            except json.JSONDecodeError as e:
                logger.error(f"Erro ao parsear JSON: {e}")
                return {'sucesso': False, 'erro': f'Erro no JSON: {e}'}
        else:
            logger.error(f"Formato de resposta inesperado: {page_source}")
            return {'sucesso': False, 'erro': 'Formato de resposta inesperado'}
            
    except Exception as e:
        logger.error(f"Erro na consulta Selenium: {e}")
        return {'sucesso': False, 'erro': str(e)}
    finally:
        if driver:
            driver.quit()

def buscar_zoneamento_selenium(endereco: str) -> dict:
    """Função principal que combina geocodificação e consulta à API"""
    logger.info(f"Iniciando busca para: {endereco}")
    
    # 1. Geocodificar endereço
    geo_result = geocodificar_endereco(endereco)
    if not geo_result['sucesso']:
        return geo_result
    
    # 2. Consultar API do GeoCuritiba
    api_result = consultar_api_geocuritiba_selenium(geo_result['x_utm'], geo_result['y_utm'])
    if not api_result['sucesso']:
        return api_result
    
    # 3. Processar resposta da API
    try:
        api_data = api_result['dados']
        features = api_data.get('features', [])
        
        if not features:
            return {
                'sucesso': False,
                'erro': 'Nenhum zoneamento encontrado para as coordenadas fornecidas'
            }
        
        # Pegar primeiro feature (zona principal)
        feature = features[0]
        attributes = feature.get('attributes', {})
        
        # Extrair dados relevantes (campos corretos do GeoCuritiba)
        sigla_zona = attributes.get('sg_zona', 'N/D')  
        nome_zona = attributes.get('nm_zona', f'Zona {sigla_zona}')
        
        # Parâmetros padrão baseados na zona
        parametros_default = {
            'coef_aproveitamento_basico': 1.0,
            'taxa_ocupacao_maxima': 50.0,
            'altura_maxima_pavimentos': 4,
            'recuo_frontal_minimo': 5.0,
            'taxa_permeabilidade_minima': 25.0
        }
        
        # Parâmetros específicos por zona baseados na Lei 15.511/2019
        if sigla_zona == 'ZC':  # Zona Central
            parametros_default.update({
                'coef_aproveitamento_basico': 6.0,
                'taxa_ocupacao_maxima': 100.0,
                'altura_maxima_pavimentos': 12,
                'recuo_frontal_minimo': 0.0,
                'taxa_permeabilidade_minima': 15.0
            })
        elif sigla_zona.startswith('ZR-1'):  # Zona Residencial 1
            parametros_default.update({
                'coef_aproveitamento_basico': 1.0,
                'taxa_ocupacao_maxima': 50.0,
                'altura_maxima_pavimentos': 2,
                'recuo_frontal_minimo': 5.0,
                'taxa_permeabilidade_minima': 30.0
            })
        elif sigla_zona.startswith('ZR-2'):  # Zona Residencial 2
            parametros_default.update({
                'coef_aproveitamento_basico': 1.4,
                'taxa_ocupacao_maxima': 60.0,
                'altura_maxima_pavimentos': 4,
                'recuo_frontal_minimo': 4.0,
                'taxa_permeabilidade_minima': 25.0
            })
        elif sigla_zona.startswith('ZR-3'):  # Zona Residencial 3
            parametros_default.update({
                'coef_aproveitamento_basico': 2.0,
                'taxa_ocupacao_maxima': 70.0,
                'altura_maxima_pavimentos': 6,
                'recuo_frontal_minimo': 4.0,
                'taxa_permeabilidade_minima': 20.0
            })
        elif sigla_zona.startswith('ZR-4'):  # Zona Residencial 4
            parametros_default.update({
                'coef_aproveitamento_basico': 2.5,
                'taxa_ocupacao_maxima': 70.0,
                'altura_maxima_pavimentos': 8,
                'recuo_frontal_minimo': 3.0,
                'taxa_permeabilidade_minima': 20.0
            })
        elif sigla_zona.startswith('ZC-'):  # Zonas Centrais específicas
            parametros_default.update({
                'coef_aproveitamento_basico': 6.0,
                'taxa_ocupacao_maxima': 100.0,
                'altura_maxima_pavimentos': 15,
                'recuo_frontal_minimo': 0.0,
                'taxa_permeabilidade_minima': 15.0
            })
        elif 'ZS' in sigla_zona:  # Zona de Serviços
            parametros_default.update({
                'coef_aproveitamento_basico': 2.0,
                'taxa_ocupacao_maxima': 70.0,
                'altura_maxima_pavimentos': 6,
                'recuo_frontal_minimo': 5.0,
                'taxa_permeabilidade_minima': 20.0
            })
        
        return {
            'sucesso': True,
            'zona_principal': f"{sigla_zona} - {nome_zona}",
            'fonte': 'API GeoCuritiba Layer 36 via Selenium',
            'coordenadas': {
                'lat': geo_result['lat'],
                'lon': geo_result['lon'],
                'x_utm': geo_result['x_utm'], 
                'y_utm': geo_result['y_utm']
            },
            'parametros': parametros_default,
            'todas_zonas_incidentes': [f"{sigla_zona} - {nome_zona}"],
            'dados_brutos': attributes
        }
        
    except Exception as e:
        logger.error(f"Erro ao processar resposta da API: {e}")
        return {
            'sucesso': False,
            'erro': f'Erro ao processar dados: {str(e)}'
        }

if __name__ == "__main__":
    # Teste
    endereco_teste = "Rua XV de Novembro, 500, Centro, Curitiba"
    print(f"Testando com: {endereco_teste}")
    
    resultado = buscar_zoneamento_selenium(endereco_teste)
    print(json.dumps(resultado, indent=2, ensure_ascii=False))