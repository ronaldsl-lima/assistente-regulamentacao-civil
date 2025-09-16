# arquivo: geocuritiba_selenium.py

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import json
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeoCuritibaScraper:
    """Automatiza o acesso ao GeoCuritiba para buscar dados de zoneamento"""
    
    def __init__(self, headless=True):
        """
        Inicializa o navegador
        headless=True: roda sem abrir janela (mais rápido)
        headless=False: abre janela para debug
        """
        self.options = Options()
        if headless:
            self.options.add_argument('--headless=new')
        
        # Argumentos para melhor compatibilidade
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--disable-gpu')
        self.options.add_argument('--disable-web-security')
        self.options.add_argument('--allow-running-insecure-content')
        self.options.add_argument('--disable-extensions')
        self.options.add_argument('--disable-plugins')
        self.options.add_argument('--disable-images')
        self.options.add_argument('--disable-javascript')
        self.options.add_argument('--window-size=1920,1080')
        self.options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Desabilitar recursos desnecessários
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.default_content_settings.popups": 0,
            "profile.managed_default_content_settings.media_stream": 2,
        }
        self.options.add_experimental_option("prefs", prefs)
        self.options.add_experimental_option('excludeSwitches', ['enable-logging'])
        self.options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = None
        
    def iniciar(self):
        """Inicia o driver do Chrome"""
        try:
            self.driver = webdriver.Chrome(options=self.options)
            logger.info("✅ Navegador iniciado com sucesso")
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar navegador: {e}")
            logger.info("Instale o ChromeDriver: https://chromedriver.chromium.org/")
            return False
    
    def buscar_por_endereco(self, endereco: str) -> dict:
        """
        Busca dados de um endereço no GeoCuritiba
        """
        if not self.driver:
            if not self.iniciar():
                return {'sucesso': False, 'erro': 'Não foi possível iniciar o navegador'}
        
        try:
            # 1. Acessar o GeoCuritiba
            logger.info("Acessando GeoCuritiba...")
            self.driver.get("https://geocuritiba.ippuc.org.br/")
            
            # Aguardar o mapa carregar
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "esri-view-root"))
            )
            time.sleep(3)  # Aguardar carregamento completo
            
            # 2. Localizar e clicar na barra de busca
            logger.info(f"Buscando por: {endereco}")
            
            # Tentar diferentes seletores para a barra de busca
            search_selectors = [
                "input[placeholder*='Buscar']",
                "input[placeholder*='Search']",
                "input[placeholder*='Endereço']",
                ".esri-search__input",
                "input[type='text']"
            ]
            
            search_box = None
            for selector in search_selectors:
                try:
                    search_box = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if search_box:
                        break
                except:
                    continue
            
            if not search_box:
                raise Exception("Campo de busca não encontrado")
            
            # 3. Inserir endereço e buscar
            search_box.clear()
            search_box.send_keys(f"{endereco}, Curitiba")
            search_box.send_keys("\n")  # Enter
            
            # Aguardar resultado
            time.sleep(5)
            
            # 4. Clicar no primeiro resultado (se houver lista)
            try:
                first_result = self.driver.find_element(By.CSS_SELECTOR, ".esri-menu__list-item")
                first_result.click()
                time.sleep(3)
            except:
                logger.info("Resultado direto, sem lista de opções")
            
            # 5. Aguardar o popup com informações
            logger.info("Aguardando informações do lote...")
            
            # Clicar no mapa para obter popup
            map_element = self.driver.find_element(By.CLASS_NAME, "esri-view-surface")
            # Clicar no centro do mapa
            map_element.click()
            
            time.sleep(3)
            
            # 6. Extrair dados do popup
            dados = self._extrair_dados_popup()
            
            if not dados:
                # Tentar método alternativo: interceptar requisições de rede
                dados = self._extrair_dados_rede()
            
            return {
                'sucesso': True,
                'dados': dados,
                'endereco_buscado': endereco
            }
            
        except Exception as e:
            logger.error(f"Erro na busca: {e}")
            return {
                'sucesso': False,
                'erro': str(e)
            }
    
    def _extrair_dados_popup(self) -> dict:
        """Extrai dados do popup do mapa"""
        try:
            # Procurar por popup/infowindow
            popup_selectors = [
                ".esri-popup__content",
                ".esri-feature__content",
                ".esri-popup-container"
            ]
            
            for selector in popup_selectors:
                try:
                    popup = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if popup:
                        texto = popup.text
                        logger.info(f"Popup encontrado: {texto[:100]}...")
                        
                        # Parsear informações
                        dados = self._parsear_texto_popup(texto)
                        return dados
                except:
                    continue
                    
        except Exception as e:
            logger.error(f"Erro ao extrair popup: {e}")
        
        return None
    
    def _parsear_texto_popup(self, texto: str) -> dict:
        """Converte texto do popup em dicionário estruturado"""
        dados = {}
        
        # Padrões para buscar no texto
        padroes = {
            'indicacao_fiscal': r'Indicação Fiscal[:\s]+([^\n]+)',
            'inscricao': r'Inscrição[:\s]+([^\n]+)',
            'zoneamento': r'Zon[ea][:\s]+([A-Z0-9\-]+)',
            'bairro': r'Bairro[:\s]+([^\n]+)',
            'regional': r'Regional[:\s]+([^\n]+)',
            'area': r'Área[:\s]+([0-9,\.]+)',
        }
        
        for key, pattern in padroes.items():
            match = re.search(pattern, texto, re.IGNORECASE)
            if match:
                dados[key] = match.group(1).strip()
        
        return dados
    
    def _extrair_dados_rede(self) -> dict:
        """Método alternativo: captura requisições de rede"""
        try:
            # Executar JavaScript para capturar dados
            script = """
            // Tentar acessar dados do mapa
            var dados = {};
            
            // Procurar por objetos do ArcGIS
            if (window.require) {
                require(["esri/views/MapView"], function(MapView) {
                    // Tentar obter dados da view
                    var view = document.querySelector('.esri-view');
                    if (view && view.__accessor__) {
                        dados = view.__accessor__.store._values;
                    }
                });
            }
            
            return JSON.stringify(dados);
            """
            
            resultado = self.driver.execute_script(script)
            if resultado:
                return json.loads(resultado)
                
        except Exception as e:
            logger.error(f"Erro ao extrair dados da rede: {e}")
        
        return None
    
    def buscar_zoneamento_layer36(self, x: float, y: float) -> dict:
        """
        Acessa diretamente a layer 36 de zoneamento
        """
        url = f"https://geocuritiba.ippuc.org.br/server/rest/services/GeoCuritiba/Zoneamento_Lei_15_511_2019/MapServer/36/query"
        
        params = {
            'f': 'json',
            'geometry': f'{{"x":{x},"y":{y},"spatialReference":{{"wkid":31982}}}}',
            'geometryType': 'esriGeometryPoint',
            'spatialRel': 'esriSpatialRelIntersects',
            'outFields': '*'
        }
        
        # Navegar diretamente para a URL da API
        url_completa = f"{url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
        self.driver.get(url_completa)
        
        # Extrair JSON da página
        time.sleep(2)
        pre_element = self.driver.find_element(By.TAG_NAME, "pre")
        json_text = pre_element.text
        
        return json.loads(json_text)
    
    def fechar(self):
        """Fecha o navegador"""
        if self.driver:
            self.driver.quit()
            logger.info("Navegador fechado")

