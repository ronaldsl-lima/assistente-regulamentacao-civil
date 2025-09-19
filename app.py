import streamlit as st
import pandas as pd
from datetime import datetime
import logging
import re
import math

# SOLUÇÃO DEFINITIVA: Importa as funções que consultam a API do GeoCuritiba
from geocuritiba_layer36_solution import buscar_zoneamento_definitivo, buscar_zoneamento_por_coordenadas

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Classes de Lógica de Negócio ---

class ProjectDataCalculator:
    """Calculadora de parâmetros do projeto do utilizador."""
    @staticmethod
    def calculate_project_parameters(form_data: dict) -> dict:
        """Calcula todos os índices urbanísticos a partir dos dados do formulário."""
        area_lote = form_data.get('area_terreno', 0)
        area_projecao = form_data.get('area_projecao', 0)
        area_computavel = form_data.get('area_computavel', 0)
        area_permeavel = form_data.get('area_permeavel', 0)

        taxa_ocupacao = (area_projecao / area_lote) * 100 if area_lote > 0 else 0
        coef_aproveitamento = area_computavel / area_lote if area_lote > 0 else 0
        taxa_permeabilidade = (area_permeavel / area_lote) * 100 if area_lote > 0 else 0
        
        return {
            "taxa_ocupacao_projeto": taxa_ocupacao,
            "coef_aproveitamento_projeto": coef_aproveitamento,
            "taxa_permeabilidade_projeto": taxa_permeabilidade,
        }

class AnalysisEngine:
    """Motor de Análise v8.0 - com validações críticas e regras de negócio."""

    def run_analysis(self, form_data: dict) -> dict:
        """Executa a análise completa usando a API do GeoCuritiba."""
        endereco = form_data.get('endereco')
        if not endereco:
            raise ValueError("O Endereço Completo é obrigatório para a análise.")

        with st.spinner(f"A geocodificar o endereço e a consultar os dados oficiais..."):
            api_data = buscar_zoneamento_definitivo(endereco)

        if not api_data or not api_data.get('sucesso'):
            erro = api_data.get('erro', 'Não foi possível obter dados.')
            raise ConnectionError(f"Falha na consulta à API do GeoCuritiba: {erro}")

        project_params = ProjectDataCalculator.calculate_project_parameters(form_data)
        validations = self._compare_parameters(form_data, project_params, api_data)

        return {
            'sucesso': True,
            'dados_api': api_data,
            'dados_projeto': {**form_data, **project_params},
            'validacoes': validations,
        }

    def run_analysis_by_coordinates(self, form_data: dict) -> dict:
        """Executa a análise usando coordenadas diretas."""
        latitude = form_data.get('latitude')
        longitude = form_data.get('longitude')

        if not latitude or not longitude:
            raise ValueError("Latitude e Longitude são obrigatórias para a análise.")

        with st.spinner(f"Consultando dados oficiais para as coordenadas {latitude}, {longitude}..."):
            api_data = buscar_zoneamento_por_coordenadas(latitude, longitude)

        if not api_data or not api_data.get('sucesso'):
            erro = api_data.get('erro', 'Não foi possível obter dados.')
            raise ConnectionError(f"Falha na consulta à API do GeoCuritiba: {erro}")

        project_params = ProjectDataCalculator.calculate_project_parameters(form_data)
        validations = self._compare_parameters(form_data, project_params, api_data)

        return {
            'sucesso': True,
            'dados_api': api_data,
            'dados_projeto': {**form_data, **project_params},
            'validacoes': validations,
        }

    def _compare_parameters(self, form_data: dict, project_params: dict, api_data: dict) -> list:
        """Compara todos os parâmetros críticos do projeto com os limites da API e regras de negócio."""
        validations = []
        api_params = api_data.get('parametros', {})
        zona_principal = api_data.get('zona_principal', '')

        # 1. Taxa de Ocupação
        taxa_max_api = api_params.get('taxa_ocupacao_maxima')
        if taxa_max_api is not None:
            is_conform = project_params['taxa_ocupacao_projeto'] <= float(taxa_max_api)
            validations.append({'parametro': 'Taxa de Ocupação', 'valor_projeto': f"{project_params['taxa_ocupacao_projeto']:.2f}%", 'limite_legislacao': f"Máximo: {taxa_max_api}%", 'conforme': is_conform})

        # 2. Coeficiente de Aproveitamento
        ca_basico_api = api_params.get('coef_aproveitamento_basico')
        if ca_basico_api is not None:
            is_conform = project_params['coef_aproveitamento_projeto'] <= float(ca_basico_api)
            validations.append({'parametro': 'Coef. Aproveitamento', 'valor_projeto': f"{project_params['coef_aproveitamento_projeto']:.2f}", 'limite_legislacao': f"Básico: {ca_basico_api}", 'conforme': is_conform})

        # 3. Taxa de Permeabilidade
        taxa_perm_min_api = api_params.get('taxa_permeabilidade_minima')
        if taxa_perm_min_api is not None:
            is_conform = project_params['taxa_permeabilidade_projeto'] >= float(taxa_perm_min_api)
            validations.append({'parametro': 'Taxa de Permeabilidade', 'valor_projeto': f"{project_params['taxa_permeabilidade_projeto']:.2f}%", 'limite_legislacao': f"Mínimo: {taxa_perm_min_api}%", 'conforme': is_conform})

        # 4. Altura
        pavimentos_projeto = form_data.get('num_pavimentos', 0)
        pavimentos_max_api = api_params.get('altura_maxima_pavimentos')
        if pavimentos_max_api is not None:
            is_conform = pavimentos_projeto <= int(pavimentos_max_api)
            validations.append({'parametro': 'Altura (Pavimentos)', 'valor_projeto': f"{pavimentos_projeto} pav.", 'limite_legislacao': f"Máximo: {pavimentos_max_api} pav.", 'conforme': is_conform})

        # 5. Recuo Frontal
        recuo_projeto = form_data.get('recuo_frontal', 0)
        recuo_min_api = api_params.get('recuo_frontal_minimo')
        if recuo_min_api is not None:
            is_conform = recuo_projeto >= float(recuo_min_api)
            validations.append({'parametro': 'Recuo Frontal', 'valor_projeto': f"{recuo_projeto} m", 'limite_legislacao': f"Mínimo: {recuo_min_api} m", 'conforme': is_conform})
            
        # 6. Vagas de Estacionamento
        vagas_previstas = form_data.get('vagas_previstas', 0)
        vagas_pcd = form_data.get('vagas_pcd', 0)
        vagas_idosos = form_data.get('vagas_idosos', 0)
        if vagas_previstas > 0:
            vagas_pcd_req = math.ceil(vagas_previstas * 0.02)
            vagas_idosos_req = math.ceil(vagas_previstas * 0.05)
            is_conform_pcd = vagas_pcd >= vagas_pcd_req
            is_conform_idosos = vagas_idosos >= vagas_idosos_req
            validations.append({'parametro': 'Vagas PCD (2%)', 'valor_projeto': f"{vagas_pcd} vagas", 'limite_legislacao': f"Mínimo: {vagas_pcd_req}", 'conforme': is_conform_pcd})
            validations.append({'parametro': 'Vagas Idosos (5%)', 'valor_projeto': f"{vagas_idosos} vagas", 'limite_legislacao': f"Mínimo: {vagas_idosos_req}", 'conforme': is_conform_idosos})

        # 7. Regras Específicas por Zona
        num_unidades_hab = form_data.get('unidades_habitacionais', 0)
        zona_base = zona_principal.split(' ')[0]
        if zona_base in ['ZR-1', 'ZR-2', 'ZR-3'] and num_unidades_hab > 2:
            validations.append({'parametro': 'Nº de Habitações em ZR-1/2/3', 'valor_projeto': f"{num_unidades_hab} unid.", 'limite_legislacao': "Máximo: 2", 'conforme': False})

        return validations

