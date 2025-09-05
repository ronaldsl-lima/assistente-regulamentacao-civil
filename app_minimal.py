import streamlit as st
import pandas as pd
from parametros_oficiais_curitiba import ParametrosOficiaisCuritiba
from dashboard_simple import mostrar_dashboard_simples

st.set_page_config(
    page_title="Assistente de Regulamentação Civil - Curitiba",
    page_icon="🏗️",
    layout="wide"
)

st.title("🏗️ Assistente de Regulamentação Civil - Versão Teste")

# Teste simples da validação
if st.button("Testar Sistema de Validação SEHIS"):
    parametros_projeto = {
        'area_permeavel': 20.0,     # 20% - deveria reprovar (mínimo 25%)
        'recuo_frontal': 5.0,       # 5m - deveria aprovar (mínimo 3m)
        'taxa_ocupacao': 70.0       # 70% - deveria aprovar (máximo 70%)
    }
    
    parametros_zona = {}
    
    st.success("Sistema funcionando! Validando parâmetros SEHIS:")
    mostrar_dashboard_simples(parametros_projeto, parametros_zona, "SEHIS")

st.info("✅ Sistema de validação oficial implementado com sucesso!")
st.markdown("**Correções aplicadas:**")
st.markdown("- Taxa permeável: Agora mostra corretamente 'MÍNIMO 25%'") 
st.markdown("- Recuo frontal SEHIS: Validação corrigida (mínimo 3m)")
st.markdown("- Sistema oficial baseado na Lei 15.511/2019")