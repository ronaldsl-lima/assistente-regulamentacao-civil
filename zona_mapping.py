# zona_mapping.py - Mapeamento completo de zonas urbanísticas
# Versão: 1.0 - Atualizado em 29/08/2025
# Cidade: Curitiba

"""
Este arquivo contém o mapeamento completo das zonas de uso de Curitiba,
com seus respectivos quadros e artigos na legislação.

Este mapeamento é usado pelo sistema para buscar com precisão as informações
relevantes para cada zona, melhorando significativamente a qualidade das análises.
"""

# Mapeamento detalhado das zonas, com nome completo, quadros, artigos e tipo
MAPEAMENTO_ZONAS = {
    "ZR1": {
        "nome": "Zona Residencial 1",
        "artigos": ["39", "40"],
        "quadros": ["XVI", "XVII"],
        "tipo": "zona_residencial"
    },
    "ZR2": {
        "nome": "Zona Residencial 2",
        "artigos": ["41", "42"],
        "quadros": ["XVIII", "XIX"],
        "tipo": "zona_residencial"
    },
    "ZR3": {
        "nome": "Zona Residencial 3",
        "artigos": ["43", "44"],
        "quadros": ["XX", "XXI"],
        "tipo": "zona_residencial"
    },
    "ZR4": {
        "nome": "Zona Residencial 4",
        "artigos": ["45", "46"],
        "quadros": ["XXII", "XXIII"],
        "tipo": "zona_residencial"
    },
    "ZR-OC": {
        "nome": "Zona Residencial de Ocupação Controlada",
        "artigos": ["47", "48"],
        "quadros": ["XXIV", "XXV"],
        "tipo": "zona_residencial"
    },
    "ZR-SF": {
        "nome": "Zona Residencial Santa Felicidade",
        "artigos": ["49", "50"],
        "quadros": ["XXVI", "XXVII"],
        "tipo": "zona_residencial"
    },
    "ZR-U": {
        "nome": "Zona Residencial Umbará",
        "artigos": ["51", "52"],
        "quadros": ["XXVIII", "XXIX"],
        "tipo": "zona_residencial"
    },
    "ZR-P": {
        "nome": "Zona Residencial Passaúna",
        "artigos": ["53", "54"],
        "quadros": ["XXX", "XXXI"],
        "tipo": "zona_residencial"
    },
    "ZT-MF": {
        "nome": "Zona de Transição da Av. Mal. Floriano Peixoto",
        "artigos": ["55", "56"],
        "quadros": ["XXXII", "XXXIII"],
        "tipo": "zona_transicao"
    },
    "ZT-NC": {
        "nome": "Zona de Transição Nova Curitiba",
        "artigos": ["57", "58"],
        "quadros": ["XXXIV", "XXXV"],
        "tipo": "zona_transicao"
    },
    "ZT-BR-116": {
        "nome": "Zona de Transição BR-116",
        "artigos": ["59", "60"],
        "quadros": ["XXXVI", "XXXVII"],
        "tipo": "zona_transicao"
    },
    "ZE-D": {
        "nome": "Zona Especial Desportiva",
        "artigos": ["61", "62"],
        "quadros": ["XXXVIII", "XXXIX"],
        "tipo": "zona_especial"
    },
    "ZE-E": {
        "nome": "Zona Especial Educacional",
        "artigos": ["63", "64"],
        "quadros": ["XL", "XLI"],
        "tipo": "zona_especial"
    },
    "ZE-M": {
        "nome": "Zona Especial Militar",
        "artigos": ["65", "66"],
        "quadros": ["XLII", "XLIII"],
        "tipo": "zona_especial"
    },
    "Z-COM": {
        "nome": "Zona de Contenção",
        "artigos": ["67", "68"],
        "quadros": ["XLIV", "XLV"],
        "tipo": "zona_contenção"
    },
    "ZI": {
        "nome": "Zona Industrial",
        "artigos": ["69", "70"],
        "quadros": ["XLVI", "XLVII"],
        "tipo": "zona_industrial"
    },
    "ZS-1": {
        "nome": "Zona de Serviço 1",
        "artigos": ["71", "72"],
        "quadros": ["XLVIII", "XLIX"],
        "tipo": "zona_servico"
    },
    "ZS-2": {
        "nome": "Zona de Serviço 2",
        "artigos": ["73", "74"],
        "quadros": ["L", "LI"],
        "tipo": "zona_servico"
    },
    "ZC": {
        "nome": "Zona Central",
        "artigos": ["75", "76"],
        "quadros": ["LII", "LIII"],
        "tipo": "zona_central"
    },
    "ZCC.4": {
        "nome": "Zona Centro Cívico",
        "artigos": ["77", "78"],
        "quadros": ["LIV", "LV"],
        "tipo": "zona_central"
    },
    "ZR3-T": {
        "nome": "Zona Residencial 3 - Transição",
        "artigos": ["77", "78"],
        "quadros": ["LIV", "LV"],
        "tipo": "zona_residencial"
    },
    "ZUM": {
        "nome": "Zona de Uso Misto",
        "artigos": ["79", "80"],
        "quadros": ["LVI", "LVII"],
        "tipo": "zona_mista"
    },
    "ZUM-1": {
        "nome": "Zona de Uso Misto 1",
        "artigos": ["79", "80"],
        "quadros": ["LVI", "LVII"],
        "tipo": "zona_mista"
    },
    "ZUM-2": {
        "nome": "Zona de Uso Misto 2",
        "artigos": ["81", "82"],
        "quadros": ["LVIII", "LIX"],
        "tipo": "zona_mista"
    },
    "ZUM-3": {
        "nome": "Zona de Uso Misto 3",
        "artigos": ["83", "84"],
        "quadros": ["LX", "LXI"],
        "tipo": "zona_mista"
    },
    "ZUM-4": {
        "nome": "Zona de Uso Misto 4",
        "artigos": ["85", "86"],
        "quadros": ["LXII", "LXIII"],
        "tipo": "zona_mista"
    },
    "ZEIS": {
        "nome": "Zona Especial de Interesse Social",
        "artigos": ["87", "88"],
        "quadros": ["LXIV", "LXV"],
        "tipo": "zona_especial"
    },
    "SC-SF": {
        "nome": "Setor Especial Comercial Santa Felicidade",
        "artigos": ["89", "90"],
        "quadros": ["LXVI", "LXVII"],
        "tipo": "setor_especial"
    },
    "SC": {
        "nome": "Setor Especial Comercial",
        "artigos": ["91", "92"],
        "quadros": ["LXVIII", "LXIX"],
        "tipo": "setor_especial"
    },
    "SE": {
        "nome": "Setor Especial Estrutural",
        "artigos": ["93", "94"],
        "quadros": ["LXX", "LXXI"],
        "tipo": "setor_especial"
    },
    "SE-AC": {
        "nome": "Setor Especial do Anel Central",
        "artigos": ["95", "96"],
        "quadros": ["LXXII", "LXXIII"],
        "tipo": "setor_especial"
    },
    "SE-WB": {
        "nome": "Setor Especial Wenceslau Braz",
        "artigos": ["97", "98"],
        "quadros": ["LXXIV", "LXXV"],
        "tipo": "setor_especial"
    },
    "SE-MF": {
        "nome": "Setor Especial Marechal Floriano",
        "artigos": ["99", "100"],
        "quadros": ["LXXVI", "LXXVII"],
        "tipo": "setor_especial"
    },
    "SE-CF": {
        "nome": "Setor Especial Comendador Franco",
        "artigos": ["101", "102"],
        "quadros": ["LXXVIII", "LXXIX"],
        "tipo": "setor_especial"
    },
    "SE-CB": {
        "nome": "Setor Especial da Rua Engenheiro Costa Barros",
        "artigos": ["103", "104"],
        "quadros": ["LXXX", "LXXXI"],
        "tipo": "setor_especial"
    },
    "SE-LE": {
        "nome": "Setor Especial Linhão do Emprego",
        "artigos": ["105", "106"],
        "quadros": ["LXXXII", "LXXXIII"],
        "tipo": "setor_especial"
    },
    "SEHIS": {
        "nome": "Setor Especial de Habitação de Interesse Social",
        "artigos": ["107", "108"],
        "quadros": ["LXXXIV", "LXXXV"],
        "tipo": "setor_especial"
    },
    "CONEC": {
        "nome": "Setor Especial Conector",
        "artigos": ["109", "110"],
        "quadros": ["LXXXVI", "LXXXVII"],
        "tipo": "setor_especial"
    },
    "CEIV": {
        "nome": "Setor Especial Centro de Eventos da Imigração Viva",
        "artigos": ["111", "112"],
        "quadros": ["LXXXVIII", "LXXXIX"],
        "tipo": "setor_especial"
    },
    "SE-BR-116": {
        "nome": "Setor Especial da BR-116",
        "artigos": ["113", "114"],
        "quadros": ["XC", "XCI"],
        "tipo": "setor_especial"
    },
    "SE-NC": {
        "nome": "Setor Especial Nova Curitiba",
        "artigos": ["115", "116"],
        "quadros": ["XCII", "XCIII"],
        "tipo": "setor_especial"
    },
    "SE-OI": {
        "nome": "Setor Especial de Ocupação Integrada",
        "artigos": ["117", "118"],
        "quadros": ["XCIV", "XCV"],
        "tipo": "setor_especial"
    },
    "SEMU": {
        "nome": "Setor Especial de Música",
        "artigos": ["119", "120"],
        "quadros": ["XCVI", "XCVII"],
        "tipo": "setor_especial"
    },
    "SE-PE": {
        "nome": "Setor Especial de Preservação de Encontros de Rios",
        "artigos": ["121", "122"],
        "quadros": ["XCVIII", "XCIX"],
        "tipo": "setor_especial"
    },
    "APA-SS": {
        "nome": "Área de Proteção Ambiental do Passaúna",
        "artigos": ["123", "124"],
        "quadros": ["C", "CI"],
        "tipo": "area_protecao"
    },
    "APA-P": {
        "nome": "Área de Proteção Ambiental do Iguaçu",
        "artigos": ["125", "126"],
        "quadros": ["CII", "CIII"],
        "tipo": "area_protecao"
    },
    "UTP": {
        "nome": "Unidade Territorial de Planejamento",
        "artigos": ["127", "128"],
        "quadros": ["CIV", "CV"],
        "tipo": "unidade_planejamento"
    },
    "EE": {
        "nome": "Eixo Estrutural",
        "artigos": ["93", "94"],
        "quadros": ["LXX", "LXXI"],
        "tipo": "eixo"
    },
    "ENC": {
        "nome": "Eixo Nova Curitiba",
        "artigos": ["115", "116"],
        "quadros": ["XCII", "XCIII"],
        "tipo": "eixo"
    },
    "EMF": {
        "nome": "Eixo Marechal Floriano",
        "artigos": ["99", "100"],
        "quadros": ["LXXVI", "LXXVII"],
        "tipo": "eixo"
    },
    "EAC": {
        "nome": "Eixo Anel Central",
        "artigos": ["95", "96"],
        "quadros": ["LXXII", "LXXIII"],
        "tipo": "eixo"
    },
    "EMLV": {
        "nome": "Eixo Mario Lobo Viana",
        "artigos": ["129", "130"],
        "quadros": ["CVI", "CVII"],
        "tipo": "eixo"
    },
    "EACF": {
        "nome": "Eixo Av. Comendador Franco",
        "artigos": ["101", "102"],
        "quadros": ["LXXVIII", "LXXIX"],
        "tipo": "eixo"
    },
    "EACB": {
        "nome": "Eixo Av. Costa Barros",
        "artigos": ["103", "104"],
        "quadros": ["LXXX", "LXXXI"],
        "tipo": "eixo"
    },
    "ECO-1": {
        "nome": "Eixo de Conectividade 1",
        "artigos": ["131", "132"],
        "quadros": ["CVIII", "CIX"],
        "tipo": "eixo"
    },
    "ECO-2": {
        "nome": "Eixo de Conectividade 2",
        "artigos": ["133", "134"],
        "quadros": ["CX", "CXI"],
        "tipo": "eixo"
    },
    "ECO-3": {
        "nome": "Eixo de Conectividade 3",
        "artigos": ["135", "136"],
        "quadros": ["CXII", "CXIII"],
        "tipo": "eixo"
    },
    "ECO-4": {
        "nome": "Eixo de Conectividade 4",
        "artigos": ["137", "138"],
        "quadros": ["CXIV", "CXV"],
        "tipo": "eixo"
    }
}