# ============================================================================
# FUNÇÃO PRINCIPAL PARA INTEGRAÇÃO
# ============================================================================

def buscar_zoneamento_selenium(endereco: str) -> dict:
    """
    Função principal que usa Selenium para buscar zoneamento
    """
    scraper = GeoCuritibaScraper(headless=True)  # False para ver o navegador
    
    try:
        resultado = scraper.buscar_por_endereco(endereco)
        
        if resultado['sucesso']:
            # Processar dados e retornar no formato esperado
            dados = resultado.get('dados', {})
            
            return {
                'sucesso': True,
                'parametros': {
                    'sigla_zona': dados.get('zoneamento', 'N/D'),
                    'nome_zona': f"Zona {dados.get('zoneamento', 'N/D')}",
                    'indicacao_fiscal': dados.get('indicacao_fiscal'),
                    'inscricao': dados.get('inscricao'),
                    'bairro': dados.get('bairro'),
                    # Adicionar parâmetros padrão baseados na zona
                    'coef_aproveitamento_basico': 1.0,  # Buscar da tabela
                    'taxa_ocupacao_maxima': 50.0,
                    'altura_maxima_pavimentos': 4,
                    'recuo_frontal_minimo': 5.0,
                    'taxa_permeabilidade_minima': 25.0
                }
            }
        else:
            return resultado
            
    finally:
        scraper.fechar()

# ============================================================================
# TESTE
# ============================================================================

if __name__ == "__main__":
    # Teste com endereço conhecido
    endereco_teste = "Rua XV de Novembro, 1234, Centro"
    print(f"Testando com: {endereco_teste}")
    
    resultado = buscar_zoneamento_selenium(endereco_teste)
    print(json.dumps(resultado, indent=2, ensure_ascii=False))