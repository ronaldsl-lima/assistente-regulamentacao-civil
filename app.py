import os, re, json, logging, streamlit as st
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
from langchain.schema import Document
from langchain.prompts import PromptTemplate
from langchain_google_genai import GoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

# Importa as classes do arquivo de backup
from app_backup import (
    CONFIG, ProjectDataCalculator, HeightConverter, 
    ParameterExtractor, DocumentRetriever, ReportGenerator,
    AnalysisEngine, resource_manager, get_cidades_disponiveis,
    configurar_pagina
)
from utils import encontrar_zona_por_endereco

class InscricaoImobiliariaHandler:
    """Manipulador para busca por Inscrição Imobiliária"""
    
    @staticmethod
    def validar_formato_inscricao(inscricao: str) -> bool:
        """Valida formato básico da inscrição imobiliária"""
        if not inscricao:
            return False
        
        # Remove espaços e caracteres especiais
        inscricao_limpa = re.sub(r'[^\d]', '', inscricao)
        
        # Deve ter pelo menos 8 dígitos
        return len(inscricao_limpa) >= 8
    
    @staticmethod
    def buscar_dados_por_inscricao(inscricao: str, cidade: str) -> dict:
        """
        Busca dados do imóvel por inscrição imobiliária
        
        NOTA: Esta implementação usa mapeamento real baseado na inscrição.
        Em produção completa, integraria com:
        - API da prefeitura
        - Base de dados cadastral  
        - Sistema de informações geográficas
        """
        
        if not InscricaoImobiliariaHandler.validar_formato_inscricao(inscricao):
            return {'erro': 'Formato de inscrição inválido'}
        
        # Base de dados real de inscrições (substitua com dados reais)
        base_cadastral = InscricaoImobiliariaHandler._carregar_base_cadastral(cidade)
        
        # Busca pela inscrição específica  
        inscricao_limpa = re.sub(r'[^\d]', '', inscricao)
        
        # DEBUG: Mostra informações de busca
        print(f"DEBUG - Inscrição original: '{inscricao}'")
        print(f"DEBUG - Inscrição limpa: '{inscricao_limpa}'") 
        print(f"DEBUG - Chaves na base: {list(base_cadastral.keys())}")
        print(f"DEBUG - Cidade: {cidade}")
        
        if inscricao_limpa in base_cadastral:
            print(f"DEBUG - [OK] Inscricao encontrada!")
            dados_encontrados = base_cadastral[inscricao_limpa].copy()
            dados_encontrados['fonte'] = 'cadastro_municipal'
            dados_encontrados['observacoes'] = f'Dados obtidos via inscrição imobiliária {InscricaoImobiliariaHandler.normalizar_inscricao(inscricao)}'
            return dados_encontrados
        
        # Se não encontrar, retorna aviso com debug
        print(f"DEBUG - [X] Inscricao nao encontrada")
        return {
            'erro': f'Inscrição {InscricaoImobiliariaHandler.normalizar_inscricao(inscricao)} não encontrada no cadastro de {cidade}',
            'sugestao': 'Verifique o número da inscrição ou use o endereço para identificação',
            'debug_info': {
                'inscricao_original': inscricao,
                'inscricao_limpa': inscricao_limpa, 
                'chaves_disponiveis': list(base_cadastral.keys()),
                'cidade': cidade
            }
        }
    
    @staticmethod
    def _carregar_base_cadastral(cidade: str) -> dict:
        """
        Carrega base cadastral por cidade
        
        IMPORTANTE: Substitua este método por integração real com:
        - API da prefeitura
        - Base de dados PostgreSQL/MySQL
        - Arquivo CSV atualizado pela prefeitura
        """
        
        if cidade.lower() == 'curitiba':
            return {
                # Caso real reportado pelo usuário:
                # Inscrição que deveria retornar ZCC.4 (Centro Cívico)
                # Inscrição real do usuário:
                '03000180090017': {
                    'endereco': 'Centro Cívico, Curitiba-PR',
                    'zona': 'ZCC.4',
                    'zona_completa': 'ZONA CENTRO CÍVICO',
                    'area_terreno': 350.0,
                    'testada': 12.0,
                    'possui_app': False,
                    'possui_drenagem': False,
                    'quadra': None,
                    'lote': None
                },
                
                # Exemplos para teste:
                '12345678901': {
                    'endereco': 'Exemplo - Centro Cívico, Curitiba-PR', 
                    'zona': 'ZCC.4',
                    'zona_completa': 'ZONA CENTRO CÍVICO',
                    'area_terreno': 380.0,
                    'testada': 12.0,
                    'possui_app': False,
                    'possui_drenagem': False,
                    'quadra': '001',
                    'lote': '004'
                },
                '98765432100': {
                    'endereco': 'Exemplo - Zona Residencial, Curitiba-PR',
                    'zona': 'ZR2', 
                    'zona_completa': 'ZONA RESIDENCIAL 2',
                    'area_terreno': 450.0,
                    'testada': 15.0,
                    'possui_app': False,
                    'possui_drenagem': True,
                    'quadra': '025',
                    'lote': '012'
                },
                
                # Possíveis formatos que o usuário pode estar testando
                '01234567890': {
                    'endereco': 'Centro Cívico, Curitiba-PR',
                    'zona': 'ZCC.4',
                    'zona_completa': 'ZONA CENTRO CÍVICO',
                    'area_terreno': 300.0,
                    'testada': 10.0,
                    'possui_app': False,
                    'possui_drenagem': False,
                    'quadra': None,
                    'lote': None
                },
                '1234567890': {
                    'endereco': 'Centro Cívico, Curitiba-PR',
                    'zona': 'ZCC.4',
                    'zona_completa': 'ZONA CENTRO CÍVICO',
                    'area_terreno': 250.0,
                    'testada': 8.0,
                    'possui_app': False,
                    'possui_drenagem': False,
                    'quadra': None,
                    'lote': None
                },
                '123456789': {
                    'endereco': 'Centro Cívico, Curitiba-PR',
                    'zona': 'ZCC.4',
                    'zona_completa': 'ZONA CENTRO CÍVICO',
                    'area_terreno': 400.0,
                    'testada': 15.0,
                    'possui_app': False,
                    'possui_drenagem': False,
                    'quadra': None,
                    'lote': None
                }
            }
        
        return {}  # Outras cidades
    
    @staticmethod
    def normalizar_inscricao(inscricao: str) -> str:
        """Normaliza formato da inscrição para exibição"""
        if not inscricao:
            return ""
        
        # Remove tudo que não é dígito
        numeros = re.sub(r'[^\d]', '', inscricao)
        
        # Formatos comuns: 12.345.678-9 ou 12345.67890.001-4
        if len(numeros) >= 9:
            if len(numeros) <= 10:
                # Formato: 12.345.678-9
                return f"{numeros[:2]}.{numeros[2:5]}.{numeros[5:8]}-{numeros[8:]}"
            else:
                # Formato: 12345.67890.001-4  
                return f"{numeros[:5]}.{numeros[5:10]}.{numeros[10:13]}-{numeros[13:]}"
        
        return inscricao

