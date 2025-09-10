"""
 TESTE DE VALIDAO 100% - SISTEMA LAYER 36
Sistema de validao completo para verificar preciso da deteco de zoneamento
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from geocuritiba_layer36_solution import GeoCuritibaLayer36Detector
import logging

# Configurar logging para ver todos os detalhes
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_validacao_completa():
    """
     TESTE DE VALIDAO COMPLETA
    
    Para ter 100% de certeza, precisamos testar com inscries reais conhecidas.
    Infelizmente, sem acesso s inscries vlidas da Guia Amarela, vamos testar:
    
    1. Sistema de mapeamento de siglas
    2. Tratamento de mltiplas zonas
    3. Robustez de erro
    4. Coordenadas conhecidas
    """
    
    print("=" * 80)
    print("TESTE DE VALIDACAO COMPLETA - LAYER 36")
    print("=" * 80)
    
    detector = GeoCuritibaLayer36Detector()
    
    # TESTE 1: Mapeamento de siglas
    print("\n1  TESTE DE MAPEAMENTO DE SIGLAS:")
    print("-" * 50)
    
    siglas_teste = [
        ("ZR4", "ZR-4"),
        ("ZR3-T", "ZR-3-T"), 
        ("ZR3T", "ZR-3-T"),
        ("ZC", "ZC"),
        ("ZS1", "ZS-1"),
        ("ZUM1", "ZUM-1"),
        ("SEHIS", "SEHIS"),
        ("ECO1", "ECO-1"),
        ("EACF", "EACF"),
        ("ZONA_INEXISTENTE", "ZONA_INEXISTENTE")
    ]
    
    for sigla_original, esperado in siglas_teste:
        resultado = detector._padronizar_sigla_zona(sigla_original)
        status = " OK" if resultado == esperado else " ERRO"
        print(f"  {sigla_original:15}  {resultado:15} (esperado: {esperado:15}) {status}")
    
    # TESTE 2: Coordenadas conhecidas (Batel - teste anterior mostrou ZR3-T)
    print("\n2  TESTE COM COORDENADAS CONHECIDAS:")
    print("-" * 50)
    
    coordenadas_teste = [
        (676000, 7180000, "Batel - deve retornar ZR3-T ou similar"),
        (675000, 7175000, "Centro - coordenada aproximada"),
        (680000, 7185000, "Zona industrial - coordenada aproximada")
    ]
    
    for x, y, descricao in coordenadas_teste:
        print(f"\n Testando: {descricao}")
        print(f"   Coordenadas: ({x}, {y})")
        
        try:
            zonas = detector._consultar_layer36_multiplas_zonas(x, y)
            
            if zonas:
                print(f"    Encontradas {len(zonas)} zona(s):")
                for i, zona in enumerate(zonas, 1):
                    sigla_original = zona.get('sg_zona', 'N/A')
                    sigla_padronizada = detector._padronizar_sigla_zona(sigla_original)
                    nome = zona.get('nm_zona', 'N/A')
                    print(f"      {i}. {sigla_original}  {sigla_padronizada} ({nome})")
                
                if len(zonas) > 1:
                    zona_principal = detector._determinar_zona_principal([
                        {
                            'sigla_original': z.get('sg_zona', ''),
                            'sigla_padronizada': detector._padronizar_sigla_zona(z.get('sg_zona', '')),
                            'nome': z.get('nm_zona', ''),
                            'codigo': z.get('cd_zona'),
                            'grupo': z.get('nm_grupo', ''),
                            'legislacao': z.get('legislacao', '')
                        } for z in zonas
                    ])
                    print(f"    Zona principal selecionada: {zona_principal['sigla_padronizada']}")
                    
            else:
                print("    Nenhuma zona encontrada")
                
        except Exception as e:
            print(f"    Erro: {e}")
    
    # TESTE 3: Inscries genricas (sabemos que vo falhar, mas testamos a robustez)
    print("\n3  TESTE DE ROBUSTEZ COM INSCRIES GENRICAS:")
    print("-" * 50)
    
    inscricoes_teste = [
        "03000180090017",   # Exemplo do placeholder
        "12345678901234",   # Genrica
        "00000000000000",   # Zeros
        "",                 # Vazia
        "INVALID",          # Invlida
    ]
    
    for inscricao in inscricoes_teste:
        print(f"\n Testando inscrio: '{inscricao}'")
        
        try:
            resultado = detector.buscar_zoneamento_100_porcento_preciso(inscricao)
            
            if resultado['sucesso']:
                print(f"    Sucesso: {resultado['zoneamento']} ({resultado['nome_completo']})")
                print(f"    Coordenadas: {resultado.get('coordenadas', 'N/A')}")
                print(f"    Total zonas: {len(resultado.get('todas_zonas', []))}")
            else:
                print(f"     Fallback: {resultado['erro']}")
                print(f"    Fonte: {resultado['fonte']}")
                
        except Exception as e:
            print(f"    Erro crtico: {e}")
    
    # TESTE 4: Teste da funo de compatibilidade
    print("\n4  TESTE DE COMPATIBILIDADE (interface antiga):")
    print("-" * 50)
    
    resultado_compat = detector.buscar_zoneamento_correto("03000180090017")
    print(f"   Zona: {resultado_compat.zona}")
    print(f"   Confiana: {resultado_compat.confidence}")
    print(f"   Fonte: {resultado_compat.source}")
    print(f"   Detalhes: {resultado_compat.details}")
    
    print("\n" + "=" * 80)
    print(" CONCLUSO DO TESTE:")
    print("=" * 80)
    print("""
 FUNCIONALIDADES TESTADAS:
- Mapeamento completo de siglas 
- Consulta  Layer 36   
- Tratamento de mltiplas zonas 
- Sistema de prioridade de zonas 
- Robustez de erros 
- Compatibilidade com interface antiga 

  PARA VALIDAO 100% PRECISA:
Precisamos de 5-10 inscries reais com zoneamentos conhecidos da Guia Amarela.

 EXEMPLO DO QUE PRECISAMOS:
- Inscrio X  deve retornar ZR-4 
- Inscrio Y  deve retornar ZC
- Inscrio Z  deve retornar ZS-1

Com essas informaes, podemos ajustar qualquer detalhe final no mapeamento.
    """)
    
    print("=" * 80)

if __name__ == "__main__":
    test_validacao_completa()