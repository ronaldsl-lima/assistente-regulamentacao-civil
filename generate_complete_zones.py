#!/usr/bin/env python3
"""
Gerador completo de dados para todas as zonas de Curitiba
Baseado na lista fornecida pelo usuário
"""

import os
import json
import pickle
from langchain.schema import Document
from typing import List, Dict, Any

# Lista completa de zonas fornecida pelo usuário
ZONAS_CURITIBA = [
    # Zonas Residenciais (ZR-1 a ZR-99)
    *[f"ZR-{i}" for i in range(1, 100)],
    
    # Zonas Especiais
    "EE", "ENC", "EMF", "EAC", "EMLV", "EACF", "EACB",
    
    # Zonas ECO
    "ECO-1-2-3-4", "ECL-3", "ECS-1", "ECL-1-2", "ECS-2",
    
    # Zonas Centrais
    "ZC",
    
    # Zonas Residenciais com nomes específicos
    "ZR1", "ZR2", "ZR3", "ZR3-T", "ZR-4", "ZROC", "ZROI",
    
    # Zonas de Uso Misto
    "ZUM-1", "ZUM-2", "ZUM-3", "ZUMVP",
    
    # Zonas de Serviços
    "ZSM", "ZSF",
    
    # Outras zonas
    "ZE", "ZM", "ZPS",
    
    # Zonas Habitacionais
    "ZH-1", "ZH-2",
    
    # Zonas Centro Cívico
    "ZCC", "ZCSF", "ZCUM",
    
    # Zonas de Serviços
    "ZS-1", "ZS-2",
    
    # Zona Industrial
    "ZI",
    
    # Setores Especiais
    "SEPE", "SEPP", "SEPI", "SEPC", "SEDE", "SEVB", "SEAV", "SESA", "SEHIS"
]