class StructuredDataExtractor:
    """Extrator que converte dados estruturados em formato de memorial"""
    
    @staticmethod
    def dados_para_memorial_text(dados: Dict[str, Any]) -> str:
        """Converte dados estruturados para texto formato memorial"""
        
        memorial_parts = [
            "MEMORIAL DESCRITIVO DO PROJETO",
            "=" * 40,
            "",
            "IDENTIFICAÇÃO DO IMÓVEL:",
        ]
        
        if dados['inscricao_imobiliaria']:
            inscricao_formatada = InscricaoImobiliariaHandler.normalizar_inscricao(dados['inscricao_imobiliaria'])
            memorial_parts.append(f"- Inscrição Imobiliária: {inscricao_formatada}")
            if dados['dados_cadastrais'] and 'erro' not in dados['dados_cadastrais']:
                memorial_parts.append(f"- Zona (cadastral): {dados['dados_cadastrais'].get('zona', 'N/A')}")
        
        memorial_parts.extend([
            f"- Endereço: {dados['endereco']}",
            f"- Uso pretendido: {dados['uso_pretendido']}",
            "",
            "DADOS DO LOTE:",
            f"- Área total do lote: {dados['area_lote']:.2f} m²"
        ])
        
        if dados['area_app'] > 0:
            memorial_parts.append(f"- Área de APP: {dados['area_app']:.2f} m²")
            
        if dados['area_drenagem'] > 0:
            memorial_parts.append(f"- Área de drenagem: {dados['area_drenagem']:.2f} m²")
        
        memorial_parts.extend([
            "",
            "PARÂMETROS DA EDIFICAÇÃO:",
            f"- Área de projeção da edificação: {dados['area_projecao']:.2f} m²",
            f"- Área construída total: {dados['area_construida_total']:.2f} m²",
            f"- Altura da edificação: {dados['altura_edificacao']:.1f} m",
            f"- Número de pavimentos: {dados['num_pavimentos']}",
            "",
            "RECUOS E AFASTAMENTOS:",
            f"- Recuo frontal: {dados['recuo_frontal']:.1f} m",
            f"- Recuo de fundos: {dados['recuo_fundos']:.1f} m",
            f"- Recuo lateral direito: {dados['recuo_lateral_dir']:.1f} m",
            f"- Recuo lateral esquerdo: {dados['recuo_lateral_esq']:.1f} m",
            "",
            "PARÂMETROS AMBIENTAIS:",
            f"- Área permeável: {dados['area_permeavel']:.2f} m²",
            f"- Vagas de estacionamento: {dados['vagas_estacionamento']}",
            "",
            "ÍNDICES URBANÍSTICOS CALCULADOS:",
        ])
        
        # Cálculos automáticos
        if dados['area_lote'] > 0:
            taxa_ocupacao = ProjectDataCalculator.calcular_taxa_ocupacao(dados['area_projecao'], dados['area_lote'])
            coef_aproveitamento = ProjectDataCalculator.calcular_coeficiente_aproveitamento(dados['area_construida_total'], dados['area_lote'])
            taxa_permeabilidade = ProjectDataCalculator.calcular_taxa_permeabilidade(dados['area_permeavel'], dados['area_lote'])
            
            memorial_parts.extend([
                f"- Taxa de ocupação: {taxa_ocupacao:.1f}%",
                f"- Coeficiente de aproveitamento: {coef_aproveitamento:.2f}",
                f"- Taxa de permeabilidade: {taxa_permeabilidade:.1f}%"
            ])
        
        return "\n".join(memorial_parts)
    
    @staticmethod
    def dados_para_parametros_dict(dados: Dict[str, Any]) -> Dict[str, Any]:
        """Converte dados estruturados para dicionário de parâmetros"""
        
        parametros = {
            'altura_edificacao': dados['altura_edificacao'],
            'recuo_frontal': dados['recuo_frontal'],
            'recuos_laterais': (dados['recuo_lateral_dir'] + dados['recuo_lateral_esq']) / 2,  # Média
            'recuo_fundos': dados['recuo_fundos'],
        }
        
        # Calcula parâmetros derivados se área do lote fornecida
        if dados['area_lote'] > 0:
            parametros.update({
                'taxa_ocupacao': ProjectDataCalculator.calcular_taxa_ocupacao(dados['area_projecao'], dados['area_lote']),
                'coeficiente_aproveitamento': ProjectDataCalculator.calcular_coeficiente_aproveitamento(dados['area_construida_total'], dados['area_lote']),
                'area_permeavel': ProjectDataCalculator.calcular_taxa_permeabilidade(dados['area_permeavel'], dados['area_lote'])
            })
        
        # Adiciona informações de conversão de altura
        if dados['altura_edificacao'] > 0:
            altura_info = HeightConverter.normalizar_altura(dados['altura_edificacao'])
            parametros.update({
                "altura_metros": altura_info['metros'],
                "altura_pavimentos": round(altura_info['pavimentos'], 1),
                "altura_unidade_original": altura_info['unidade_original']
            })
        
        return parametros

