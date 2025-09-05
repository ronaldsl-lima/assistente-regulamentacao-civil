#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parâmetros Oficiais de Zoneamento de Curitiba
Baseado na Guia Amarela e legislação vigente (Lei 15.511/2019)
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ParametrosOficiaisCuritiba:
    """
    Parâmetros oficiais conforme Lei 15.511/2019 e Guia Amarela
    """
    
    def __init__(self):
        # Parâmetros oficiais por zona - REVISÃO COMPLETA baseada na guia amarela
        self.parametros_zona = {
            # ZONAS RESIDENCIAIS
            "ZR-1": {
                "nome": "Zona Residencial 1",
                "taxa_ocupacao_max": 50.0,  # %
                "coeficiente_aproveitamento_max": 1.0,
                "altura_max_metros": 7.5,
                "altura_max_pavimentos": 2,
                "recuo_frontal_min": 4.0,  # metros
                "recuos_laterais_min": 1.5,  # metros
                "recuo_fundos_min": 3.0,  # metros
                "taxa_permeabilidade_min": 30.0,  # % MÍNIMO obrigatório
                "descricao": "Zona residencial unifamiliar de baixa densidade"
            },
            
            "ZR-2": {
                "nome": "Zona Residencial 2", 
                "taxa_ocupacao_max": 60.0,
                "coeficiente_aproveitamento_max": 1.5,
                "altura_max_metros": 12.0,
                "altura_max_pavimentos": 4,
                "recuo_frontal_min": 4.0,
                "recuos_laterais_min": 1.5,
                "recuo_fundos_min": 3.0,
                "taxa_permeabilidade_min": 25.0,  # % MÍNIMO obrigatório
                "descricao": "Zona residencial de média densidade"
            },
            
            "ZR-3": {
                "nome": "Zona Residencial 3",
                "taxa_ocupacao_max": 70.0,
                "coeficiente_aproveitamento_max": 2.5,
                "altura_max_metros": 18.0,
                "altura_max_pavimentos": 6,
                "recuo_frontal_min": 4.0,
                "recuos_laterais_min": 1.5,
                "recuo_fundos_min": 3.0,
                "taxa_permeabilidade_min": 20.0,
                "descricao": "Zona residencial de alta densidade"
            },
            
            "ZR-4": {
                "nome": "Zona Residencial 4",
                "taxa_ocupacao_max": 80.0,
                "coeficiente_aproveitamento_max": 4.0,
                "altura_max_metros": 30.0,
                "altura_max_pavimentos": 10,
                "recuo_frontal_min": 4.0,
                "recuos_laterais_min": 1.5,
                "recuo_fundos_min": 3.0,
                "taxa_permeabilidade_min": 15.0,
                "descricao": "Zona residencial de densidade alta"
            },
            
            # SETOR ESPECIAL DE HABITAÇÃO DE INTERESSE SOCIAL
            "SEHIS": {
                "nome": "Setor Especial de Habitação de Interesse Social",
                "taxa_ocupacao_max": 70.0,
                "coeficiente_aproveitamento_max": 2.0,
                "altura_max_metros": 15.0,
                "altura_max_pavimentos": 5,
                "recuo_frontal_min": 3.0,  # SEHIS tem recuos menores
                "recuos_laterais_min": 1.5,
                "recuo_fundos_min": 2.0,
                "taxa_permeabilidade_min": 25.0,  # % MÍNIMO obrigatório
                "descricao": "Habitação de interesse social com parâmetros específicos",
                "observacoes": "Legislação específica para habitação social"
            },
            
            # ZONA CENTRAL
            "ZC": {
                "nome": "Zona Central",
                "taxa_ocupacao_max": 85.0,
                "coeficiente_aproveitamento_max": 6.0,
                "altura_max_metros": 75.0,
                "altura_max_pavimentos": 25,
                "recuo_frontal_min": 0.0,  # Centro pode ter recuo zero
                "recuos_laterais_min": 0.0,
                "recuo_fundos_min": 3.0,
                "taxa_permeabilidade_min": 10.0,
                "descricao": "Zona central com alta densidade construtiva"
            },
            
            # ZONA HISTÓRICA
            "ZH-1": {
                "nome": "Zona Histórica 1",
                "taxa_ocupacao_max": 60.0,
                "coeficiente_aproveitamento_max": 1.5,
                "altura_max_metros": 12.0,
                "altura_max_pavimentos": 4,
                "recuo_frontal_min": 0.0,  # Preservação do alinhamento histórico
                "recuos_laterais_min": 1.5,
                "recuo_fundos_min": 3.0,
                "taxa_permeabilidade_min": 20.0,
                "descricao": "Zona histórica com restrições especiais de preservação"
            },
            
            # ZONA INDUSTRIAL
            "ZI": {
                "nome": "Zona Industrial",
                "taxa_ocupacao_max": 70.0,
                "coeficiente_aproveitamento_max": 1.5,
                "altura_max_metros": 18.0,
                "altura_max_pavimentos": 6,
                "recuo_frontal_min": 5.0,
                "recuos_laterais_min": 3.0,
                "recuo_fundos_min": 5.0,
                "taxa_permeabilidade_min": 20.0,
                "descricao": "Zona para atividades industriais"
            }
        }
    
    def get_parametros_zona(self, zona: str) -> Optional[Dict[str, Any]]:
        """
        Obtém parâmetros oficiais para uma zona
        """
        zona_clean = zona.upper().replace("-", "").replace(" ", "")
        
        # Busca exata primeiro
        if zona in self.parametros_zona:
            return self.parametros_zona[zona]
        
        # Busca normalizada
        for zone_key, params in self.parametros_zona.items():
            if zone_key.upper().replace("-", "").replace(" ", "") == zona_clean:
                return params
        
        logger.warning(f"Zona não encontrada: {zona}")
        return None
    
    def validar_parametro(self, zona: str, parametro: str, valor: float) -> Dict[str, Any]:
        """
        Valida um parâmetro específico contra a legislação oficial
        """
        params_zona = self.get_parametros_zona(zona)
        
        if not params_zona:
            return {
                "conforme": False,
                "erro": f"Zona {zona} não encontrada na legislação",
                "observacao": "Consulte legislação específica"
            }
        
        # Mapeamento de parâmetros
        param_mapping = {
            "taxa_ocupacao": ("taxa_ocupacao_max", "máximo", "%"),
            "coeficiente_aproveitamento": ("coeficiente_aproveitamento_max", "máximo", ""),
            "altura_edificacao": ("altura_max_metros", "máximo", "m"),
            "altura_pavimentos": ("altura_max_pavimentos", "máximo", "pavimentos"),
            "recuo_frontal": ("recuo_frontal_min", "mínimo", "m"),
            "recuos_laterais": ("recuos_laterais_min", "mínimo", "m"),
            "recuo_fundos": ("recuo_fundos_min", "mínimo", "m"),
            "taxa_permeabilidade": ("taxa_permeabilidade_min", "mínimo", "%"),
            "area_permeavel": ("taxa_permeabilidade_min", "mínimo", "%")  # Alias
        }
        
        if parametro not in param_mapping:
            return {
                "conforme": False,
                "erro": f"Parâmetro {parametro} não reconhecido",
                "observacao": "Verifique nome do parâmetro"
            }
        
        param_key, tipo_limite, unidade = param_mapping[parametro]
        
        if param_key not in params_zona:
            return {
                "conforme": False,
                "erro": f"Parâmetro {parametro} não definido para zona {zona}",
                "observacao": "Consulte legislação específica"
            }
        
        limite = params_zona[param_key]
        
        # Validação conforme tipo de limite
        if tipo_limite == "máximo":
            conforme = valor <= limite
            comparacao = "≤"
            status_texto = "não excede" if conforme else "excede"
        else:  # mínimo
            conforme = valor >= limite
            comparacao = "≥" 
            status_texto = "atende" if conforme else "não atende"
        
        # Formatação específica para cada parâmetro
        if parametro in ["taxa_permeabilidade", "area_permeavel"]:
            # Taxa de permeabilidade tem lógica especial
            if tipo_limite == "mínimo":
                observacao = f"Exigido MÍNIMO de {limite}% de área permeável"
            else:
                observacao = f"Permitido MÁXIMO de {limite}% de área permeável"
        else:
            observacao = f"Limite {tipo_limite}: {limite}{unidade}"
        
        return {
            "conforme": conforme,
            "valor_projeto": valor,
            "limite_legal": limite,
            "tipo_limite": tipo_limite,
            "comparacao": comparacao,
            "unidade": unidade,
            "observacao": observacao,
            "status": f"[OK] Conforme" if conforme else f"[ERRO] Nao Conforme",
            "detalhes": f"Valor {valor}{unidade} {status_texto} o {tipo_limite} legal de {limite}{unidade}"
        }
    
    def gerar_tabela_comparativa(self, zona: str, parametros_projeto: Dict[str, float]) -> Dict[str, Any]:
        """
        Gera tabela comparativa completa entre projeto e legislação
        """
        params_zona = self.get_parametros_zona(zona)
        
        if not params_zona:
            return {
                "erro": f"Zona {zona} não encontrada",
                "zona_valida": False
            }
        
        tabela = {
            "zona": zona,
            "nome_zona": params_zona.get("nome", zona),
            "descricao": params_zona.get("descricao", ""),
            "zona_valida": True,
            "parametros": {},
            "resumo": {
                "total_parametros": 0,
                "conformes": 0,
                "nao_conformes": 0,
                "aprovado": True
            }
        }
        
        # Validar cada parâmetro do projeto
        for param_nome, valor_projeto in parametros_projeto.items():
            if valor_projeto is None:
                continue
            
            validacao = self.validar_parametro(zona, param_nome, valor_projeto)
            tabela["parametros"][param_nome] = validacao
            
            tabela["resumo"]["total_parametros"] += 1
            
            if validacao.get("conforme", False):
                tabela["resumo"]["conformes"] += 1
            else:
                tabela["resumo"]["nao_conformes"] += 1
                tabela["resumo"]["aprovado"] = False
        
        return tabela
    
    def listar_zonas_disponiveis(self) -> Dict[str, str]:
        """
        Lista todas as zonas disponíveis com suas descrições
        """
        return {
            zona: params["nome"] 
            for zona, params in self.parametros_zona.items()
        }