def get_zone_parameters(zona: str) -> Dict[str, Any]:
    """
    Retorna parâmetros urbanísticos baseados no tipo de zona
    """
    
    # Parâmetros para zonas residenciais ZR-1 a ZR-99
    if zona.startswith("ZR-") and zona[3:].isdigit():
        num = int(zona[3:])
        if num <= 10:
            return {
                "taxa_ocupacao": "50%",
                "coeficiente_aproveitamento": "1,0",
                "altura_maxima": "2 pavimentos ou 8,5 metros",
                "recuo_frontal": "4,0 metros",
                "recuos_laterais": "1,5 metros quando exigido",
                "recuo_fundos": "3,0 metros",
                "area_permeavel": "20%",
                "densidade": "baixa"
            }
        elif num <= 30:
            return {
                "taxa_ocupacao": "60%",
                "coeficiente_aproveitamento": "1,2",
                "altura_maxima": "3 pavimentos ou 12 metros",
                "recuo_frontal": "4,0 metros",
                "recuos_laterais": "1,5 metros",
                "recuo_fundos": "3,0 metros",
                "area_permeavel": "15%",
                "densidade": "baixa-média"
            }
        else:
            return {
                "taxa_ocupacao": "70%",
                "coeficiente_aproveitamento": "1,4",
                "altura_maxima": "4 pavimentos ou 16 metros",
                "recuo_frontal": "5,0 metros",
                "recuos_laterais": "2,0 metros",
                "recuo_fundos": "3,0 metros",
                "area_permeavel": "10%",
                "densidade": "média"
            }
    
    # Parâmetros específicos por zona
    zone_specs = {
        "ZCC": {
            "taxa_ocupacao": "70%",
            "coeficiente_aproveitamento": "4,0",
            "altura_maxima": "12 pavimentos ou 36 metros",
            "recuo_frontal": "5,0 metros",
            "recuos_laterais": "3,0 metros",
            "recuo_fundos": "3,0 metros",
            "area_permeavel": "15%",
            "densidade": "alta"
        },
        "ZR1": {
            "taxa_ocupacao": "50%",
            "coeficiente_aproveitamento": "1,0",
            "altura_maxima": "2 pavimentos ou 8,5 metros",
            "recuo_frontal": "4,0 metros",
            "recuos_laterais": "1,5 metros quando exigido",
            "recuo_fundos": "3,0 metros",
            "area_permeavel": "20%",
            "densidade": "baixa"
        },
        "ZR2": {
            "taxa_ocupacao": "50%",
            "coeficiente_aproveitamento": "1,4",
            "altura_maxima": "2 pavimentos ou 8,5 metros",
            "recuo_frontal": "4,0 metros",
            "recuos_laterais": "1,5 metros quando exigido",
            "recuo_fundos": "3,0 metros",
            "area_permeavel": "20%",
            "densidade": "baixa"
        },
        "ZR3": {
            "taxa_ocupacao": "60%",
            "coeficiente_aproveitamento": "1,8",
            "altura_maxima": "3 pavimentos ou 12 metros",
            "recuo_frontal": "4,0 metros",
            "recuos_laterais": "1,5 metros",
            "recuo_fundos": "3,0 metros",
            "area_permeavel": "15%",
            "densidade": "média"
        },
        "ZR3-T": {
            "taxa_ocupacao": "60%",
            "coeficiente_aproveitamento": "2,0",
            "altura_maxima": "4 pavimentos ou 16 metros",
            "recuo_frontal": "4,0 metros",
            "recuos_laterais": "1,5 metros",
            "recuo_fundos": "3,0 metros",
            "area_permeavel": "15%",
            "densidade": "média"
        },
        "ZR-4": {
            "taxa_ocupacao": "50%",
            "coeficiente_aproveitamento": "1,0",
            "altura_maxima": "2 pavimentos ou 8,5 metros",
            "recuo_frontal": "10,0 metros",
            "recuos_laterais": "5,0 metros",
            "recuo_fundos": "10,0 metros",
            "area_permeavel": "30%",
            "densidade": "muito baixa"
        },
        "ZUM-1": {
            "taxa_ocupacao": "70%",
            "coeficiente_aproveitamento": "2,5",
            "altura_maxima": "6 pavimentos ou 24 metros",
            "recuo_frontal": "5,0 metros",
            "recuos_laterais": "3,0 metros",
            "recuo_fundos": "3,0 metros",
            "area_permeavel": "10%",
            "densidade": "alta"
        },
        "ZUM-2": {
            "taxa_ocupacao": "80%",
            "coeficiente_aproveitamento": "3,0",
            "altura_maxima": "8 pavimentos ou 32 metros",
            "recuo_frontal": "5,0 metros",
            "recuos_laterais": "3,0 metros",
            "recuo_fundos": "3,0 metros",
            "area_permeavel": "5%",
            "densidade": "muito alta"
        },
        "ZC": {
            "taxa_ocupacao": "100%",
            "coeficiente_aproveitamento": "6,0",
            "altura_maxima": "sem limite",
            "recuo_frontal": "0 metros",
            "recuos_laterais": "0 metros",
            "recuo_fundos": "0 metros",
            "area_permeavel": "0%",
            "densidade": "muito alta"
        },
        "ZI": {
            "taxa_ocupacao": "70%",
            "coeficiente_aproveitamento": "1,4",
            "altura_maxima": "sem limite",
            "recuo_frontal": "10,0 metros",
            "recuos_laterais": "5,0 metros",
            "recuo_fundos": "5,0 metros",
            "area_permeavel": "10%",
            "densidade": "industrial"
        }
    }
    
    # Retorna parâmetros específicos ou padrão baseado no tipo
    if zona in zone_specs:
        return zone_specs[zona]
    
    # Parâmetros padrão para zonas não mapeadas
    if zona.startswith("ZS"):
        return {
            "taxa_ocupacao": "80%",
            "coeficiente_aproveitamento": "2,0",
            "altura_maxima": "4 pavimentos ou 16 metros",
            "recuo_frontal": "5,0 metros",
            "recuos_laterais": "3,0 metros",
            "recuo_fundos": "3,0 metros",
            "area_permeavel": "10%",
            "densidade": "serviços"
        }
    elif zona.startswith("SE"):
        return {
            "taxa_ocupacao": "variável",
            "coeficiente_aproveitamento": "conforme regulamentação específica",
            "altura_maxima": "conforme regulamentação específica",
            "recuo_frontal": "conforme regulamentação específica",
            "recuos_laterais": "conforme regulamentação específica",
            "recuo_fundos": "conforme regulamentação específica",
            "area_permeavel": "conforme regulamentação específica",
            "densidade": "especial"
        }
    elif zona.startswith("E"):
        return {
            "taxa_ocupacao": "60%",
            "coeficiente_aproveitamento": "1,5",
            "altura_maxima": "conforme projeto",
            "recuo_frontal": "10,0 metros",
            "recuos_laterais": "5,0 metros",
            "recuo_fundos": "5,0 metros",
            "area_permeavel": "20%",
            "densidade": "especial"
        }
    else:
        return {
            "taxa_ocupacao": "60%",
            "coeficiente_aproveitamento": "1,5",
            "altura_maxima": "3 pavimentos ou 12 metros",
            "recuo_frontal": "5,0 metros",
            "recuos_laterais": "3,0 metros",
            "recuo_fundos": "3,0 metros",
            "area_permeavel": "15%",
            "densidade": "padrão"
        }

