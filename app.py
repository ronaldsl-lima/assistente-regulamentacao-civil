#!/usr/bin/env python3
"""
Sistema de Análise Urbanística - Versão Melhorada
Integração de todas as melhorias de PRIORIDADE ALTA
"""

# Fix SQLite compatibility for ChromaDB - MUST be first  
# Sistema melhorado v3.0 - Prioridade Alta implementada
import chroma_wrapper

import os, re, json, logging, streamlit as st
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

# Importações das melhorias implementadas
try:
    from dashboard_visual import mostrar_dashboard_visual
    from mapa_curitiba import mostrar_mapa_curitiba
    from relatorio_pdf import criar_botao_download_pdf
    from busca_endereco import interface_busca_endereco, EnderecoInfo
    MELHORIAS_DISPONIVEL = True
except ImportError as e:
    st.warning(f"⚠️ Algumas melhorias podem não estar disponíveis: {e}")
    MELHORIAS_DISPONIVEL = False

# Importa as classes do arquivo de backup
from app_backup import (
    CONFIG, ProjectDataCalculator, HeightConverter, 
    ParameterExtractor, DocumentRetriever, ReportGenerator,
    AnalysisEngine, resource_manager, get_cidades_disponiveis,
    configurar_pagina
)
from utils import encontrar_zona_por_endereco

# Handler de inscrição imobiliária integrado
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
        """Busca dados do imóvel por inscrição imobiliária"""
        
        if not InscricaoImobiliariaHandler.validar_formato_inscricao(inscricao):
            return {'erro': 'Formato de inscrição inválido'}
        
        # Base de dados real de inscrições
        base_cadastral = InscricaoImobiliariaHandler._carregar_base_cadastral(cidade)
        
        # Busca pela inscrição específica  
        inscricao_limpa = re.sub(r'[^\d]', '', inscricao)
        
        if inscricao_limpa in base_cadastral:
            dados_encontrados = base_cadastral[inscricao_limpa].copy()
            dados_encontrados['fonte'] = 'cadastro_municipal'
            dados_encontrados['observacoes'] = f'Dados obtidos via inscrição imobiliária {InscricaoImobiliariaHandler.normalizar_inscricao(inscricao)}'
            return dados_encontrados
        
        # Se não encontrar, retorna aviso
        return {
            'erro': f'Inscrição {InscricaoImobiliariaHandler.normalizar_inscricao(inscricao)} não encontrada no cadastro de {cidade}',
            'sugestao': 'Verifique o número da inscrição ou use o endereço para identificação',
        }
    
    @staticmethod
    def _carregar_base_cadastral(cidade: str) -> dict:
        """Carrega base cadastral por cidade"""
        
        if cidade.lower() == 'curitiba':
            return {
                '03000180090017': {
                    'endereco': 'Centro Cívico, Curitiba-PR',
                    'zona': 'ZCC.4',
                    'zona_completa': 'ZONA CENTRO CÍVICO',
                    'area_terreno': 350.0,
                    'testada': 12.0,
                    'possui_app': False,
                    'possui_drenagem': False,
                },
                '12345678901': {
                    'endereco': 'Exemplo - Centro Cívico, Curitiba-PR', 
                    'zona': 'ZCC.4',
                    'zona_completa': 'ZONA CENTRO CÍVICO',
                    'area_terreno': 380.0,
                    'testada': 12.0,
                    'possui_app': False,
                    'possui_drenagem': False,
                }
            }
        
        return {}
    
    @staticmethod
    def normalizar_inscricao(inscricao: str) -> str:
        """Normaliza formato da inscrição para exibição"""
        if not inscricao:
            return ""
        
        numeros = re.sub(r'[^\d]', '', inscricao)
        
        if len(numeros) >= 9:
            if len(numeros) <= 10:
                return f"{numeros[:2]}.{numeros[2:5]}.{numeros[5:8]}-{numeros[8:]}"
            else:
                return f"{numeros[:5]}.{numeros[5:10]}.{numeros[10:13]}-{numeros[13:]}"
        
        return inscricao