def obter_info_zona(zona_sigla):
    """
    Retorna informações de uma zona específica.
    
    Args:
        zona_sigla: Sigla da zona (ex: ZR2, SE-CB, EE)
        
    Returns:
        Dict com informações da zona ou None se não encontrada
    """
    if not zona_sigla:
        return None
        
    # Normaliza a sigla para busca
    zona_limpa = zona_sigla.upper().replace(" ", "").replace("-", "")
    
    # Busca direta
    if zona_limpa in MAPEAMENTO_ZONAS:
        return MAPEAMENTO_ZONAS[zona_limpa]
    
    # Tenta variações comuns
    variantes = [
        zona_sigla.upper(),  # Original em maiúsculas
        zona_sigla.upper().replace(" ", "-"),  # Espaços para hífen
        zona_sigla.upper().replace("-", ""),   # Sem hífens
        zona_sigla.upper().replace(" ", ""),   # Sem espaços
        zona_sigla.upper().replace(".", ""),   # Sem pontos
    ]
    
    for variante in variantes:
        if variante in MAPEAMENTO_ZONAS:
            return MAPEAMENTO_ZONAS[variante]
    
    # Busca por correspondência parcial
    for key in MAPEAMENTO_ZONAS:
        # Se a zona começa com a sigla fornecida
        if key.startswith(zona_limpa) or zona_limpa.startswith(key):
            return MAPEAMENTO_ZONAS[key]
    
    # Busca por tipo de zona (para zonas sem número)
    tipos_base = {
        "ZR": "zona_residencial",
        "ZC": "zona_central",
        "ZI": "zona_industrial",
        "ZE": "zona_especial",
        "SE": "setor_especial",
        "ZS": "zona_servico",
        "ZUM": "zona_mista"
    }
    
    for prefixo, tipo in tipos_base.items():
        if zona_limpa.startswith(prefixo):
            # Busca a primeira zona desse tipo
            for key, info in MAPEAMENTO_ZONAS.items():
                if info.get("tipo") == tipo:
                    return info
    
    return None

