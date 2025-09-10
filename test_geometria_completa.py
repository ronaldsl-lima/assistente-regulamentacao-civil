"""
🧪 TESTE DA NOVA FUNCIONALIDADE: CONSULTA POR GEOMETRIA COMPLETA
Testa se a consulta por polígono (ao invés de ponto) está funcionando
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from geocuritiba_layer36_solution import GeoCuritibaLayer36Detector
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_geometria_completa():
    """
    TESTE CRÍTICO: Comparar consulta por PONTO vs POLÍGONO
    
    Este teste demonstra a diferença entre:
    1. Consulta por centróide (método antigo - impreciso)
    2. Consulta por geometria completa (método novo - preciso)
    """
    
    print("=" * 80)
    print("TESTE: CONSULTA POR GEOMETRIA COMPLETA vs PONTO")
    print("=" * 80)
    
    detector = GeoCuritibaLayer36Detector()
    
    # TESTE 1: Coordenadas do Batel (sabemos que retorna ZR3-T)
    print("\n1. TESTE COM COORDENADAS CONHECIDAS (Batel):")
    print("-" * 50)
    
    x, y = 676000, 7180000
    print(f"Coordenadas: ({x}, {y})")
    
    # Método 1: Consulta por PONTO (método antigo)
    print("\nMÉTODO 1: Consulta por PONTO (centróide)")
    geometria_ponto = {"x": x, "y": y, "spatialReference": {"wkid": 31982}}
    zonas_ponto = detector._consultar_layer36_multiplas_zonas(geometria_ponto)
    
    if zonas_ponto:
        for zona in zonas_ponto:
            sigla = zona.get('sg_zona', 'N/A')
            nome = zona.get('nm_zona', 'N/A')
            print(f"   Resultado: {sigla} - {nome}")
    else:
        print("   Nenhuma zona encontrada")
    
    # Método 2: Simular consulta por POLÍGONO
    print("\nMÉTODO 2: Consulta por POLÍGONO (simulado)")
    print("   (Simulando um lote de 1000m² ao redor do ponto)")
    
    # Criar um pequeno polígono ao redor do ponto para simular um lote
    offset = 15  # ~15 metros = lote pequeno
    geometria_poligono = {
        "rings": [[
            [x - offset, y - offset],
            [x + offset, y - offset], 
            [x + offset, y + offset],
            [x - offset, y + offset],
            [x - offset, y - offset]  # Fechar o polígono
        ]],
        "spatialReference": {"wkid": 31982}
    }
    
    zonas_poligono = detector._consultar_layer36_multiplas_zonas(geometria_poligono)
    
    if zonas_poligono:
        for zona in zonas_poligono:
            sigla = zona.get('sg_zona', 'N/A')
            nome = zona.get('nm_zona', 'N/A')
            print(f"   Resultado: {sigla} - {nome}")
            
        # Se múltiplas zonas, testar lógica de prioridade
        if len(zonas_poligono) > 1:
            print(f"\n   🔍 MÚLTIPLAS ZONAS DETECTADAS ({len(zonas_poligono)})")
            
            zonas_processadas = []
            for zona_raw in zonas_poligono:
                zona_info = {
                    'sigla_original': zona_raw.get('sg_zona', ''),
                    'sigla_padronizada': detector._padronizar_sigla_zona(zona_raw.get('sg_zona', '')),
                    'nome': zona_raw.get('nm_zona', ''),
                    'codigo': zona_raw.get('cd_zona'),
                    'grupo': zona_raw.get('nm_grupo', ''),
                    'legislacao': zona_raw.get('legislacao', '')
                }
                zonas_processadas.append(zona_info)
            
            zona_principal = detector._determinar_zona_principal(zonas_processadas)
            print(f"   ✅ Zona principal selecionada: {zona_principal['sigla_padronizada']}")
            
    else:
        print("   Nenhuma zona encontrada")
    
    # ANÁLISE DOS RESULTADOS
    print("\n" + "=" * 80)
    print("ANÁLISE DOS RESULTADOS:")
    print("=" * 80)
    
    if zonas_ponto and zonas_poligono:
        zonas_ponto_siglas = [z.get('sg_zona') for z in zonas_ponto]
        zonas_poligono_siglas = [z.get('sg_zona') for z in zonas_poligono]
        
        print(f"Zonas por PONTO: {zonas_ponto_siglas}")
        print(f"Zonas por POLÍGONO: {zonas_poligono_siglas}")
        
        if zonas_ponto_siglas == zonas_poligono_siglas:
            print("✅ RESULTADOS IDÊNTICOS - Neste caso específico não há diferença")
        else:
            print("🎯 RESULTADOS DIFERENTES - A consulta por polígono detectou zonas adicionais!")
            print("   Isso demonstra a importância de usar geometria completa")
    
    print(f"""
🎯 CONCLUSÃO:
- Consulta por PONTO: Analisa apenas o centróide do lote
- Consulta por POLÍGONO: Analisa toda a área do lote

💡 VANTAGEM DO POLÍGONO:
- Detecta quando lote está em múltiplas zonas
- Identifica sobreposições (ex: eixo sobre zona residencial)  
- Permite análise de prioridade regulatória
- Maior precisão para lotes grandes ou irregulares

⚠️ LIMITAÇÃO ATUAL:
- Sem inscrições reais, só podemos testar com coordenadas simuladas
- Para validação 100%, precisamos de inscrições fiscais válidas
    """)
    
    print("=" * 80)

if __name__ == "__main__":
    test_geometria_completa()