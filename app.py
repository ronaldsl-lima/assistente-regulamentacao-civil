import streamlit as st
import pandas as pd
from datetime import datetime
import logging
import re
import math

# SOLUÇÃO DEFINITIVA: Importa a função que consulta a API do GeoCuritiba
# from geocuritiba_layer36_solution import buscar_zoneamento_definitivo

# NOVA SOLUÇÃO COM SELENIUM: Automação real do navegador
from geocuritiba_selenium_simples import buscar_zoneamento_selenium as buscar_zoneamento_definitivo

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
    st.set_page_config(page_title="Assistente Regulatório v8.2", page_icon="🏗️", layout="wide")

def criar_formulario_completo(dados_existentes=None):
    if dados_existentes is None: dados_existentes = {}
    
    st.sidebar.title("🏗️ Assistente Regulatório")
    st.sidebar.header("1. Identificação do Imóvel")

    endereco = st.sidebar.text_input("Endereço Completo: *", value=dados_existentes.get('endereco', ''), help="Obrigatório. A precisão da análise depende de um endereço completo e correto (Rua, Número, Bairro, Cidade).")
    indicacao_fiscal = st.sidebar.text_input("Indicação Fiscal (opcional):", value=dados_existentes.get('indicacao_fiscal', ''), help="Se souber, ajuda a confirmar a localização, mas o endereço é o principal.")

    with st.sidebar.expander("2. Dimensionais do Projeto", expanded=True):
        st.info("Aqui você coloca as medidas principais do seu projeto.")
        area_terreno = st.number_input("Área Total do Terreno (m²): *", min_value=0.1, value=dados_existentes.get('area_terreno', 200.0), format="%.2f", help="A área total do seu terreno, conforme a matrícula do imóvel.")
        area_projecao = st.number_input("Área de Projeção/Implantação (m²):", value=dados_existentes.get('area_projecao', 130.0), format="%.2f", help="Imagine uma 'sombra' da sua construção no terreno. Esta é a área que essa sombra ocupa.")
        area_computavel = st.number_input("Área Construída Computável (m²):", value=dados_existentes.get('area_computavel', 175.0), format="%.2f", help="A soma das áreas que contam para o Coeficiente de Aproveitamento.")
        area_nao_computavel = st.number_input("Área Construída Não Computável (m²):", value=dados_existentes.get('area_nao_computavel', 0.0), format="%.2f", help="A soma das áreas que não contam (garagens, sacadas abertas, etc.).")
        area_permeavel = st.number_input("Área Permeável (m²):", value=dados_existentes.get('area_permeavel', 10.0), format="%.2f", help="A parte do terreno sem construção, que permite a absorção da água da chuva.")
        num_pavimentos = st.number_input("Número de Pavimentos:", min_value=1, step=1, value=dados_existentes.get('num_pavimentos', 2), help="A quantidade de andares da sua construção.")
        altura_total = st.number_input("Altura Total (metros):", value=dados_existentes.get('altura_total', 7.0), format="%.2f", help="A altura total da sua construção, do nível médio do terreno ao ponto mais alto.")

    with st.sidebar.expander("3. Afastamentos e Recuos (m)"):
        st.info("Distâncias mínimas da sua construção até as divisas do terreno.")
        lote_esquina = st.checkbox("Lote de Esquina", value=dados_existentes.get('lote_esquina', False), help="O seu terreno fica na esquina de duas ruas?")
        recuo_frontal = st.number_input("Recuo Frontal:", value=dados_existentes.get('recuo_frontal', 5.0), format="%.2f", help="Distância da construção até a calçada.")
        afastamento_ld = st.number_input("Afastamento Lateral Direito:", value=dados_existentes.get('afastamento_ld', 1.5), format="%.2f", help="Distância até a divisa lateral direita.")
        afastamento_le = st.number_input("Afastamento Lateral Esquerdo:", value=dados_existentes.get('afastamento_le', 1.5), format="%.2f", help="Distância até a divisa lateral esquerda.")
        afastamento_fundos = st.number_input("Afastamento de Fundos:", value=dados_existentes.get('afastamento_fundos', 3.0), format="%.2f", help="Distância até a divisa dos fundos.")

    with st.sidebar.expander("4. Uso e Atividade"):
        categoria_uso = st.selectbox("Categoria de Uso:", ["Residencial", "Comercial", "Serviços", "Misto", "Industrial", "Institucional"])
        unidades_habitacionais = st.number_input("Nº de Unidades Habitacionais:", min_value=0, step=1, value=dados_existentes.get('unidades_habitacionais', 1))
        unidades_nao_habitacionais = st.number_input("Nº de Unidades Comerciais/Serviços:", min_value=0, step=1, value=dados_existentes.get('unidades_nao_habitacionais', 0))

    with st.sidebar.expander("5. Vagas de Estacionamento"):
        vagas_previstas = st.number_input("Total de Vagas Previstas:", min_value=0, step=1, value=dados_existentes.get('vagas_previstas', 1))
        vagas_pcd = st.number_input("Vagas para PCD:", min_value=0, step=1, value=dados_existentes.get('vagas_pcd', 0), help="A lei exige um mínimo de 2%.")
        vagas_idosos = st.number_input("Vagas para Idosos:", min_value=0, step=1, value=dados_existentes.get('vagas_idosos', 0), help="A lei exige um mínimo de 5%.")

    with st.sidebar.expander("6. Características Especiais do Lote"):
        declividade = st.slider("Declividade (%)", 0, 100, value=dados_existentes.get('declividade', 5), help="A inclinação do terreno pode influenciar nas regras de altura.")

    st.sidebar.markdown("---")
    pode_analisar = bool(endereco and area_terreno)
    analisar = st.sidebar.button("🔍 Analisar Conformidade", type="primary", use_container_width=True, disabled=not pode_analisar)
    if not pode_analisar: st.sidebar.warning("Preencha o Endereço Completo e a Área do Terreno.")

    return {k:v for k,v in locals().items() if k not in ['dados_existentes']}

def exibir_resultados(resultado):
    api_info = resultado['dados_api']
    validacoes = resultado['validacoes']

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

def main():
    configurar_pagina()
    if 'analysis_result' not in st.session_state: st.session_state.analysis_result = None
    
    form_data = criar_formulario_completo(st.session_state.analysis_result['dados_projeto'] if st.session_state.analysis_result else None)

    if form_data['analisar']:
        try:
            engine = AnalysisEngine()
            st.session_state.analysis_result = engine.run_analysis(form_data)
        except (ValueError, ConnectionError) as e:
            st.error(f"❌ Erro na Análise: {e}")
            st.session_state.analysis_result = None
        except Exception:
            st.error("Ocorreu um erro inesperado. Verifique os logs.")
            logger.error("Erro inesperado na análise", exc_info=True)
            st.session_state.analysis_result = None

    if st.session_state.analysis_result and st.session_state.analysis_result.get('sucesso'):
        exibir_resultados(st.session_state.analysis_result)
        if st.button("🔄 Nova Análise"):
            st.session_state.analysis_result = None
            st.rerun()
    else:
        st.title("🏗️ Assistente Regulatório v8.2")
        st.info("📋 Preencha o **Endereço Completo** para iniciar a análise geoespacial.")

if __name__ == "__main__":
    main()

