#!/usr/bin/env python3
"""
Dashboard Simplificado para Análise Urbanística
Versão sem plotly para máxima compatibilidade
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, List
from parametros_oficiais_curitiba import ParametrosOficiaisCuritiba

class SimpleDashboard:
    """Dashboard simplificado para análise urbanística"""
    
    def __init__(self):
        self.cores = {
            'conforme': '#28a745',      # Verde
            'atencao': '#ffc107',       # Amarelo  
            'nao_conforme': '#dc3545',  # Vermelho
            'neutro': '#6c757d'         # Cinza
        }
        # Sistema oficial de parâmetros
        self.parametros_oficiais = ParametrosOficiaisCuritiba()
    
    def _analisar_parametros_oficiais(self, parametros_projeto: Dict, zona: str) -> Dict:
        """Analisa parâmetros usando o sistema oficial de Curitiba"""
        
        # Mapear parâmetros do projeto para formato esperado
        projeto_mapeado = {
            'taxa_ocupacao': parametros_projeto.get('taxa_ocupacao', 0),
            'coeficiente_aproveitamento': parametros_projeto.get('coeficiente_aproveitamento', 0),
            'altura_edificacao': parametros_projeto.get('altura_edificacao', 0),
            'recuo_frontal': parametros_projeto.get('recuo_frontal', 0),
            'recuos_laterais': parametros_projeto.get('recuos_laterais', 0),
            'recuo_fundos': parametros_projeto.get('recuo_fundos', 0),
            'taxa_permeabilidade': parametros_projeto.get('area_permeavel', 0),
        }
        
        # Filtrar apenas valores válidos (> 0)
        projeto_filtrado = {k: v for k, v in projeto_mapeado.items() if v and float(v) > 0}
        
        # Gerar análise oficial
        resultado = self.parametros_oficiais.gerar_tabela_comparativa(zona, projeto_filtrado)
        
        # Converter para formato compatível com dashboard
        analises = {}
        if resultado.get('zona_valida'):
            for param_nome, validacao in resultado.get('parametros', {}).items():
                # Mapear nomes de volta
                nome_dashboard = {
                    'taxa_ocupacao': 'Taxa de Ocupação',
                    'coeficiente_aproveitamento': 'Coef. Aproveitamento', 
                    'altura_edificacao': 'Altura',
                    'recuo_frontal': 'Recuo Frontal',
                    'recuos_laterais': 'Recuos Laterais',
                    'recuo_fundos': 'Recuo Fundos',
                    'taxa_permeabilidade': 'Área Permeável'
                }.get(param_nome, param_nome)
                
                # Determinar status visual
                conforme = validacao.get('conforme', False)
                if conforme:
                    status = 'Conforme' 
                    cor = self.cores['conforme']
                    emoji = '✅'
                else:
                    status = 'Não Conforme'
                    cor = self.cores['nao_conforme']
                    emoji = '❌'
                
                analises[nome_dashboard] = {
                    'status': status,
                    'valor_projeto': f"{validacao.get('valor_projeto', 0)}{validacao.get('unidade', '')}",
                    'valor_limite': f"{validacao.get('limite_legal', 0)}{validacao.get('unidade', '')}",
                    'valor_projeto_num': float(validacao.get('valor_projeto', 0)),
                    'valor_limite_num': float(validacao.get('limite_legal', 0)),
                    'unidade': validacao.get('unidade', ''),
                    'tipo_limite': validacao.get('tipo_limite', ''),
                    'observacao': validacao.get('observacao', ''),
                    'detalhes': validacao.get('detalhes', ''),
                    'cor': cor,
                    'emoji': emoji
                }
        
        return analises
    
    def criar_tabela_resumo(self, parametros_projeto: Dict, parametros_zona: Dict, zona: str) -> None:
        """Cria tabela resumo da conformidade"""
        
        st.subheader("📋 Análise de Conformidade - Sistema Oficial")
        
        analises = self._analisar_parametros_oficiais(parametros_projeto, zona)
        
        if not analises:
            st.info("ℹ️ Nenhum parâmetro válido para análise")
            return
        
        # Criar dataframe para exibição
        dados_tabela = []
        
        for param, dados in analises.items():
            dados_tabela.append({
                'Parâmetro': param,
                'Status': f"{dados['emoji']} {dados['status']}", 
                'Projeto': dados['valor_projeto'],
                'Limite Legal': f"{dados['valor_limite']} ({dados['tipo_limite']})",
                'Observação': dados['observacao']
            })
        
        df = pd.DataFrame(dados_tabela)
        
        # Contar conformidade
        total = len(analises)
        conformes = sum(1 for dados in analises.values() if dados['status'] == 'Conforme')
        nao_conformes = total - conformes
        
        # Status geral
        if nao_conformes == 0:
            st.success(f"✅ **PROJETO CONFORME** - Todos os {total} parâmetros atendem à legislação")
        else:
            st.error(f"❌ **PROJETO NÃO CONFORME** - {nao_conformes} de {total} parâmetros não atendem à legislação")
        
        # Mostrar tabela
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Detalhes expandidos
        with st.expander("🔍 Ver Detalhes de Cada Parâmetro"):
            for param, dados in analises.items():
                color = "#28a745" if dados['status'] == 'Conforme' else "#dc3545"
                st.markdown(f"""
                <div style="border-left: 4px solid {color}; padding: 10px; margin: 5px 0; background-color: #f8f9fa;">
                    <strong>{param}</strong><br/>
                    <strong>Status:</strong> {dados['emoji']} {dados['status']}<br/>
                    <strong>Valor do Projeto:</strong> {dados['valor_projeto']}<br/>
                    <strong>Limite Legal:</strong> {dados['valor_limite']} ({dados['tipo_limite']})<br/>
                    <strong>Observação:</strong> {dados['observacao']}<br/>
                    <em>{dados['detalhes']}</em>
                </div>
                """, unsafe_allow_html=True)

def mostrar_dashboard_simples(parametros_projeto: Dict, parametros_zona: Dict, zona: str):
    """Função principal para mostrar dashboard simplificado"""
    
    dashboard = SimpleDashboard()
    dashboard.criar_tabela_resumo(parametros_projeto, parametros_zona, zona)

if __name__ == "__main__":
    # Teste do dashboard simplificado
    st.title("🏗️ Dashboard de Análise Urbanística - Versão Simplificada")
    
    parametros_projeto_teste = {
        'area_permeavel': 20.0,
        'recuo_frontal': 5.0,
        'taxa_ocupacao': 70.0
    }
    
    parametros_zona_teste = {}  # Não usado na versão oficial
    
    mostrar_dashboard_simples(parametros_projeto_teste, parametros_zona_teste, "SEHIS")