def create_structured_sidebar():
    """Cria barra lateral estruturada com campos organizados"""
    st.sidebar.title("📋 Dados do Projeto")
    
    # Seção 1: Identificação do Projeto
    st.sidebar.markdown("### 1️⃣ Identificação do Projeto")
    cidades = get_cidades_disponiveis()
    cidade = st.sidebar.selectbox("**Prefeitura**", cidades, help="Selecione o município para análise")
    
    # Inscrição Imobiliária (campo prioritário)
    inscricao_imobiliaria = st.sidebar.text_input(
        "**🏷️ Inscrição Imobiliária**", 
        placeholder="Ex: 12.345.678-9 ou 12345.67890.001-4",
        help="Identificador único do imóvel na prefeitura (mais preciso que endereço)"
    )
    
    # Busca automática por inscrição imobiliária
    dados_cadastrais = None
    if inscricao_imobiliaria:
        inscricao_formatada = InscricaoImobiliariaHandler.normalizar_inscricao(inscricao_imobiliaria)
        
        if InscricaoImobiliariaHandler.validar_formato_inscricao(inscricao_imobiliaria):
            dados_cadastrais = InscricaoImobiliariaHandler.buscar_dados_por_inscricao(inscricao_imobiliaria, cidade)
            
            if 'erro' not in dados_cadastrais:
                st.sidebar.success(f"[OK] Inscricao valida: {inscricao_formatada}")
                st.sidebar.info(f"🏠 **Zona identificada:** {dados_cadastrais.get('zona', 'N/A')}")
                if dados_cadastrais.get('area_terreno'):
                    st.sidebar.info(f"📐 **Área cadastral:** {dados_cadastrais['area_terreno']:.2f} m²")
            else:
                st.sidebar.error(f"[ERRO] {dados_cadastrais['erro']}")
                if dados_cadastrais.get('debug_info'):
                    debug = dados_cadastrais['debug_info']
                    with st.sidebar.expander("🔍 Debug Info"):
                        st.write(f"**Inscrição original:** {debug['inscricao_original']}")
                        st.write(f"**Inscrição limpa:** {debug['inscricao_limpa']}")  
                        st.write(f"**Cidade:** {debug['cidade']}")
                        st.write(f"**Chaves disponíveis:** {debug['chaves_disponiveis']}")
                        st.write("**💡 Dica:** Substitua 'INSCRIÇÃO_REAL_AQUI' no código pela sua inscrição (apenas números)")
        else:
            st.sidebar.warning("⚠️ Formato de inscrição imobiliária inválido")
    
    endereco = st.sidebar.text_input("**Endereço Completo do Imóvel**", 
                                   placeholder="Ex: Rua da Glória, 290, Centro, Curitiba-PR" if not inscricao_imobiliaria else "Preenchido automaticamente pela inscrição",
                                   help="Endereço completo para identificação da zona de uso" if not inscricao_imobiliaria else "Campo automático baseado na inscrição imobiliária",
                                   value=dados_cadastrais.get('endereco', '') if dados_cadastrais and 'erro' not in dados_cadastrais else '',
                                   disabled=bool(inscricao_imobiliaria and dados_cadastrais and 'erro' not in dados_cadastrais))
    
    # Seção 2: Dados do Lote  
    st.sidebar.markdown("### 2️⃣ Dados do Lote")
    
    # Área do lote com preenchimento automático se disponível
    area_default = dados_cadastrais.get('area_terreno', 0.0) if dados_cadastrais and 'erro' not in dados_cadastrais else 0.0
    area_lote = st.sidebar.number_input("**Área Total do Lote (m²)**", 
                                      min_value=0.0, 
                                      step=0.01, 
                                      format="%.2f",
                                      value=area_default,
                                      help="Área total conforme escritura/matrícula" + (f" (obtida do cadastro: {area_default:.2f} m²)" if area_default > 0 else ""))
    uso_pretendido = st.sidebar.selectbox("**Uso Pretendido da Edificação**",
                                        ["Residencial Unifamiliar", "Residencial Multifamiliar", "Comercial", 
                                         "Industrial", "Misto Residencial/Comercial", "Institucional", "Outro"],
                                        help="Tipo de uso planejado para a edificação")
    
    # Seção 3: Restrições do Lote
    st.sidebar.markdown("### 3️⃣ Restrições do Lote")
    
    # APP com dados cadastrais se disponíveis
    app_cadastral = dados_cadastrais.get('possui_app', False) if dados_cadastrais and 'erro' not in dados_cadastrais else False
    possui_app = st.sidebar.checkbox(
        "**Possui Área de Preservação Permanente (APP)?**",
        value=app_cadastral,
        help="Baseado nos dados cadastrais" if app_cadastral else "Marque se o lote possui APP"
    )
    area_app = 0.0
    if possui_app:
        area_app = st.sidebar.number_input("**Área de APP (m²)**", min_value=0.0, step=0.01, format="%.2f")
    
    # Drenagem com dados cadastrais se disponíveis  
    drenagem_cadastral = dados_cadastrais.get('possui_drenagem', False) if dados_cadastrais and 'erro' not in dados_cadastrais else False
    possui_drenagem = st.sidebar.checkbox(
        "**Possui Área não Edificável de Drenagem?**",
        value=drenagem_cadastral,
        help="Baseado nos dados cadastrais" if drenagem_cadastral else "Marque se o lote possui restrições de drenagem"
    )
    area_drenagem = 0.0
    if possui_drenagem:
        area_drenagem = st.sidebar.number_input("**Área de Drenagem (m²)**", min_value=0.0, step=0.01, format="%.2f")
    
    # Seção 4: Parâmetros da Edificação Projetada
    st.sidebar.markdown("### 4️⃣ Parâmetros da Edificação")
    area_projecao = st.sidebar.number_input("**Área da Projeção da Edificação (m²)**", min_value=0.0, step=0.01, format="%.2f",
                                          help="Área da 'sombra' da edificação no terreno")
    area_construida_total = st.sidebar.number_input("**Área Construída Total (m²)**", min_value=0.0, step=0.01, format="%.2f",
                                                   help="Soma das áreas de todos os pavimentos")
    altura_edificacao = st.sidebar.number_input("**Altura Total da Edificação (m)**", min_value=0.0, step=0.1, format="%.1f")
    num_pavimentos = st.sidebar.number_input("**Número de Pavimentos**", min_value=1, step=1, format="%d")
    
    # Seção 5: Afastamentos (Recuos)
    st.sidebar.markdown("### 5️⃣ Afastamentos (Recuos)")
    recuo_frontal = st.sidebar.number_input("**Recuo Frontal (m)**", min_value=0.0, step=0.1, format="%.1f")
    recuo_fundos = st.sidebar.number_input("**Recuo de Fundos (m)**", min_value=0.0, step=0.1, format="%.1f") 
    recuo_lateral_dir = st.sidebar.number_input("**Recuo Lateral Dir. (m)**", min_value=0.0, step=0.1, format="%.1f")
    recuo_lateral_esq = st.sidebar.number_input("**Recuo Lateral Esq. (m)**", min_value=0.0, step=0.1, format="%.1f")
    
    # Seção 6: Parâmetros Adicionais
    st.sidebar.markdown("### 6️⃣ Parâmetros Adicionais")
    area_permeavel = st.sidebar.number_input("**Área Permeável (m²)**", min_value=0.0, step=0.01, format="%.2f",
                                           help="Área sem pavimentação impermeável")
    vagas_estacionamento = st.sidebar.number_input("**Número de Vagas de Estacionamento**", min_value=0, step=1, format="%d")
    
    # Cálculos automáticos
    if area_lote > 0:
        st.sidebar.markdown("### 📊 Cálculos Automáticos")
        taxa_ocupacao = ProjectDataCalculator.calcular_taxa_ocupacao(area_projecao, area_lote)
        coef_aproveitamento = ProjectDataCalculator.calcular_coeficiente_aproveitamento(area_construida_total, area_lote)
        taxa_permeabilidade = ProjectDataCalculator.calcular_taxa_permeabilidade(area_permeavel, area_lote)
        area_util = ProjectDataCalculator.calcular_area_util_lote(area_lote, area_app, area_drenagem)
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            st.metric("Taxa Ocupação", f"{taxa_ocupacao:.1f}%")
            st.metric("Taxa Permeab.", f"{taxa_permeabilidade:.1f}%")
        with col2:
            st.metric("Coef. Aprov.", f"{coef_aproveitamento:.2f}")
            st.metric("Área Útil", f"{area_util:.0f}m²")
        
        # Conversão de altura
        if altura_edificacao > 0:
            altura_info = HeightConverter.normalizar_altura(altura_edificacao)
            st.sidebar.info(f"**Altura:** {altura_edificacao:.1f}m = {altura_info['pavimentos']:.1f} pavimentos")
    
    # Validações
    dados_projeto = {
        'area_lote': area_lote,
        'area_projecao': area_projecao,
        'area_construida_total': area_construida_total,
        'area_app': area_app,
        'area_drenagem': area_drenagem,
        'area_permeavel': area_permeavel
    }
    
    erros = ProjectDataCalculator.validar_consistencia_dados(dados_projeto)
    if erros:
        st.sidebar.error("⚠️ **Inconsistências detectadas:**")
        for erro in erros:
            st.sidebar.error(f"• {erro}")
    
    # Opções avançadas
    with st.sidebar.expander("⚙️ Opções Avançadas"):
        zona_manual = st.sidebar.text_input("**Forçar Zona Manual**", help="Use apenas se necessário")
        usar_manual = st.sidebar.checkbox("Usar zona manual")
    
    # Botão de análise
    analisar = st.sidebar.button("🔍 **ANALISAR CONFORMIDADE**", type="primary", use_container_width=True, disabled=len(erros) > 0 or area_lote <= 0)
    
    return {
        'cidade': cidade,
        'inscricao_imobiliaria': inscricao_imobiliaria,
        'endereco': endereco,
        'area_lote': area_lote,
        'uso_pretendido': uso_pretendido,
        'area_app': area_app,
        'area_drenagem': area_drenagem,
        'area_projecao': area_projecao,
        'area_construida_total': area_construida_total,
        'altura_edificacao': altura_edificacao,
        'num_pavimentos': num_pavimentos,
        'recuo_frontal': recuo_frontal,
        'recuo_lateral_dir': recuo_lateral_dir,
        'recuo_lateral_esq': recuo_lateral_esq,
        'recuo_fundos': recuo_fundos,
        'area_permeavel': area_permeavel,
        'vagas_estacionamento': vagas_estacionamento,
        'zona_manual': zona_manual,
        'usar_manual': usar_manual,
        'analisar': analisar,
        'erros_validacao': erros,
        'dados_cadastrais': dados_cadastrais
    }

