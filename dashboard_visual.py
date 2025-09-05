#!/usr/bin/env python3
"""
Dashboard Visual para Análise Urbanística
Gráficos comparativos, semáforos e visualizações interativas
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, List
import numpy as np
from parametros_oficiais_curitiba import ParametrosOficiaisCuritiba

# Importação condicional do plotly com fallback
try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    st.warning("⚠️ Plotly não disponível. Gráficos desabilitados temporariamente.")

class VisualDashboard:
    """Dashboard visual para análise urbanística"""
    
    def __init__(self):
        self.cores = {
            'conforme': '#28a745',      # Verde
            'atencao': '#ffc107',       # Amarelo  
            'nao_conforme': '#dc3545',  # Vermelho
            'neutro': '#6c757d'         # Cinza
        }
        # Sistema oficial de parâmetros
        self.parametros_oficiais = ParametrosOficiaisCuritiba()
    
    def criar_semaforo_conformidade(self, parametros_projeto: Dict, parametros_zona: Dict, zona: str) -> None:
        """Cria visualização semáforo da conformidade"""
        
        st.subheader("🚦 Análise de Conformidade")
        
        # Extrair valores numéricos dos parâmetros
        analises = self._analisar_parametros_oficiais(parametros_projeto, zona)
        
        # Criar colunas para o semáforo
        cols = st.columns(len(analises))
        
        for i, (parametro, dados) in enumerate(analises.items()):
            with cols[i]:
                cor = dados['cor']
                status = dados['status']
                valor_projeto = dados['valor_projeto']
                valor_limite = dados['valor_limite']
                
                # Criar card visual
                st.markdown(f"""
                <div style="
                    background-color: {cor}20;
                    border-left: 5px solid {cor};
                    padding: 15px;
                    border-radius: 5px;
                    margin: 5px 0;
                ">
                    <h4 style="color: {cor}; margin: 0;">{parametro}</h4>
                    <p style="margin: 5px 0;"><strong>Projeto:</strong> {valor_projeto}</p>
                    <p style="margin: 5px 0;"><strong>Limite:</strong> {valor_limite}</p>
                    <p style="margin: 5px 0; color: {cor};"><strong>{status}</strong></p>
                </div>
                """, unsafe_allow_html=True)
    
    def criar_grafico_barras_comparativo(self, parametros_projeto: Dict, parametros_zona: Dict, zona: str) -> None:
        """Cria gráfico de barras comparativo"""
        
        st.subheader("📊 Comparativo: Projeto vs Permitido")
        
        # Processar dados para o gráfico
        dados = []
        analises = self._analisar_parametros_oficiais(parametros_projeto, zona)
        
        for parametro, info in analises.items():
            if isinstance(info['valor_projeto_num'], (int, float)) and isinstance(info['valor_limite_num'], (int, float)):
                dados.append({
                    'Parâmetro': parametro,
                    'Projeto': info['valor_projeto_num'],
                    'Permitido': info['valor_limite_num'],
                    'Status': info['status']
                })
        
        if dados:
            df = pd.DataFrame(dados)
            
            # Criar gráfico
            fig = go.Figure()
            
            # Barras do projeto
            fig.add_trace(go.Bar(
                name='Seu Projeto',
                x=df['Parâmetro'],
                y=df['Projeto'],
                marker_color='lightblue',
                text=df['Projeto'],
                textposition='auto',
            ))
            
            # Barras do permitido
            fig.add_trace(go.Bar(
                name='Limite Permitido',
                x=df['Parâmetro'],
                y=df['Permitido'],
                marker_color='darkblue',
                text=df['Permitido'],
                textposition='auto',
            ))
            
            fig.update_layout(
                title="Comparação: Projeto vs Limites da Zona",
                xaxis_title="Parâmetros Urbanísticos",
                yaxis_title="Valores",
                barmode='group',
                height=500
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    def criar_gauge_aproveitamento(self, parametros_projeto: Dict, parametros_zona: Dict, zona: str) -> None:
        """Cria gráficos gauge de aproveitamento"""
        
        st.subheader("🎯 Aproveitamento do Potencial Construtivo")
        
        # Criar gauges para parâmetros principais
        analises = self._analisar_parametros_oficiais(parametros_projeto, zona)
        
        # Filtrar parâmetros para gauge
        parametros_gauge = ['Taxa de Ocupação', 'Coef. Aproveitamento', 'Altura']
        
        cols = st.columns(len(parametros_gauge))
        
        for i, param in enumerate(parametros_gauge):
            if param in analises:
                with cols[i]:
                    info = analises[param]
                    if isinstance(info['valor_projeto_num'], (int, float)) and isinstance(info['valor_limite_num'], (int, float)):
                        
                        # Calcular percentual de aproveitamento
                        percentual = min((info['valor_projeto_num'] / info['valor_limite_num']) * 100, 150)
                        
                        # Definir cor baseada no percentual
                        if percentual <= 80:
                            cor_gauge = 'green'
                        elif percentual <= 100:
                            cor_gauge = 'yellow'
                        else:
                            cor_gauge = 'red'
                        
                        # Criar gauge
                        fig = go.Figure(go.Indicator(
                            mode = "gauge+number+delta",
                            value = percentual,
                            domain = {'x': [0, 1], 'y': [0, 1]},
                            title = {'text': param},
                            delta = {'reference': 100},
                            gauge = {
                                'axis': {'range': [None, 150]},
                                'bar': {'color': cor_gauge},
                                'steps': [
                                    {'range': [0, 80], 'color': "lightgray"},
                                    {'range': [80, 100], 'color': "yellow"},
                                    {'range': [100, 150], 'color': "red"}
                                ],
                                'threshold': {
                                    'line': {'color': "red", 'width': 4},
                                    'thickness': 0.75,
                                    'value': 100
                                }
                            }
                        ))
                        
                        fig.update_layout(height=250)
                        st.plotly_chart(fig, use_container_width=True)
    
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
                else:
                    status = 'Não Conforme'
                    cor = self.cores['nao_conforme']
                
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
                    'cor': cor
                }
        
        return analises
    
    def criar_resumo_executivo(self, parametros_projeto: Dict, parametros_zona: Dict, zona: str) -> None:
        """Cria resumo executivo visual"""
        
        st.subheader("📋 Resumo Executivo")
        
        analises = self._analisar_parametros_oficiais(parametros_projeto, zona)
        
        # Contar status
        conformes = sum(1 for a in analises.values() if a['status'] == 'CONFORME')
        nao_conformes = sum(1 for a in analises.values() if a['status'] == 'NÃO CONFORME')
        atencao = sum(1 for a in analises.values() if a['status'] == 'ATENÇÃO')
        
        total = len(analises)
        
        # Criar layout de resumo
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Zona Analisada",
                zona,
                help="Zona de zoneamento urbano"
            )
        
        with col2:
            st.metric(
                "Parâmetros Conformes", 
                f"{conformes}/{total}",
                help="Parâmetros que atendem aos limites"
            )
        
        with col3:
            st.metric(
                "Não Conformes",
                nao_conformes,
                delta=f"-{nao_conformes}" if nao_conformes > 0 else "0",
                delta_color="inverse",
                help="Parâmetros que excedem os limites"
            )
        
        with col4:
            # Percentual de conformidade
            perc_conforme = (conformes / total * 100) if total > 0 else 0
            st.metric(
                "Conformidade",
                f"{perc_conforme:.0f}%",
                help="Percentual geral de conformidade"
            )
        
        # Status geral
        if nao_conformes == 0:
            st.success("✅ **PROJETO CONFORME** - Todos os parâmetros atendem aos limites da zona")
        elif nao_conformes <= 2:
            st.warning(f"⚠️ **PROJETO COM RESTRIÇÕES** - {nao_conformes} parâmetro(s) fora dos limites")
        else:
            st.error(f"❌ **PROJETO NÃO CONFORME** - {nao_conformes} parâmetros excedem os limites")
    
    def _analisar_parametros(self, parametros_projeto: Dict, parametros_zona: Dict) -> Dict:
        """Analisa parâmetros e retorna status de conformidade"""
        
        analises = {}
        
        # Mapear parâmetros com seus limites
        mapeamentos = {
            'Taxa de Ocupação': {
                'projeto': parametros_projeto.get('taxa_ocupacao', 0),
                'limite': self._extrair_numero(parametros_zona.get('taxa_ocupacao', '0%')),
                'unidade': '%',
                'tipo': 'maximo'
            },
            'Coef. Aproveitamento': {
                'projeto': parametros_projeto.get('coeficiente_aproveitamento', 0),
                'limite': self._extrair_numero(parametros_zona.get('coeficiente_aproveitamento', '0')),
                'unidade': '',
                'tipo': 'maximo'
            },
            'Altura': {
                'projeto': parametros_projeto.get('altura_edificacao', 0),
                'limite': self._extrair_numero(parametros_zona.get('altura_maxima', '0')),
                'unidade': 'm',
                'tipo': 'maximo'
            },
            'Área Permeável': {
                'projeto': parametros_projeto.get('area_permeavel', 0),
                'limite': self._extrair_numero(parametros_zona.get('area_permeavel', '0%')),
                'unidade': '%',
                'tipo': 'minimo'
            }
        }
        
        for param, dados in mapeamentos.items():
            projeto_val = float(dados['projeto']) if dados['projeto'] else 0
            limite_val = float(dados['limite']) if dados['limite'] else 0
            
            if limite_val == 0:
                continue
                
            # Determinar status
            if dados['tipo'] == 'maximo':
                if projeto_val <= limite_val * 0.8:
                    status = 'CONFORME'
                    cor = self.cores['conforme']
                elif projeto_val <= limite_val:
                    status = 'ATENÇÃO'
                    cor = self.cores['atencao']
                else:
                    status = 'NÃO CONFORME'
                    cor = self.cores['nao_conforme']
            else:  # mínimo
                if projeto_val >= limite_val:
                    status = 'CONFORME'
                    cor = self.cores['conforme']
                elif projeto_val >= limite_val * 0.8:
                    status = 'ATENÇÃO'
                    cor = self.cores['atencao']
                else:
                    status = 'NÃO CONFORME'
                    cor = self.cores['nao_conforme']
            
            analises[param] = {
                'valor_projeto': f"{projeto_val}{dados['unidade']}",
                'valor_limite': f"{limite_val}{dados['unidade']}",
                'valor_projeto_num': projeto_val,
                'valor_limite_num': limite_val,
                'status': status,
                'cor': cor
            }
        
        return analises
    
    def _extrair_numero(self, texto: str) -> float:
        """Extrai número de string com unidades"""
        if not texto:
            return 0.0
            
        import re
        # Procurar por números (incluindo decimais)
        match = re.search(r'(\d+(?:[.,]\d+)?)', str(texto).replace(',', '.'))
        if match:
            return float(match.group(1))
        return 0.0

# Função principal para integração
def mostrar_dashboard_visual(parametros_projeto: Dict, parametros_zona: Dict, zona: str):
    """Função principal para mostrar dashboard visual"""
    
    dashboard = VisualDashboard()
    
    # Mostrar todos os componentes
    dashboard.criar_resumo_executivo(parametros_projeto, parametros_zona, zona)
    dashboard.criar_semaforo_conformidade(parametros_projeto, parametros_zona, zona)
    dashboard.criar_gauge_aproveitamento(parametros_projeto, parametros_zona, zona)
    dashboard.criar_grafico_barras_comparativo(parametros_projeto, parametros_zona, zona)

if __name__ == "__main__":
    # Teste do dashboard
    st.title("🏗️ Dashboard de Análise Urbanística")
    
    # Dados de exemplo
    parametros_projeto_teste = {
        'taxa_ocupacao': 75,
        'coeficiente_aproveitamento': 2.5,
        'altura_edificacao': 15,
        'area_permeavel': 12
    }
    
    parametros_zona_teste = {
        'taxa_ocupacao': '70%',
        'coeficiente_aproveitamento': '2,0',
        'altura_maxima': '12 metros',
        'area_permeavel': '15%'
    }
    
    mostrar_dashboard_visual(parametros_projeto_teste, parametros_zona_teste, "ZR2")