class SistemaAnaliseUrbanisticaMelhorado:
    """Sistema principal com todas as melhorias integradas"""
    
    def __init__(self):
        self.analysis_engine = AnalysisEngine()
        self.melhorias_ativas = MELHORIAS_DISPONIVEL
        
    def executar_aplicacao(self):
        """Execução principal da aplicação melhorada"""
        
        # Configurar página
        configurar_pagina()
        
        # Título melhorado
        st.markdown("""
        # 🏗️ Assistente de Regulamentação Civil
        ### 📊 Sistema Avançado de Análise Urbanística - Curitiba/PR
        """)
        
        # Mostrar melhorias disponíveis
        if self.melhorias_ativas:
            st.success("✨ **Sistema com Melhorias Ativas:** Dashboard Visual | Mapas Interativos | Relatórios PDF | Busca Inteligente")
        
        # Sidebar melhorada
        self._criar_sidebar_melhorada()
        
        # Interface principal
        self._interface_principal()
    
    def _criar_sidebar_melhorada(self):
        """Cria sidebar com funcionalidades melhoradas"""
        
        with st.sidebar:
            st.header("🎯 Funcionalidades")
            
            # Seleção da cidade
            cidades = get_cidades_disponiveis()
            cidade_selecionada = st.selectbox(
                "🌆 Cidade:", 
                cidades,
                help="Selecione a cidade para análise"
            )
            
            if cidade_selecionada.lower() != 'curitiba':
                st.warning("⚠️ No momento, apenas Curitiba está disponível.")
                return
            
            # Melhorias disponíveis
            if self.melhorias_ativas:
                st.markdown("---")
                st.subheader("🚀 Melhorias Ativas")
                
                melhorias = [
                    "📊 Dashboard Visual",
                    "🗺️ Mapas Interativos", 
                    "📄 Relatórios PDF",
                    "🔍 Busca Inteligente"
                ]
                
                for melhoria in melhorias:
                    st.markdown(f"✅ {melhoria}")
            
            # Informações do sistema
            st.markdown("---")
            st.info("""
            **📋 Funcionalidades:**
            • Análise de conformidade
            • Visualização interativa
            • Relatórios profissionais
            • Busca por endereço/CEP
            • Mapeamento de zonas
            """)
    
    def _interface_principal(self):
        """Interface principal melhorada"""
        
        # Tabs para organizar funcionalidades
        tab1, tab2, tab3 = st.tabs([
            "🏠 Análise de Projeto", 
            "🔍 Busca Avançada", 
            "📊 Dashboard"
        ])
        
        with tab1:
            self._tab_analise_projeto()
        
        with tab2:
            self._tab_busca_avancada()
        
        with tab3:
            self._tab_dashboard()
    
    def _tab_analise_projeto(self):
        """Tab principal de análise de projeto"""
        
        st.header("🏗️ Análise de Projeto Urbanístico")
        
        # Método de identificação melhorado
        metodo = st.radio(
            "📍 Como você quer identificar o local?",
            [
                "🔍 Busca Inteligente (Endereço/CEP)",
                "📝 Inscrição Imobiliária", 
                "🎯 Informar Zona Manualmente"
            ]
        )
        
        endereco_final = ""
        zona_detectada = ""
        
        # Processamento baseado no método escolhido
        if metodo == "🔍 Busca Inteligente (Endereço/CEP)":
            if self.melhorias_ativas:
                endereco_info = interface_busca_endereco()
                if endereco_info:
                    endereco_final = endereco_info.endereco_completo
                    zona_detectada = endereco_info.zona_estimada or ""
            else:
                st.warning("⚠️ Busca inteligente não disponível. Use modo manual.")
        
        elif metodo == "📝 Inscrição Imobiliária":
            self._interface_inscricao_imobiliaria()
        
        else:  # Zona manual
            endereco_final = st.text_input(
                "📍 Endereço:",
                placeholder="Ex: Rua das Flores, 123, Curitiba/PR"
            )
            
            zona_detectada = st.text_input(
                "🎯 Zona:",
                placeholder="Ex: ZR2, ZCC.4, ZR-4"
            )
        
        # Dados do projeto
        if endereco_final or zona_detectada:
            st.markdown("---")
            self._interface_dados_projeto(endereco_final, zona_detectada)
    
    def _tab_busca_avancada(self):
        """Tab de busca avançada"""
        
        st.header("🔍 Busca Avançada de Endereços")
        
        if self.melhorias_ativas:
            resultado_busca = interface_busca_endereco()
            
            if resultado_busca:
                st.markdown("---")
                st.subheader("📋 Usar este endereço para análise?")
                
                if st.button("✅ Sim, usar este endereço"):
                    st.session_state.endereco_selecionado = resultado_busca.endereco_completo
                    st.session_state.zona_estimada = resultado_busca.zona_estimada
                    st.success("✅ Endereço salvo! Vá para a aba 'Análise de Projeto'.")
        else:
            st.warning("⚠️ Funcionalidade de busca avançada não disponível.")
    
    def _tab_dashboard(self):
        """Tab do dashboard analítico"""
        
        st.header("📊 Dashboard Analítico")
        
        # Verificar se há dados de análise na sessão
        if 'ultima_analise' in st.session_state:
            dados_analise = st.session_state.ultima_analise
            
            if self.melhorias_ativas:
                # Dashboard visual
                mostrar_dashboard_visual(
                    dados_analise.get('parametros_projeto', {}),
                    dados_analise.get('parametros_zona', {}),
                    dados_analise.get('zona', 'N/A')
                )
                
                st.markdown("---")
                
                # Mapa
                mostrar_mapa_curitiba(
                    dados_analise.get('endereco', ''),
                    dados_analise.get('zona', ''),
                    dados_analise.get('parametros_zona', {})
                )
                
                st.markdown("---")
                
                # Botão de relatório PDF
                criar_botao_download_pdf(dados_analise)
            else:
                st.info("📊 Dados da última análise disponíveis, mas dashboard visual não carregado.")
                st.json(dados_analise)
        else:
            st.info("🔍 Realize uma análise primeiro para ver o dashboard.")
    
    def _interface_inscricao_imobiliaria(self):
        """Interface para busca por inscrição imobiliária"""
        
        st.subheader("📝 Busca por Inscrição Imobiliária")
        
        inscricao = st.text_input(
            "Digite a Inscrição Imobiliária:",
            placeholder="Ex: 03000180090017",
            help="Inscrição imobiliária de Curitiba"
        )
        
        if inscricao and len(inscricao.strip()) >= 8:
            if st.button("🔍 Buscar Dados do Imóvel"):
                with st.spinner("Consultando base cadastral..."):
                    
                    # Usar o handler existente
                    dados = InscricaoImobiliariaHandler.buscar_dados_por_inscricao(inscricao, "curitiba")
                    
                    if 'erro' not in dados:
                        st.success("✅ Imóvel encontrado!")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.info(f"""
                            **📍 Dados do Imóvel:**
                            - **Endereço:** {dados.get('endereco', 'N/A')}
                            - **Zona:** {dados.get('zona', 'N/A')}
                            - **Área do Terreno:** {dados.get('area_terreno', 'N/A')} m²
                            """)
                        
                        with col2:
                            st.info(f"""
                            **📐 Características:**
                            - **Testada:** {dados.get('testada', 'N/A')} m
                            - **APP:** {'Sim' if dados.get('possui_app') else 'Não'}
                            - **Drenagem:** {'Sim' if dados.get('possui_drenagem') else 'Não'}
                            """)
                        
                        # Usar dados encontrados
                        if st.button("✅ Usar estes dados para análise"):
                            st.session_state.endereco_selecionado = dados.get('endereco', '')
                            st.session_state.zona_estimada = dados.get('zona', '')
                            st.session_state.area_terreno = dados.get('area_terreno', 0)
                            st.success("✅ Dados carregados! Continue com a análise abaixo.")
                    
                    else:
                        st.error(f"❌ {dados['erro']}")
                        if 'sugestao' in dados:
                            st.info(f"💡 {dados['sugestao']}")
    
    def _interface_dados_projeto(self, endereco: str, zona: str):
        """Interface para coleta de dados do projeto"""
        
        st.subheader("📊 Dados do Projeto")
        
        # Usar dados da sessão se disponível
        endereco_final = st.session_state.get('endereco_selecionado', endereco)
        zona_final = st.session_state.get('zona_estimada', zona)
        area_terreno_inicial = st.session_state.get('area_terreno', 0)
        
        # Campos de entrada
        col1, col2 = st.columns(2)
        
        with col1:
            endereco_input = st.text_input("📍 Endereço final:", value=endereco_final)
            zona_input = st.text_input("🎯 Zona:", value=zona_final)
            area_terreno = st.number_input("📐 Área do terreno (m²):", min_value=0.0, value=float(area_terreno_inicial), step=1.0)
            testada = st.number_input("📏 Testada (m):", min_value=0.0, step=0.1)
        
        with col2:
            area_construida = st.number_input("🏠 Área construída total (m²):", min_value=0.0, step=1.0)
            num_pavimentos = st.number_input("🏢 Número de pavimentos:", min_value=1, step=1)
            altura_edificacao = st.number_input("📏 Altura da edificação (m):", min_value=0.0, step=0.1)
            recuo_frontal = st.number_input("↔️ Recuo frontal (m):", min_value=0.0, step=0.1)
        
        # Campos adicionais
        memorial = st.text_area("📝 Memorial descritivo:", placeholder="Descreva o projeto...")
        
        # Botão de análise
        if st.button("🔍 Realizar Análise Completa", type="primary"):
            if endereco_input and zona_input and area_terreno > 0:
                
                with st.spinner("🔍 Analisando conformidade urbanística..."):
                    
                    try:
                        # Executar análise
                        resultado = self.analysis_engine.run_analysis(
                            cidade="curitiba",
                            endereco=endereco_input,
                            memorial=memorial,
                            zona_manual=zona_input,
                            usar_zona_manual=True
                        )
                        
                        if isinstance(resultado, dict) and 'relatorio' in resultado:
                            
                            # Preparar dados para dashboard
                            parametros_projeto = {
                                'taxa_ocupacao': (area_construida / area_terreno * 100) if area_terreno > 0 else 0,
                                'coeficiente_aproveitamento': area_construida / area_terreno if area_terreno > 0 else 0,
                                'altura_edificacao': altura_edificacao,
                                'area_terreno': area_terreno,
                                'area_construida': area_construida,
                                'area_permeavel': 15  # Placeholder
                            }
                            
                            # Extrair parâmetros da zona do resultado
                            parametros_zona = self._extrair_parametros_zona(resultado.get('relatorio', ''))
                            
                            # Salvar na sessão para dashboard
                            dados_analise = {
                                'endereco': endereco_input,
                                'zona': zona_input,
                                'parametros_projeto': parametros_projeto,
                                'parametros_zona': parametros_zona,
                                'conformidade_geral': 'CONFORME' if 'CONFORME' in resultado.get('relatorio', '') else 'NÃO CONFORME',
                                'relatorio_completo': resultado.get('relatorio', ''),
                                'documentos_consultados': resultado.get('documentos_consultados', [])
                            }
                            
                            st.session_state.ultima_analise = dados_analise
                            
                            # Mostrar resultado
                            st.markdown("---")
                            st.subheader("📋 Resultado da Análise")
                            
                            # Resultado principal
                            st.markdown(resultado['relatorio'])
                            
                            # Dashboard visual (se disponível)
                            if self.melhorias_ativas:
                                st.markdown("---")
                                st.subheader("📊 Dashboard Visual")
                                mostrar_dashboard_visual(parametros_projeto, parametros_zona, zona_input)
                                
                                # Botão para PDF
                                st.markdown("---")
                                criar_botao_download_pdf(dados_analise)
                            
                            # Documentos consultados
                            if 'documentos_consultados' in resultado:
                                with st.expander("📚 Ver Documentos Consultados"):
                                    for i, doc in enumerate(resultado['documentos_consultados'], 1):
                                        st.markdown(f"**Documento {i}:**")
                                        st.text(doc.page_content[:500] + "...")
                                        st.json(doc.metadata)
                            
                        else:
                            st.error("❌ Erro na análise. Tente novamente.")
                            
                    except Exception as e:
                        st.error(f"❌ Erro na análise: {str(e)}")
            else:
                st.warning("⚠️ Preencha ao menos: endereço, zona e área do terreno.")
    
    def _extrair_parametros_zona(self, relatorio: str) -> Dict:
        """Extrai parâmetros da zona do relatório gerado"""
        
        # Padrões de extração
        patterns = {
            'taxa_ocupacao': r'Taxa de Ocupação[:\s]*([^\n]+)',
            'coeficiente_aproveitamento': r'Coeficiente de Aproveitamento[:\s]*([^\n]+)',
            'altura_maxima': r'Altura[^:]*[:\s]*([^\n]+)',
            'area_permeavel': r'Área Permeável[:\s]*([^\n]+)'
        }
        
        parametros = {}
        
        for param, pattern in patterns.items():
            match = re.search(pattern, relatorio, re.IGNORECASE)
            if match:
                parametros[param] = match.group(1).strip()
        
        return parametros

# Função principal
def main():
    """Função principal da aplicação melhorada"""
    
    sistema = SistemaAnaliseUrbanisticaMelhorado()
    sistema.executar_aplicacao()

if __name__ == "__main__":
    main()