# --- Funções da Interface do Utilizador (UI) ---

def configurar_pagina():
    st.set_page_config(page_title="Assistente Regulatório v8.3 - Alta Precisão", page_icon="🎯", layout="wide")


def exibir_resultados(resultado):
    api_info = resultado['dados_api']
    validacoes = resultado['validacoes']

    # Exibir nível de confiança se disponível
    nivel_confianca = api_info.get('nivel_confianca', None)
    if nivel_confianca:
        if nivel_confianca >= 90:
            st.success(f"🎯 **ALTA PRECISÃO:** Resultado com {nivel_confianca}% de confiança")
        elif nivel_confianca >= 75:
            st.info(f"✅ **BOA PRECISÃO:** Resultado com {nivel_confianca}% de confiança")
        else:
            st.warning(f"⚠️ **PRECISÃO MODERADA:** Resultado com {nivel_confianca}% de confiança")

    st.header(f"📋 Relatório de Análise | Zona Principal: {api_info['zona_principal']}")
    st.caption(f"Análise baseada nos dados oficiais via API GeoCuritiba. Fonte: {api_info['fonte']}")
    
    st.subheader("1. Conformidade dos Parâmetros")
    
    df_data = [{'Parâmetro': v['parametro'], 'Projeto': v['valor_projeto'], 'Legislação': v['limite_legislacao'], 'Status': "✅ Conforme" if v['conforme'] else "❌ NÃO CONFORME"} for v in validacoes]
    df = pd.DataFrame(df_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    num_nao_conformes = sum(1 for v in validacoes if not v['conforme'])
    if num_nao_conformes == 0:
        st.success("🎉 **PARECER: APROVADO.** Todos os parâmetros analisados estão em conformidade.")
        st.balloons()
    else:
        st.error(f"⚠️ **PARECER: REPROVADO.** Foram encontradas {num_nao_conformes} não conformidades.")
    
    with st.expander("2. Dados Oficiais da Zona"):
        st.json(api_info.get('parametros', {}))
        
    with st.expander("3. Informações Técnicas da Deteção"):
        st.json({
            "Endereço Analisado": resultado['dados_projeto']['endereco'],
            "Coordenadas Encontradas": api_info.get('coordenadas'),
            "Zonas Incidentes no Lote": api_info.get('todas_zonas_incidentes', []),
        })

def criar_formulario_endereco():
    """Cria formulário específico para consulta por endereço."""
    col1, col2 = st.columns([2, 1])

    with col1:
        endereco = st.text_input(
            "📍 Endereço Completo",
            placeholder="Ex: Rua XV de Novembro, 1000, Centro, Curitiba",
            help="Digite o endereço completo incluindo número, rua e bairro"
        )

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Espaçamento
        analisar = st.button("🔍 Consultar Zoneamento", type="primary", use_container_width=True)

    # Formulário de projeto (opcional)
    with st.expander("🏗️ Dados do Projeto (Opcional)", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            area_terreno = st.number_input("Área do Terreno (m²)", min_value=0.0, value=0.0)
            area_projecao = st.number_input("Área de Projeção (m²)", min_value=0.0, value=0.0)
        with col2:
            area_computavel = st.number_input("Área Computável (m²)", min_value=0.0, value=0.0)
            area_permeavel = st.number_input("Área Permeável (m²)", min_value=0.0, value=0.0)

        num_pavimentos = st.number_input("Número de Pavimentos", min_value=0, value=0)
        recuo_frontal = st.number_input("Recuo Frontal (m)", min_value=0.0, value=0.0)

    return {
        'endereco': endereco.strip() if endereco else '',
        'area_terreno': area_terreno,
        'area_projecao': area_projecao,
        'area_computavel': area_computavel,
        'area_permeavel': area_permeavel,
        'num_pavimentos': num_pavimentos,
        'recuo_frontal': recuo_frontal,
        'analisar': analisar and bool(endereco.strip())
    }

def criar_formulario_coordenadas():
    """Cria formulário específico para consulta por coordenadas."""
    st.info("💡 **Dica:** Use coordenadas no formato decimal (ex: -25.4284, -49.2733)")

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        latitude = st.number_input(
            "🌐 Latitude",
            value=-25.4284,
            format="%.6f",
            help="Latitude em graus decimais (negativo para Sul)"
        )

    with col2:
        longitude = st.number_input(
            "🌐 Longitude",
            value=-49.2733,
            format="%.6f",
            help="Longitude em graus decimais (negativo para Oeste)"
        )

    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        analisar = st.button("🔍 Consultar por Coordenadas", type="primary", use_container_width=True)

    # Validação básica de coordenadas para Curitiba
    coords_validas = (-26.0 <= latitude <= -25.0) and (-50.0 <= longitude <= -49.0)

    if not coords_validas and (latitude != -25.4284 or longitude != -49.2733):
        st.warning("⚠️ Coordenadas fora da região de Curitiba. Verifique os valores inseridos.")

    # Formulário de projeto (opcional)
    with st.expander("🏗️ Dados do Projeto (Opcional)", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            area_terreno = st.number_input("Área do Terreno (m²)", min_value=0.0, value=0.0, key="coord_area_terreno")
            area_projecao = st.number_input("Área de Projeção (m²)", min_value=0.0, value=0.0, key="coord_area_projecao")
        with col2:
            area_computavel = st.number_input("Área Computável (m²)", min_value=0.0, value=0.0, key="coord_area_computavel")
            area_permeavel = st.number_input("Área Permeável (m²)", min_value=0.0, value=0.0, key="coord_area_permeavel")

        num_pavimentos = st.number_input("Número de Pavimentos", min_value=0, value=0, key="coord_num_pavimentos")
        recuo_frontal = st.number_input("Recuo Frontal (m)", min_value=0.0, value=0.0, key="coord_recuo_frontal")

    return {
        'latitude': latitude,
        'longitude': longitude,
        'area_terreno': area_terreno,
        'area_projecao': area_projecao,
        'area_computavel': area_computavel,
        'area_permeavel': area_permeavel,
        'num_pavimentos': num_pavimentos,
        'recuo_frontal': recuo_frontal,
        'analisar': analisar and coords_validas
    }

def salvar_no_historico(result, tipo, endereco=None, coordenadas=None):
    """Salva consulta no histórico."""
    if 'historico_consultas' not in st.session_state:
        st.session_state.historico_consultas = []

    api_data = result.get('dados_api', {})
    consulta = {
        'timestamp': datetime.now().strftime("%d/%m/%Y %H:%M"),
        'tipo': tipo,
        'zona_principal': api_data.get('zona_principal', 'N/A'),
        'fonte': api_data.get('fonte', 'N/A'),
        'coordenadas_encontradas': api_data.get('coordenadas', 'N/A')
    }

    if endereco:
        consulta['endereco'] = endereco
    if coordenadas:
        consulta['coordenadas'] = coordenadas

    st.session_state.historico_consultas.append(consulta)

    # Manter apenas as últimas 50 consultas
    if len(st.session_state.historico_consultas) > 50:
        st.session_state.historico_consultas = st.session_state.historico_consultas[-50:]

def exibir_historico():
    """Exibe histórico de consultas."""
    if 'historico_consultas' not in st.session_state:
        st.session_state.historico_consultas = []

    if not st.session_state.historico_consultas:
        st.info("📝 Nenhuma consulta realizada ainda. Faça sua primeira consulta nas abas anteriores!")
        return

    st.subheader("🕐 Últimas Consultas")

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🗑️ Limpar Histórico"):
            st.session_state.historico_consultas = []
            st.rerun()

    for i, consulta in enumerate(reversed(st.session_state.historico_consultas[-10:])):  # Últimas 10
        with st.expander(f"Consulta {len(st.session_state.historico_consultas) - i}: {consulta.get('endereco', consulta.get('coordenadas', 'N/A'))}"):
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Tipo:**", "📍 Endereço" if consulta.get('tipo') == 'endereco' else "🗺️ Coordenadas")
                st.write("**Zona Principal:**", consulta.get('zona_principal', 'N/A'))
                st.write("**Fonte:**", consulta.get('fonte', 'N/A'))
            with col2:
                st.write("**Data:**", consulta.get('timestamp', 'N/A'))
                st.write("**Coordenadas:**", consulta.get('coordenadas_encontradas', 'N/A'))

def main():
    configurar_pagina()
    if 'analysis_result' not in st.session_state: st.session_state.analysis_result = None

    # Interface principal com abas
    st.title("🏗️ Assistente de Regulamentação Civil")
    st.markdown("**Sistema de consulta de zoneamento urbano de Curitiba**")

    # Criar abas
    tab1, tab2, tab3 = st.tabs(["📍 Consulta por Endereço", "🗺️ Consulta por Coordenadas", "📊 Histórico"])

    with tab1:
        st.header("📍 Consulta por Endereço")
        form_data = criar_formulario_endereco()

        if form_data['analisar']:
            try:
                engine = AnalysisEngine()
                st.session_state.analysis_result = engine.run_analysis(form_data)

                # Salvar no histórico
                if st.session_state.analysis_result and st.session_state.analysis_result.get('sucesso'):
                    salvar_no_historico(st.session_state.analysis_result, tipo="endereco", endereco=form_data['endereco'])

            except (ValueError, ConnectionError) as e:
                st.error(f"❌ Erro na Análise: {e}")
                st.session_state.analysis_result = None
            except Exception:
                st.error("Ocorreu um erro inesperado. Verifique os logs.")
                logger.error("Erro inesperado na análise", exc_info=True)
                st.session_state.analysis_result = None

    with tab2:
        st.header("🗺️ Consulta por Coordenadas")
        coord_data = criar_formulario_coordenadas()

        if coord_data['analisar']:
            try:
                engine = AnalysisEngine()
                st.session_state.analysis_result = engine.run_analysis_by_coordinates(coord_data)

                # Salvar no histórico
                if st.session_state.analysis_result and st.session_state.analysis_result.get('sucesso'):
                    coordenadas_str = f"{coord_data['latitude']:.6f}, {coord_data['longitude']:.6f}"
                    salvar_no_historico(st.session_state.analysis_result, tipo="coordenadas", coordenadas=coordenadas_str)

            except (ValueError, ConnectionError) as e:
                st.error(f"❌ Erro na Análise: {e}")
                st.session_state.analysis_result = None
            except Exception:
                st.error("Ocorreu um erro inesperado. Verifique os logs.")
                logger.error("Erro inesperado na análise", exc_info=True)
                st.session_state.analysis_result = None

    with tab3:
        st.header("📊 Histórico de Consultas")
        exibir_historico()

    # Exibir resultados se houver
    if st.session_state.analysis_result and st.session_state.analysis_result.get('sucesso'):
        st.markdown("---")
        exibir_resultados(st.session_state.analysis_result)
        if st.button("🔄 Nova Consulta"):
            st.session_state.analysis_result = None
            st.rerun()

if __name__ == "__main__":
    main()

