#!/usr/bin/env python3
"""
Sistema de Busca Inteligente por Endereço
Integração com APIs e validação de endereços
"""

import streamlit as st
import requests
import re
from typing import Dict, List, Optional, Tuple
import json
from dataclasses import dataclass
import time

@dataclass
class EnderecoInfo:
    """Classe para informações de endereço"""
    endereco_completo: str
    cep: str = ""
    logradouro: str = ""
    numero: str = ""
    bairro: str = ""
    cidade: str = ""
    estado: str = ""
    coordenadas: Tuple[float, float] = None
    zona_estimada: str = ""
    confiabilidade: str = ""

class BuscaEndereco:
    """Sistema inteligente de busca por endereço"""
    
    def __init__(self):
        self.cache_enderecos = {}
        
        # Mapeamento de bairros para zonas (dados reais de Curitiba)
        self.bairros_zonas = {
            # Centro e região central
            "centro": "ZC",
            "centro cívico": "ZCC",
            "rebouças": "ZUM-1",
            "água verde": "ZUM-2",
            "batel": "ZUM-1",
            
            # Zonas residenciais
            "cidade industrial": "ZI",
            "cajuru": "ZR-3",
            "portão": "ZR-2",
            "santa quitéria": "ZR-1",
            "santo inácio": "ZR-2",
            "são francisco": "ZR-2",
            "jardim botânico": "ZR-3",
            "bigorrilho": "ZR-3",
            "mercês": "ZR-2",
            "juvevê": "ZR-3",
            "cabral": "ZR-2",
            "hugo lange": "ZR-2",
            "bacacheri": "ZR-2",
            "boa vista": "ZR-2",
            "alto da rua xv": "ZUM-1",
            
            # Bairros específicos
            "linha verde": "ZR-4",  # Importante!
            "campo de santana": "ZR-1",
            "tarumã": "ZR-1",
            "orleans": "ZR-2",
            "pinheirinho": "ZR-2",
            
            # Zonas industriais
            "distrito industrial": "ZI",
            "fazendinha": "ZI",
            
            # Outras zonas
            "alto da glória": "ZS-1",
            "cristo rei": "ZR-3",
            "pilarzinho": "ZR-2"
        }
    
    def buscar_endereco_inteligente(self, entrada_usuario: str) -> EnderecoInfo:
        """Busca inteligente que combina múltiplas estratégias"""
        
        entrada_limpa = entrada_usuario.strip().lower()
        
        # Verificar cache primeiro
        if entrada_limpa in self.cache_enderecos:
            return self.cache_enderecos[entrada_limpa]
        
        resultado = None
        
        # Estratégia 1: CEP direto
        if self._eh_cep(entrada_limpa):
            resultado = self._buscar_por_cep(entrada_limpa)
        
        # Estratégia 2: Endereço completo com APIs
        if not resultado:
            resultado = self._buscar_endereco_completo(entrada_usuario)
        
        # Estratégia 3: Análise de texto inteligente
        if not resultado:
            resultado = self._analisar_texto_endereco(entrada_usuario)
        
        # Estratégia 4: Fallback com dados conhecidos
        if not resultado:
            resultado = self._buscar_fallback_local(entrada_usuario)
        
        # Cache do resultado
        if resultado:
            self.cache_enderecos[entrada_limpa] = resultado
        
        return resultado or EnderecoInfo(endereco_completo=entrada_usuario, confiabilidade="baixa")
    
    def _eh_cep(self, texto: str) -> bool:
        """Verifica se texto é um CEP"""
        cep_pattern = r'^\d{5}-?\d{3}$'
        return bool(re.match(cep_pattern, texto.replace(' ', '')))
    
    def _buscar_por_cep(self, cep: str) -> Optional[EnderecoInfo]:
        """Busca endereço por CEP usando ViaCEP"""
        
        cep_limpo = re.sub(r'\D', '', cep)
        
        if len(cep_limpo) != 8:
            return None
        
        try:
            # API ViaCEP
            url = f"https://viacep.com.br/ws/{cep_limpo}/json/"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'erro' not in data and data.get('localidade', '').lower() == 'curitiba':
                    bairro = data.get('district', '').lower() or data.get('bairro', '').lower()
                    zona_estimada = self._estimar_zona_por_bairro(bairro)
                    
                    return EnderecoInfo(
                        endereco_completo=f"{data.get('logradouro', '')} - {data.get('district', '')}, Curitiba/PR",
                        cep=data.get('cep', ''),
                        logradouro=data.get('logradouro', ''),
                        bairro=data.get('district', ''),
                        cidade=data.get('localidade', ''),
                        estado=data.get('uf', ''),
                        zona_estimada=zona_estimada,
                        confiabilidade="alta"
                    )
                    
        except Exception as e:
            st.warning(f"⚠️ Erro na consulta de CEP: {e}")
        
        return None
    
    def _buscar_endereco_completo(self, endereco: str) -> Optional[EnderecoInfo]:
        """Busca endereço completo usando APIs de geocodificação"""
        
        if not endereco or len(endereco.strip()) < 5:
            return None
        
        endereco_curitiba = f"{endereco}, Curitiba, PR, Brasil"
        
        try:
            # Nominatim (OpenStreetMap) - API gratuita
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': endereco_curitiba,
                'format': 'json',
                'addressdetails': 1,
                'limit': 1,
                'countrycodes': 'br'
            }
            
            headers = {
                'User-Agent': 'AssistenteRegulamentacao/2.0 (contato@exemplo.com)'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data:
                    result = data[0]
                    address = result.get('address', {})
                    
                    # Verificar se é realmente Curitiba
                    cidade = address.get('city', '').lower()
                    if 'curitiba' not in cidade:
                        return None
                    
                    lat = float(result.get('lat', 0))
                    lon = float(result.get('lon', 0))
                    
                    # Verificar coordenadas de Curitiba
                    if not (-25.6 < lat < -25.3 and -49.4 < lon < -49.1):
                        return None
                    
                    bairro = address.get('suburb', '').lower() or address.get('neighbourhood', '').lower()
                    zona_estimada = self._estimar_zona_por_bairro(bairro)
                    
                    return EnderecoInfo(
                        endereco_completo=result.get('display_name', endereco),
                        logradouro=address.get('road', ''),
                        numero=address.get('house_number', ''),
                        bairro=bairro.title(),
                        cidade='Curitiba',
                        estado='PR',
                        coordenadas=(lat, lon),
                        zona_estimada=zona_estimada,
                        confiabilidade="alta"
                    )
                    
        except Exception as e:
            st.warning(f"⚠️ Erro na geocodificação: {e}")
        
        return None
    
    def _analisar_texto_endereco(self, texto: str) -> Optional[EnderecoInfo]:
        """Análise inteligente de texto para extrair informações"""
        
        texto_lower = texto.lower()
        
        # Procurar por bairros conhecidos
        bairro_encontrado = None
        zona_estimada = None
        
        for bairro, zona in self.bairros_zonas.items():
            if bairro in texto_lower:
                bairro_encontrado = bairro.title()
                zona_estimada = zona
                break
        
        # Procurar padrões de endereço
        patterns = {
            'rua': r'(?:rua|r\.)\s+([^,\-\d]+)',
            'avenida': r'(?:avenida|av\.)\s+([^,\-\d]+)',
            'numero': r'(?:n[°º]?|número)\s*(\d+)',
            'cep': r'(\d{5}-?\d{3})'
        }
        
        info_extraida = {}
        for tipo, pattern in patterns.items():
            match = re.search(pattern, texto_lower)
            if match:
                info_extraida[tipo] = match.group(1).strip()
        
        # Construir resultado
        if bairro_encontrado or info_extraida:
            endereco_reconstruido = texto
            
            return EnderecoInfo(
                endereco_completo=endereco_reconstruido,
                bairro=bairro_encontrado or "",
                zona_estimada=zona_estimada or "",
                confiabilidade="média"
            )
        
        return None
    
    def _buscar_fallback_local(self, endereco: str) -> Optional[EnderecoInfo]:
        """Sistema fallback com dados conhecidos localmente"""
        
        texto_lower = endereco.lower()
        
        # Endereços conhecidos de exemplo
        enderecos_conhecidos = {
            "centro civico": EnderecoInfo(
                endereco_completo="Centro Cívico, Curitiba/PR",
                bairro="Centro Cívico",
                cidade="Curitiba",
                estado="PR",
                zona_estimada="ZCC",
                confiabilidade="média"
            ),
            "linha verde": EnderecoInfo(
                endereco_completo="Região da Linha Verde, Curitiba/PR",
                bairro="Linha Verde",
                cidade="Curitiba",
                estado="PR",
                zona_estimada="ZR-4",
                confiabilidade="média"
            ),
            "batel": EnderecoInfo(
                endereco_completo="Batel, Curitiba/PR",
                bairro="Batel",
                cidade="Curitiba",
                estado="PR",
                zona_estimada="ZUM-1",
                confiabilidade="média"
            )
        }
        
        for chave, info in enderecos_conhecidos.items():
            if chave in texto_lower:
                return info
        
        return None
    
    def _estimar_zona_por_bairro(self, bairro: str) -> str:
        """Estima zona baseada no bairro"""
        
        bairro_lower = bairro.lower().strip()
        
        # Busca exata
        if bairro_lower in self.bairros_zonas:
            return self.bairros_zonas[bairro_lower]
        
        # Busca parcial
        for bairro_conhecido, zona in self.bairros_zonas.items():
            if bairro_conhecido in bairro_lower or bairro_lower in bairro_conhecido:
                return zona
        
        # Fallback baseado em padrões
        if 'centro' in bairro_lower:
            return 'ZC'
        elif 'industrial' in bairro_lower:
            return 'ZI'
        elif any(word in bairro_lower for word in ['jardim', 'vila', 'conjunto']):
            return 'ZR-2'
        else:
            return 'ZR-3'  # Padrão residencial
    
    def validar_endereco_curitiba(self, endereco_info: EnderecoInfo) -> bool:
        """Valida se endereço pertence a Curitiba"""
        
        if not endereco_info:
            return False
        
        # Verificar cidade explícita
        if endereco_info.cidade and 'curitiba' in endereco_info.cidade.lower():
            return True
        
        # Verificar coordenadas
        if endereco_info.coordenadas:
            lat, lon = endereco_info.coordenadas
            if -25.6 < lat < -25.3 and -49.4 < lon < -49.1:
                return True
        
        # Verificar bairros conhecidos
        if endereco_info.bairro and endereco_info.bairro.lower() in self.bairros_zonas:
            return True
        
        return False

# Interface Streamlit
def interface_busca_endereco() -> Optional[EnderecoInfo]:
    """Interface para busca de endereço"""
    
    st.subheader("🔍 Busca Inteligente de Endereço")
    
    # Criar instância do buscador
    buscador = BuscaEndereco()
    
    # Opções de entrada
    tipo_busca = st.radio(
        "Como você quer informar o endereço?",
        ["✍️ Digite o endereço", "📮 Informar CEP", "🗺️ Selecionar bairro"]
    )
    
    endereco_info = None
    
    if tipo_busca == "✍️ Digite o endereço":
        endereco = st.text_input(
            "Digite o endereço completo:",
            placeholder="Ex: Rua das Flores, 123, Batel, Curitiba/PR",
            help="Digite o endereço mais completo possível"
        )
        
        if endereco and len(endereco.strip()) > 3:
            if st.button("🔍 Buscar Endereço"):
                with st.spinner("Buscando endereço..."):
                    endereco_info = buscador.buscar_endereco_inteligente(endereco)
    
    elif tipo_busca == "📮 Informar CEP":
        cep = st.text_input(
            "Digite o CEP:",
            placeholder="Ex: 80020-000",
            help="CEP de Curitiba"
        )
        
        if cep and len(cep.replace('-', '').replace(' ', '')) >= 8:
            if st.button("🔍 Buscar por CEP"):
                with st.spinner("Consultando CEP..."):
                    endereco_info = buscador.buscar_endereco_inteligente(cep)
    
    else:  # Selecionar bairro
        bairros_disponiveis = sorted(buscador.bairros_zonas.keys())
        bairro_selecionado = st.selectbox(
            "Selecione o bairro:",
            ["Escolha um bairro..."] + [b.title() for b in bairros_disponiveis]
        )
        
        if bairro_selecionado and bairro_selecionado != "Escolha um bairro...":
            endereco_info = EnderecoInfo(
                endereco_completo=f"{bairro_selecionado}, Curitiba/PR",
                bairro=bairro_selecionado,
                cidade="Curitiba",
                estado="PR",
                zona_estimada=buscador.bairros_zonas[bairro_selecionado.lower()],
                confiabilidade="alta"
            )
    
    # Mostrar resultado
    if endereco_info:
        mostrar_resultado_busca(endereco_info, buscador)
        return endereco_info
    
    return None

def mostrar_resultado_busca(endereco_info: EnderecoInfo, buscador: BuscaEndereco):
    """Mostra resultado da busca de endereço"""
    
    if not endereco_info:
        return
    
    # Validar se é de Curitiba
    eh_curitiba = buscador.validar_endereco_curitiba(endereco_info)
    
    if not eh_curitiba:
        st.error("❌ Endereço não pertence a Curitiba ou não foi possível validar.")
        return
    
    # Mostrar informações encontradas
    st.success("✅ Endereço encontrado e validado!")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"""
        **📍 Endereço Localizado:**
        - **Completo:** {endereco_info.endereco_completo}
        - **Bairro:** {endereco_info.bairro or 'Não identificado'}
        - **CEP:** {endereco_info.cep or 'Não informado'}
        - **Confiabilidade:** {endereco_info.confiabilidade.title()}
        """)
    
    with col2:
        zona_cor = "🟢" if endereco_info.zona_estimada else "🔍"
        st.info(f"""
        **🎯 Análise de Zoneamento:**
        - **Zona Estimada:** {zona_cor} {endereco_info.zona_estimada or 'Análise necessária'}
        - **Coordenadas:** {'✅ Disponível' if endereco_info.coordenadas else '❌ Não disponível'}
        """)
    
    # Alertas importantes
    if endereco_info.confiabilidade == "baixa":
        st.warning("⚠️ **Atenção:** Informações com baixa confiabilidade. Verifique manualmente.")
    
    if not endereco_info.zona_estimada:
        st.warning("⚠️ **Zona não identificada automaticamente.** Você deverá informar manualmente.")

if __name__ == "__main__":
    st.title("🏠 Sistema de Busca de Endereços")
    
    resultado = interface_busca_endereco()
    
    if resultado:
        st.json({
            "endereco_completo": resultado.endereco_completo,
            "bairro": resultado.bairro,
            "zona_estimada": resultado.zona_estimada,
            "confiabilidade": resultado.confiabilidade
        })