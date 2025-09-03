#!/usr/bin/env python3
"""
Integração com Mapas de Curitiba
Visualização de zonas e localização de terrenos
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import requests
from typing import Dict, Tuple, Optional
import json
import time

class MapaCuritiba:
    """Sistema de mapas para análise urbanística"""
    
    def __init__(self):
        # Coordenadas do centro de Curitiba
        self.centro_curitiba = (-25.4284, -49.2733)
        
        # Cores por tipo de zona
        self.cores_zonas = {
            'ZR': '#28a745',    # Verde - Residencial
            'ZC': '#dc3545',    # Vermelho - Central
            'ZI': '#6f42c1',    # Roxo - Industrial
            'ZUM': '#fd7e14',   # Laranja - Uso Misto
            'ZS': '#20c997',    # Teal - Serviços
            'ZH': '#0dcaf0',    # Cyan - Habitacional
            'ZCC': '#ffc107',   # Amarelo - Centro Cívico
            'SE': '#6c757d',    # Cinza - Setores Especiais
            'E': '#e83e8c',     # Rosa - Equipamentos
            'default': '#17a2b8'  # Azul - Padrão
        }
    
    def criar_mapa_zona(self, endereco: str, zona: str, parametros_zona: Dict) -> None:
        """Cria mapa mostrando localização e zona"""
        
        st.subheader("🗺️ Localização e Contexto Urbano")
        
        # Tentar geocodificar endereço
        coordenadas = self._geocodificar_endereco(endereco)
        
        if coordenadas:
            lat, lon = coordenadas
        else:
            # Usar centro de Curitiba como fallback
            lat, lon = self.centro_curitiba
            st.info("🔍 Localização aproximada - Centro de Curitiba")
        
        # Criar mapa base
        mapa = folium.Map(
            location=[lat, lon],
            zoom_start=15,
            tiles='OpenStreetMap'
        )
        
        # Adicionar marcador do terreno
        cor_zona = self._obter_cor_zona(zona)
        
        folium.Marker(
            [lat, lon],
            popup=self._criar_popup_terreno(endereco, zona, parametros_zona),
            tooltip=f"📍 {endereco} - {zona}",
            icon=folium.Icon(color='red', icon='home', prefix='fa')
        ).add_to(mapa)
        
        # Adicionar círculo da zona
        folium.Circle(
            [lat, lon],
            radius=500,  # 500m de raio
            popup=f"Zona {zona}",
            color=cor_zona,
            fillColor=cor_zona,
            fillOpacity=0.2,
            weight=2
        ).add_to(mapa)
        
        # Adicionar pontos de interesse próximos
        self._adicionar_pontos_interesse(mapa, lat, lon)
        
        # Adicionar controles
        folium.LayerControl().add_to(mapa)
        
        # Mostrar mapa
        mapa_data = st_folium(mapa, width=700, height=500)
        
        # Mostrar informações da localização
        self._mostrar_info_localizacao(endereco, zona, lat, lon)
    
    def criar_mapa_comparativo_zonas(self, zona_atual: str) -> None:
        """Cria mapa comparativo com outras zonas similares"""
        
        st.subheader("📊 Zonas Similares em Curitiba")
        
        # Criar mapa base
        mapa = folium.Map(
            location=self.centro_curitiba,
            zoom_start=12,
            tiles='OpenStreetMap'
        )
        
        # Adicionar exemplos de zonas similares
        zonas_exemplo = self._obter_zonas_exemplo(zona_atual)
        
        for i, zona_info in enumerate(zonas_exemplo):
            lat = self.centro_curitiba[0] + (i - 2) * 0.02
            lon = self.centro_curitiba[1] + (i - 2) * 0.02
            
            cor = self._obter_cor_zona(zona_info['zona'])
            
            folium.CircleMarker(
                [lat, lon],
                radius=15,
                popup=zona_info['descricao'],
                tooltip=f"Zona {zona_info['zona']}",
                color=cor,
                fillColor=cor,
                fillOpacity=0.6,
                weight=2
            ).add_to(mapa)
        
        # Mostrar mapa
        st_folium(mapa, width=700, height=400)
        
        # Mostrar legenda
        self._mostrar_legenda_zonas()
    
    def _geocodificar_endereco(self, endereco: str) -> Optional[Tuple[float, float]]:
        """Tenta geocodificar endereço usando APIs gratuitas"""
        
        if not endereco or len(endereco.strip()) < 5:
            return None
        
        endereco_completo = f"{endereco}, Curitiba, PR, Brasil"
        
        try:
            # Usar Nominatim (OpenStreetMap)
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': endereco_completo,
                'format': 'json',
                'limit': 1,
                'countrycodes': 'br'
            }
            
            headers = {
                'User-Agent': 'AssistenteRegulamentacao/1.0'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    lat = float(data[0]['lat'])
                    lon = float(data[0]['lon'])
                    
                    # Verificar se está em Curitiba (aproximadamente)
                    if -25.6 < lat < -25.3 and -49.4 < lon < -49.1:
                        return (lat, lon)
            
        except Exception as e:
            st.warning(f"⚠️ Não foi possível localizar endereço: {e}")
        
        return None
    
    def _criar_popup_terreno(self, endereco: str, zona: str, parametros_zona: Dict) -> str:
        """Cria popup informativo para o terreno"""
        
        popup_html = f"""
        <div style="width: 250px;">
            <h4>📍 {endereco}</h4>
            <p><strong>Zona:</strong> {zona}</p>
            <hr>
            <p><strong>Parâmetros Principais:</strong></p>
            <ul>
                <li>Taxa Ocupação: {parametros_zona.get('taxa_ocupacao', 'N/A')}</li>
                <li>Coef. Aproveitamento: {parametros_zona.get('coeficiente_aproveitamento', 'N/A')}</li>
                <li>Altura Máxima: {parametros_zona.get('altura_maxima', 'N/A')}</li>
                <li>Área Permeável: {parametros_zona.get('area_permeavel', 'N/A')}</li>
            </ul>
        </div>
        """
        
        return popup_html
    
    def _adicionar_pontos_interesse(self, mapa: folium.Map, lat: float, lon: float) -> None:
        """Adiciona pontos de interesse próximos"""
        
        # Pontos de interesse fictícios (em produção, usar API real)
        pontos = [
            {
                'nome': 'Escola Municipal',
                'tipo': 'educacao',
                'lat': lat + 0.005,
                'lon': lon + 0.003,
                'icon': 'graduation-cap'
            },
            {
                'nome': 'UBS - Unidade Básica de Saúde',
                'tipo': 'saude',
                'lat': lat - 0.003,
                'lon': lon + 0.004,
                'icon': 'hospital'
            },
            {
                'nome': 'Praça do Bairro',
                'tipo': 'lazer',
                'lat': lat + 0.002,
                'lon': lon - 0.005,
                'icon': 'tree'
            },
            {
                'nome': 'Terminal de Ônibus',
                'tipo': 'transporte',
                'lat': lat - 0.006,
                'lon': lon - 0.002,
                'icon': 'bus'
            }
        ]
        
        cores_poi = {
            'educacao': 'blue',
            'saude': 'green',
            'lazer': 'orange',
            'transporte': 'purple'
        }
        
        for poi in pontos:
            folium.Marker(
                [poi['lat'], poi['lon']],
                popup=poi['nome'],
                tooltip=poi['nome'],
                icon=folium.Icon(
                    color=cores_poi.get(poi['tipo'], 'gray'),
                    icon=poi['icon'],
                    prefix='fa'
                )
            ).add_to(mapa)
    
    def _obter_cor_zona(self, zona: str) -> str:
        """Retorna cor baseada no tipo de zona"""
        
        for prefixo, cor in self.cores_zonas.items():
            if zona.startswith(prefixo):
                return cor
        
        return self.cores_zonas['default']
    
    def _obter_zonas_exemplo(self, zona_atual: str) -> list:
        """Retorna zonas similares para comparação"""
        
        exemplos_base = {
            'ZR': [
                {'zona': 'ZR-1', 'descricao': 'Zona Residencial de baixa densidade'},
                {'zona': 'ZR-2', 'descricao': 'Zona Residencial padrão'},
                {'zona': 'ZR-3', 'descricao': 'Zona Residencial de média densidade'},
            ],
            'ZC': [
                {'zona': 'ZC', 'descricao': 'Zona Central principal'},
                {'zona': 'ZCC', 'descricao': 'Centro Cívico'},
            ],
            'ZUM': [
                {'zona': 'ZUM-1', 'descricao': 'Uso Misto densidade média'},
                {'zona': 'ZUM-2', 'descricao': 'Uso Misto alta densidade'},
            ]
        }
        
        # Encontrar tipo da zona atual
        for prefixo, zonas in exemplos_base.items():
            if zona_atual.startswith(prefixo):
                return zonas
        
        # Retorno padrão
        return exemplos_base['ZR']
    
    def _mostrar_info_localizacao(self, endereco: str, zona: str, lat: float, lon: float) -> None:
        """Mostra informações detalhadas da localização"""
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.info(f"""
            **📍 Localização**
            - Endereço: {endereco}
            - Coordenadas: {lat:.4f}, {lon:.4f}
            - Zona: {zona}
            """)
        
        with col2:
            st.info(f"""
            **🏙️ Contexto Urbano**
            - Região: Central
            - Densidade: Média
            - Transporte: Terminal próximo
            """)
        
        with col3:
            st.info(f"""
            **🎯 Equipamentos Próximos**
            - Educação: Escola (500m)
            - Saúde: UBS (400m)  
            - Lazer: Praça (300m)
            """)
    
    def _mostrar_legenda_zonas(self) -> None:
        """Mostra legenda das cores das zonas"""
        
        st.subheader("🎨 Legenda das Zonas")
        
        col1, col2, col3 = st.columns(3)
        
        legenda_items = [
            ("ZR - Residencial", self.cores_zonas['ZR']),
            ("ZC - Central", self.cores_zonas['ZC']),
            ("ZI - Industrial", self.cores_zonas['ZI']),
            ("ZUM - Uso Misto", self.cores_zonas['ZUM']),
            ("ZS - Serviços", self.cores_zonas['ZS']),
            ("ZH - Habitacional", self.cores_zonas['ZH']),
            ("ZCC - Centro Cívico", self.cores_zonas['ZCC']),
            ("SE - Setores Especiais", self.cores_zonas['SE']),
            ("E - Equipamentos", self.cores_zonas['E'])
        ]
        
        for i, (nome, cor) in enumerate(legenda_items):
            col_idx = i % 3
            with [col1, col2, col3][col_idx]:
                st.markdown(f"""
                <div style="display: flex; align-items: center; margin: 5px 0;">
                    <div style="
                        width: 20px; 
                        height: 20px; 
                        background-color: {cor}; 
                        border-radius: 50%;
                        margin-right: 10px;
                    "></div>
                    <span>{nome}</span>
                </div>
                """, unsafe_allow_html=True)

# Função principal para integração
def mostrar_mapa_curitiba(endereco: str, zona: str, parametros_zona: Dict):
    """Função principal para mostrar mapas"""
    
    mapa = MapaCuritiba()
    
    # Mostrar mapa principal
    mapa.criar_mapa_zona(endereco, zona, parametros_zona)
    
    # Mostrar mapa comparativo
    with st.expander("🔍 Ver Zonas Similares"):
        mapa.criar_mapa_comparativo_zonas(zona)