# visual_check.py - Script para verificar visualmente a localização de um endereço no mapa

import geopandas as gpd
from geopy.geocoders import Nominatim
from shapely.geometry import Point
import os
import matplotlib.pyplot as plt

def verificar_e_plotar_endereco(endereco, caminho_mapa_zoneamento):
    """
    Encontra um endereço, verifica a zona e gera um mapa visual para depuração.
    """
    try:
        # --- ETAPA 1: Geocodificar o Endereço ---
        print(f"Buscando coordenadas para o endereço: '{endereco}'...")
        geolocator = Nominatim(user_agent="assistente_regulatorio_visual_check", timeout=10)
        location = geolocator.geocode(f"{endereco}, Curitiba")
        
        if not location:
            print("ERRO: Endereço não foi encontrado pelo serviço de geolocalização.")
            return

        print(f"-> Coordenadas encontradas: ({location.latitude}, {location.longitude})")
        
        # --- ETAPA 2: Ler o Mapa de Zoneamento ---
        print(f"Lendo o arquivo de mapa: '{caminho_mapa_zoneamento}'...")
        mapa_gdf = gpd.read_file(caminho_mapa_zoneamento)
        
        # --- ETAPA 3: Preparar o Ponto para Plotagem ---
        ponto_geom = Point(location.longitude, location.latitude)
        ponto_gdf = gpd.GeoDataFrame([1], geometry=[ponto_geom], crs="EPSG:4326")
        ponto_no_crs_do_mapa = ponto_gdf.to_crs(mapa_gdf.crs)

        # --- ETAPA 4: Gerar o Mapa Visual ---
        print("Gerando mapa de verificação visual...")
        fig, ax = plt.subplots(1, 1, figsize=(10, 10))
        
        # Desenha o mapa de zoneamento
        mapa_gdf.plot(ax=ax, color='lightblue', edgecolor='gray')
        
        # Desenha o ponto do endereço em vermelho
        ponto_no_crs_do_mapa.plot(ax=ax, marker='o', color='red', markersize=50, label='Endereço Encontrado')
        
        ax.set_title("Verificação Visual da Localização do Endereço")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        plt.legend()
        
        # Salva o mapa como uma imagem PNG
        nome_arquivo_saida = "debug_map.png"
        plt.savefig(nome_arquivo_saida)
        
        print(f"\nSUCESSO! Um mapa de verificação foi salvo como '{nome_arquivo_saida}' na sua pasta.")
        print("Por favor, abra este arquivo e veja se o ponto vermelho está dentro das áreas do mapa.")

    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")

# --- Bloco de Execução Principal ---
if __name__ == "__main__":
    
    # --- ATENÇÃO: COLOQUE AQUI O ENDEREÇO QUE FALHOU ---
    endereco_teste = "Rua Capitão Dr. Antônio José, 946 - Xaxim"
    
    nome_do_arquivo_shp = "feature_20250828095223479778.shp"
    caminho_completo_shp = os.path.join("mapas", nome_do_arquivo_shp)
    
    if "COLOQUE AQUI" in endereco_teste:
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!! ATENÇÃO: Edite o arquivo 'visual_check.py' na linha 62      !!!")
        print("!!! e substitua o texto de exemplo pelo endereço que você quer testar. !!!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    else:
        verificar_e_plotar_endereco(endereco_teste, caminho_completo_shp)