def test_parametros_oficiais():
    """
    Teste dos parâmetros oficiais
    """
    print("TESTE DOS PARÂMETROS OFICIAIS DE CURITIBA")
    print("=" * 60)
    
    params = ParametrosOficiaisCuritiba()
    
    # Teste 1: SEHIS - caso do engenheiro
    print("\n1. TESTE SEHIS - Caso do engenheiro:")
    zona = "SEHIS"
    projeto = {
        "taxa_permeabilidade": 25.0,  # Valor que o engenheiro informou
        "recuo_frontal": 5.0  # Valor que foi rejeitado incorretamente
    }
    
    resultado = params.gerar_tabela_comparativa(zona, projeto)
    
    print(f"   Zona: {resultado['nome_zona']}")
    for param, validacao in resultado['parametros'].items():
        print(f"   {param}: {validacao['status']}")
        print(f"      Projeto: {validacao['valor_projeto']}")
        print(f"      Legal: {validacao['limite_legal']} ({validacao['tipo_limite']})")
        print(f"      {validacao['observacao']}")
    
    # Teste 2: ZR-4 padrão
    print(f"\n2. TESTE ZR-4 - Padrão:")
    resultado2 = params.gerar_tabela_comparativa("ZR-4", projeto)
    
    print(f"   Zona: {resultado2['nome_zona']}")
    for param, validacao in resultado2['parametros'].items():
        print(f"   {param}: {validacao['status']}")
    
    print(f"\nZonas disponíveis: {list(params.listar_zonas_disponiveis().keys())}")

if __name__ == "__main__":
    test_parametros_oficiais()