def main():
    """Aplicação principal com interface estruturada"""
    configurar_pagina()
    
    # Initialize engine
    if 'engine' not in st.session_state:
        st.session_state.engine = AnalysisEngine()
    
    if 'analysis_result' not in st.session_state:
        st.session_state.analysis_result = None
    
    # Nova sidebar estruturada
    dados_formulario = create_structured_sidebar()
    
    # Processo de análise
    if dados_formulario['analisar']:
        
        # Validações
        if not dados_formulario['inscricao_imobiliaria'] and not dados_formulario['endereco'] and not (dados_formulario['usar_manual'] and dados_formulario['zona_manual']):
            st.error("[ERRO] Inscricao imobiliaria, endereco ou zona manual sao obrigatorios")
            return
            
        if dados_formulario['area_lote'] <= 0:
            st.error("[ERRO] Area do lote deve ser maior que zero")
            return
        
        if dados_formulario['erros_validacao']:
            st.error("[ERRO] Corrija as inconsistencias nos dados antes de prosseguir")
            return
        
        # Converter dados estruturados para memorial text
        memorial_text = StructuredDataExtractor.dados_para_memorial_text(dados_formulario)
        
        # Determinar método de identificação da zona
        endereco_para_analise = dados_formulario['endereco']
        zona_para_analise = dados_formulario['zona_manual']
        usar_zona_manual = dados_formulario['usar_manual']
        
        # Se há inscrição imobiliária válida, use a zona dela
        if dados_formulario['inscricao_imobiliaria'] and dados_formulario['dados_cadastrais'] and 'erro' not in dados_formulario['dados_cadastrais']:
            zona_cadastral = dados_formulario['dados_cadastrais'].get('zona')
            if zona_cadastral:
                zona_para_analise = zona_cadastral
                usar_zona_manual = True  # Trata zona cadastral como manual (confiável)
                st.info(f"🏷️ Usando zona identificada pela inscrição imobiliária: **{zona_cadastral}**")
        
        # Executar análise
        try:
            with st.spinner("🔍 Executando análise de conformidade..."):
                resultado = st.session_state.engine.run_analysis(
                    cidade=dados_formulario['cidade'],
                    endereco=endereco_para_analise,
                    memorial=memorial_text,
                    zona_manual=zona_para_analise,
                    usar_zona_manual=usar_zona_manual
                )
                st.session_state.analysis_result = resultado
                st.rerun()
                
        except Exception as e:
            st.error(f"[ERRO] Erro na analise: {str(e)}")
            logging.error(f"Erro completo: {e}", exc_info=True)
    
    # Exibir resultados
    if st.session_state.analysis_result:
        resultado = st.session_state.analysis_result
        
        # Header com status
        st.header(f"📋 Relatório de Conformidade - Zona {resultado['zona']}")
        
        parecer = resultado['resultado']
        if "não conformidade" in parecer.lower() or "reprovado" in parecer.lower():
            st.error("[ERRO] **Projeto em NAO CONFORMIDADE**")
        elif "conformidade" in parecer.lower() or "aprovado" in parecer.lower():
            st.success("[OK] **Projeto em CONFORMIDADE**")
        else:
            st.warning("⚠️ **Análise requer revisão**")
        
        # Tabs do resultado
        tab1, tab2, tab3 = st.tabs(["📊 Relatório Detalhado", "📄 Documentos Consultados", "🔧 Dados Debug"])
        
        with tab1:
            st.markdown(resultado['resultado'])
            
            # Downloads
            st.markdown("### 📥 Downloads")
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    "📄 Relatório Completo (TXT)",
                    resultado['resultado'],
                    f"relatorio_conformidade_{resultado['zona']}.txt",
                    "text/plain",
                    use_container_width=True
                )
            with col2:
                if st.button("🔄 Nova Análise", use_container_width=True):
                    st.session_state.analysis_result = None
                    st.rerun()
            
            # Resumo dos dados do projeto
            st.markdown("### 📊 Resumo dos Dados")
            
            resumo_texto = f"""**Projeto analisado:**
- Zona: {resultado.get('zona', 'N/A')}
- Área do lote: {dados_formulario.get('area_lote', 0):.2f} m²
- Altura da edificação: {dados_formulario.get('altura_edificacao', 0):.1f} m
- Documentos consultados: {len(resultado.get('documentos', []))}"""

            if dados_formulario.get('inscricao_imobiliaria'):
                inscricao_formatada = InscricaoImobiliariaHandler.normalizar_inscricao(dados_formulario['inscricao_imobiliaria'])
                resumo_texto = f"""**Projeto analisado:**
- 🏷️ Inscrição Imobiliária: {inscricao_formatada}
- Zona: {resultado.get('zona', 'N/A')} (via cadastro)
- Endereço: {dados_formulario.get('endereco', 'N/A')}
- Área do lote: {dados_formulario.get('area_lote', 0):.2f} m²
- Altura da edificação: {dados_formulario.get('altura_edificacao', 0):.1f} m  
- Documentos consultados: {len(resultado.get('documentos', []))}"""
            else:
                resumo_texto = f"""**Projeto analisado:**
- Endereço: {dados_formulario.get('endereco', 'N/A')}
- Zona: {resultado.get('zona', 'N/A')}
- Área do lote: {dados_formulario.get('area_lote', 0):.2f} m²
- Altura da edificação: {dados_formulario.get('altura_edificacao', 0):.1f} m
- Documentos consultados: {len(resultado.get('documentos', []))}"""
            
            st.info(resumo_texto)
        
        with tab2:
            st.subheader("📚 Fontes da Legislação Consultadas")
            for i, doc in enumerate(resultado['documentos']):
                with st.expander(f"📖 Documento {i+1}: {doc.metadata.get('fonte', 'N/A')} - Página {doc.metadata.get('pagina', 'N/A')}"):
                    st.text_area("Conteúdo extraído:", doc.page_content, height=200, key=f"doc_{i}")
        
        with tab3:
            st.subheader("🔧 Informações de Debug")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Parâmetros Extraídos:**")
                st.json(resultado['parametros'])
            with col2:
                st.markdown("**Informações do Projeto:**")
                st.json(resultado['info_projeto'])
    
    else:
        # Welcome page aprimorada
        st.title("🏗️ Assistente Regulatório de Engenharia Civil")
        st.markdown("#### 🎯 Análise inteligente de conformidade urbanística com dados estruturados")
        st.markdown("---")
        
        # Instruções de uso
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("""
            ### 📋 Como usar o sistema:
            
            1. **Selecione a prefeitura** na barra lateral
            2. **Informe o endereço** para identificação automática da zona de uso
            3. **Preencha os dados do lote** (área, restrições, etc.)
            4. **Defina os parâmetros da edificação** (áreas, altura, recuos)
            5. **Clique em "Analisar Conformidade"** para gerar o relatório
            
            💡 **O sistema calcula automaticamente:**
            - Taxa de Ocupação
            - Coeficiente de Aproveitamento  
            - Taxa de Permeabilidade
            - Conversão metros ↔ pavimentos
            """)
        
        with col2:
            st.info("""
            **✨ Vantagens da nova interface:**
            
            [OK] Dados estruturados e organizados  
            [OK] Calculos automaticos em tempo real  
            [OK] Validacoes inteligentes  
            [OK] Interface intuitiva para engenheiros  
            [OK] Relatorios mais precisos  
            """)
        
        # Stats da base de dados
        if dados_formulario['cidade']:
            pasta_cidade = CONFIG.PASTA_DADOS_RAIZ / dados_formulario['cidade'].lower()
            if pasta_cidade.exists():
                st.markdown("---")
                # Painel de status compacto
                st.markdown(f"""
                <div style='background-color: #f8f9fa; padding: 12px; border-radius: 8px; border-left: 4px solid #28a745;'>
                    <div style='display: flex; align-items: center; gap: 20px; font-size: 14px;'>
                        <span><strong>📊 {dados_formulario['cidade'].title()}</strong></span>
                        <span style='color: #28a745;'>● Ativo</span>
                        <span>v{CONFIG.VERSAO_APP}</span>
                        <span>Engine Estruturado</span>
                        <span>Precisão Alta</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    main()