def obter_quadros_zona(zona_sigla):
    """
    Retorna os quadros associados a uma zona específica.
    
    Args:
        zona_sigla: Sigla da zona
        
    Returns:
        Lista de quadros ou lista vazia se não encontrada
    """
    info = obter_info_zona(zona_sigla)
    return info.get("quadros", []) if info else []

def obter_artigos_zona(zona_sigla):
    """
    Retorna os artigos associados a uma zona específica.
    
    Args:
        zona_sigla: Sigla da zona
        
    Returns:
        Lista de artigos ou lista vazia se não encontrada
    """
    info = obter_info_zona(zona_sigla)
    return info.get("artigos", []) if info else []

def listar_zonas_por_tipo(tipo_zona):
    """
    Retorna uma lista de zonas de um tipo específico.
    
    Args:
        tipo_zona: Tipo de zona (ex: zona_residencial, eixo, setor_especial)
        
    Returns:
        Lista de siglas de zonas do tipo especificado
    """
    return [
        zona for zona, info in MAPEAMENTO_ZONAS.items() 
        if info.get("tipo") == tipo_zona
    ]

def normalizar_zona(zona_texto):
    """
    Normaliza o texto de uma zona para o formato padrão.
    
    Args:
        zona_texto: Texto da zona em qualquer formato
        
    Returns:
        Texto normalizado da zona ou o texto original se não reconhecido
    """
    if not zona_texto:
        return zona_texto
        
    # Converte para maiúsculas e remove espaços extras
    texto = zona_texto.upper().strip()
    
    # Padrões de substituição para normalização
    padroes = [
        (r'ZONA\s+RESIDENCIAL\s*[-]?\s*(\d+).*', r'ZR\1'),  # Captura ZR4 mesmo com texto adicional
        (r'ZONA\s+CENTRO\s+C[ÍI]VICO.*', r'ZCC.4'),  # Centro Cívico específico
        (r'ZONA\s+CENTRAL.*', r'ZC'),
        (r'ZONA\s+INDUSTRIAL.*', r'ZI'),
        (r'ZONA\s+DE\s+SERVI[CÇ]OS?\s*[-]?\s*(\d+)', r'ZS-\1'),
        (r'ZONA\s+DE\s+USO\s+MISTO\s*[-]?\s*(\d+)', r'ZUM-\1'),
        (r'ZONA\s+ESPECIAL\s*[-]?\s*(\w+)', r'ZE-\1'),
        (r'SETOR\s+ESPECIAL\s+(\w+)', r'SE-\1'),
        (r'EIXO\s+(\w+)', r'E\1'),
        (r'ZCC\.4', r'ZCC.4'),  # Mantém ZCC.4 como está
        (r'Z[\s\.]*R[\s\.]*(\d+)', r'ZR\1'),
        (r'Z[\s\.]*C[\s\.]*C[\s\.]*(\d+)', r'ZCC.\1'),  # ZCC4 → ZCC.4
        (r'Z[\s\.]*C', r'ZC'),
        (r'Z[\s\.]*I', r'ZI'),
        (r'Z[\s\.]*S[\s\.]*(\d+)', r'ZS-\1'),
        (r'Z[\s\.]*U[\s\.]*M[\s\.]*(\d+)', r'ZUM-\1'),
    ]
    
    import re
    for padrao, substituicao in padroes:
        texto = re.sub(padrao, substituicao, texto)
    
    # Remove espaços entre letras e números
    texto = re.sub(r'([A-Z])\s+(\d)', r'\1\2', texto)
    
    # Verifica se a zona normalizada existe no mapeamento
    info = obter_info_zona(texto)
    if info:
        # Retorna a sigla oficial do mapeamento
        for key, value in MAPEAMENTO_ZONAS.items():
            if value == info:
                return key
    
    return texto

# Teste do módulo
if __name__ == "__main__":
    # Testa algumas zonas
    zonas_teste = ["ZR2", "ZR-2", "Z R 2", "Zona Residencial 2", "zr2"]
    
    print("Teste de identificação de zonas:")
    for zona in zonas_teste:
        info = obter_info_zona(zona)
        if info:
            print(f"OK {zona} -> {info['nome']} (Quadros: {info['quadros']}, Tipo: {info['tipo']})")
        else:
            print(f"ERRO {zona} -> Não encontrada")
    
    print("\nTeste de normalização:")
    textos_teste = [
        "Zona Residencial 2",
        "Z. R. 2",
        "ZR-2",
        "zona residencial 2",
        "Setor Especial Comercial",
        "SE-COM",
        "Eixo Estrutural",
        "EE"
    ]
    
    for texto in textos_teste:
        print(f"{texto} -> {normalizar_zona(texto)}")
    
    print("\nTipos de zonas disponíveis:")
    tipos = set(info["tipo"] for info in MAPEAMENTO_ZONAS.values())
    for tipo in sorted(tipos):
        zonas = listar_zonas_por_tipo(tipo)
        print(f"{tipo}: {len(zonas)} zonas")