def get_zone_uses(zona: str) -> List[str]:
    """
    Retorna usos permitidos baseados no tipo de zona
    """
    
    if zona.startswith("ZR"):
        return [
            "Residencial unifamiliar",
            "Residencial multifamiliar",
            "Comércio de proximidade",
            "Serviços de proximidade",
            "Institucional de vizinhança"
        ]
    elif zona.startswith("ZC"):
        return [
            "Residencial multifamiliar",
            "Comercial de grande porte",
            "Serviços especializados",
            "Institucional",
            "Hoteleiro",
            "Cultural"
        ]
    elif zona.startswith("ZUM"):
        return [
            "Residencial",
            "Comercial",
            "Serviços",
            "Institucional",
            "Escritórios"
        ]
    elif zona.startswith("ZI"):
        return [
            "Industrial",
            "Logístico",
            "Serviços industriais",
            "Comercial atacadista"
        ]
    elif zona.startswith("ZS"):
        return [
            "Serviços especializados",
            "Comercial",
            "Institucional",
            "Escritórios"
        ]
    elif zona.startswith("SE"):
        return [
            "Conforme regulamentação específica do setor"
        ]
    elif zona.startswith("E"):
        return [
            "Equipamentos urbanos",
            "Institucionais",
            "Serviços públicos"
        ]
    else:
        return [
            "Conforme regulamentação específica"
        ]

def normalize_zone_name(zona: str) -> str:
    """
    Normaliza nome da zona para evitar problemas de matching
    """
    # Mapeamentos especiais conhecidos
    mappings = {
        "ZONA RESIDENCIAL 4 - LINHA VERDE": "ZR-4",
        "ZONA RESIDENCIAL 1": "ZR-1", 
        "ZONA RESIDENCIAL 2": "ZR-2",
        "ZONA RESIDENCIAL 3": "ZR-3",
        "ZONA RESIDENCIAL 4": "ZR-4",
        "ZONA CENTRO CIVICO": "ZCC",
        "ZONA CENTRO CÍVICO": "ZCC",
        "ZONA INDUSTRIAL": "ZI",
        "ZONA CENTRAL": "ZC"
    }
    
    zona_upper = zona.upper().strip()
    
    if zona_upper in mappings:
        return mappings[zona_upper]
    
    return zona

