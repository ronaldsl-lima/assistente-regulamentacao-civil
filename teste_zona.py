# teste_zona.py - Prova de Conceito para Consulta de Zoneamento (Versão Robusta com CRS)

import geopandas as gpd
from geopy.geocoders import Nominatim
from shapely.geometry import Point
import os

def encontrar_zona_por_endereco(endereco, caminho_mapa_zoneamento):
    """
    Recebe um endereço e o caminho para um Shapefile de zoneamento,
    e retorna a sigla da zona correspondente.
    """
    try:
        # --- ETAPA 1: Geocodificar o Endereço ---
        print(f"Buscando coordenadas para o endereço: '{endereco}'...")
        geolocator = Nominatim(user_agent="assistente_regulatorio_poc", timeout=10)
        location = geolocator.geocode(endereco)
        
        if not location:
            return "Endereço não foi encontrado pelo serviço de geolocalização."

        print(f"-> Coordenadas encontradas: ({location.latitude}, {location.longitude})")
        
        # --- ETAPA 2: Ler o Mapa de Zoneamento ---
        print(f"Lendo o arquivo de mapa: '{caminho_mapa_zoneamento}'...")
        mapa_gdf = gpd.read_file(caminho_mapa_zoneamento)
        print(f"-> Mapa carregado com sucesso. O sistema de coordenadas do mapa é: {mapa_gdf.crs}")

        # --- ETAPA 3: Garantir Compatibilidade de Coordenadas (CRS) ---
        # Cria um GeoDataFrame para o nosso ponto. O CRS 'EPSG:4326' é o padrão para WGS84 (Lat/Lon).
        ponto_geom = Point(location.longitude, location.latitude)
        ponto_gdf = gpd.GeoDataFrame([1], geometry=[ponto_geom], crs="EPSG:4326")
        
        # Converte o CRS do nosso ponto para ser EXATAMENTE igual ao do mapa.
        print("-> Garantindo compatibilidade de sistemas de coordenadas...")
        ponto_no_crs_do_mapa = ponto_gdf.to_crs(mapa_gdf.crs)
        print("-> Compatibilidade OK.")

        # --- ETAPA 4: Fazer a Consulta Espacial (Método Robusto) ---
        print("Procurando a qual zona o ponto pertence...")
        # Usamos 'sjoin' (spatial join) que é otimizado para essa operação.
        zona_encontrada = gpd.sjoin(ponto_no_crs_do_mapa, mapa_gdf, how="inner", predicate="within")

        # --- ETAPA 5: Retornar o Resultado ---
        if not zona_encontrada.empty:
            sigla_zona = zona_encontrada.iloc[0]['sg_zona']
            print(f"-> Ponto localizado dentro da zona: '{sigla_zona}'")
            return sigla_zona
        else:
            return "Nenhuma zona encontrada para estas coordenadas. O ponto pode estar fora dos limites do mapa de zoneamento."

    except FileNotFoundError:
        return f"ERRO: O arquivo do mapa não foi encontrado em '{caminho_mapa_zoneamento}'. Verifique o caminho e o nome do arquivo."
    except Exception as e:
        return f"Ocorreu um erro inesperado: {e}"

# --- Bloco de Execução Principal ---
if __name__ == "__main__":
    
    # MODIFICAÇÃO: Usando o endereço fornecido por você. Adicionei a cidade para ajudar o geolocalizador.
    endereco_teste = "Rua Governador Agamenon Magalhães, 239, Curitiba"
    
    # --- ATENÇÃO: Verifique se o nome do arquivo .shp está correto ---
    nome_do_arquivo_shp = "feature_20250828095223479778.shp"
    
    # Monta o caminho completo para o arquivo
    caminho_completo_shp = os.path.join("mapas", nome_do_arquivo_shp)

    # Chama a função principal e guarda o resultado
    resultado_zona = encontrar_zona_por_endereco(endereco_teste, caminho_completo_shp)

    # Imprime o resultado final
    print("\n--- RESULTADO DA CONSULTA ---")
    print(f"Endereço: {endereco_teste}")
    print(f"Zona de Uso: {resultado_zona}")
    print("-----------------------------")