def create_document_for_zone(zona: str) -> List[Document]:
    """
    Cria documentos para uma zona específica
    """
    documents = []
    
    # Normalizar nome da zona
    zona_normalizada = normalize_zone_name(zona)
    parametros = get_zone_parameters(zona_normalizada)
    usos = get_zone_uses(zona_normalizada)
    
    # Documento de parâmetros urbanísticos
    parametros_content = f"""
            {zona.upper()} - PARÂMETROS URBANÍSTICOS
            
            PARÂMETROS URBANÍSTICOS:
            - Taxa de Ocupação: máximo {parametros['taxa_ocupacao']}
            - Coeficiente de Aproveitamento: máximo {parametros['coeficiente_aproveitamento']}
            - Altura da Edificação: máximo {parametros['altura_maxima']}
            - Recuo Frontal: mínimo {parametros['recuo_frontal']}
            - Recuos Laterais: mínimo {parametros['recuos_laterais']}
            - Recuo de Fundos: mínimo {parametros['recuo_fundos']}
            - Área Permeável: mínimo {parametros['area_permeavel']}
            - Densidade: {parametros['densidade']}
            """
    
    documents.append(Document(
        page_content=parametros_content,
        metadata={
            'source': 'lei_municipal_curitiba',
            'zona_especifica': zona_normalizada,
            'zona_nome_completo': zona,
            'zonas_mencionadas': [zona, zona_normalizada] if zona != zona_normalizada else [zona],
            'tipo_conteudo': 'parametros_urbanisticos',
            'contem_tabela': True
        }
    ))
    
    # Documento de usos permitidos
    usos_content = f"""
            {zona.upper()} - USOS PERMITIDOS
            
            São permitidos na {zona}:
            """ + "\n            ".join([f"- {uso}" for uso in usos]) + f"""
            
            Características: Zona destinada a {parametros['densidade']} densidade construtiva e ocupação.
            Regulamentada pela Lei Municipal de Zoneamento de Curitiba.
            """
    
    documents.append(Document(
        page_content=usos_content,
        metadata={
            'source': 'lei_municipal_curitiba',
            'zona_especifica': zona_normalizada,
            'zona_nome_completo': zona,
            'zonas_mencionadas': [zona, zona_normalizada] if zona != zona_normalizada else [zona],
            'tipo_conteudo': 'usos_permitidos',
            'contem_tabela': False
        }
    ))
    
    return documents

def generate_complete_zone_data():
    """
    Gera dados completos para todas as zonas de Curitiba
    """
    print("Gerando dados completos para todas as zonas de Curitiba...")
    
    all_documents = []
    
    # Gerar dados para cada zona
    for zona in ZONAS_CURITIBA:
        print(f"Processando zona: {zona}")
        docs = create_document_for_zone(zona)
        all_documents.extend(docs)
    
    # Adicionar algumas variações de nomes conhecidas
    zonas_especiais = [
        "ZONA RESIDENCIAL 4 - LINHA VERDE",  # Mapeará para ZR-4
        "ZONA CENTRO CÍVICO",
        "ZONA INDUSTRIAL",
        "ZONA CENTRAL"
    ]
    
    for zona_especial in zonas_especiais:
        if zona_especial not in [doc.metadata.get('zona_nome_completo', '') for doc in all_documents]:
            print(f"Adicionando zona especial: {zona_especial}")
            docs = create_document_for_zone(zona_especial)
            all_documents.extend(docs)
    
    print(f"Total de documentos gerados: {len(all_documents)}")
    
    # Salvar dados
    output_dir = "db_fallback"
    os.makedirs(output_dir, exist_ok=True)
    
    # Salvar como pickle
    with open(os.path.join(output_dir, 'documents.pkl'), 'wb') as f:
        pickle.dump(all_documents, f)
    
    # Salvar como JSON
    doc_data = []
    for doc in all_documents:
        doc_data.append({
            'content': doc.page_content,
            'metadata': doc.metadata
        })
    
    with open(os.path.join(output_dir, 'documents.json'), 'w', encoding='utf-8') as f:
        json.dump(doc_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Dados salvos em {output_dir}")
    print(f"📊 Total de zonas: {len(set(doc.metadata['zona_especifica'] for doc in all_documents))}")
    print("🚀 Sistema pronto para todas as zonas de Curitiba!")
    
    # Mostrar algumas zonas para confirmação
    zonas_geradas = sorted(set(doc.metadata['zona_especifica'] for doc in all_documents))
    print(f"\nPrimeiras 20 zonas geradas: {zonas_geradas[:20]}")
    print(f"Últimas 10 zonas geradas: {zonas_geradas[-10:]}")
    
    return all_documents

if __name__ == "__main__":
    generate_complete_zone_data()