#!/usr/bin/env python3
"""
Gerador de Relatório PDF Profissional
Relatórios técnicos completos para análise urbanística
"""

import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics import renderPDF
from datetime import datetime
import io
import base64
from typing import Dict, Any, List
import qrcode
from PIL import Image as PILImage
import tempfile
import os

class GeradorRelatorioPDF:
    """Gerador de relatórios PDF profissionais"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._criar_estilos_customizados()
        
    def _criar_estilos_customizados(self):
        """Cria estilos customizados para o relatório"""
        
        # Título principal
        self.styles.add(ParagraphStyle(
            name='TituloPrincipal',
            parent=self.styles['Title'],
            fontSize=24,
            textColor=colors.HexColor('#1f4e79'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Subtítulo
        self.styles.add(ParagraphStyle(
            name='Subtitulo',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#2e75b6'),
            spaceBefore=20,
            spaceAfter=12,
            fontName='Helvetica-Bold'
        ))
        
        # Cabeçalho de seção
        self.styles.add(ParagraphStyle(
            name='CabecalhoSecao',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#4472c4'),
            spaceBefore=15,
            spaceAfter=8,
            fontName='Helvetica-Bold'
        ))
        
        # Texto de resultado
        self.styles.add(ParagraphStyle(
            name='TextoResultado',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceBefore=6,
            spaceAfter=6,
            alignment=TA_JUSTIFY,
            fontName='Helvetica'
        ))
        
        # Status conforme
        self.styles.add(ParagraphStyle(
            name='StatusConforme',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.green,
            fontName='Helvetica-Bold'
        ))
        
        # Status não conforme
        self.styles.add(ParagraphStyle(
            name='StatusNaoConforme',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.red,
            fontName='Helvetica-Bold'
        ))
    
    def gerar_relatorio_completo(self, dados: Dict[str, Any]) -> bytes:
        """Gera relatório PDF completo"""
        
        # Criar buffer em memória
        buffer = io.BytesIO()
        
        # Criar documento PDF
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        # Construir conteúdo
        story = []
        
        # Capa
        story.extend(self._criar_capa(dados))
        story.append(PageBreak())
        
        # Resumo executivo
        story.extend(self._criar_resumo_executivo(dados))
        story.append(Spacer(1, 0.5*inch))
        
        # Dados do projeto
        story.extend(self._criar_secao_dados_projeto(dados))
        story.append(Spacer(1, 0.3*inch))
        
        # Análise de conformidade
        story.extend(self._criar_secao_conformidade(dados))
        story.append(Spacer(1, 0.3*inch))
        
        # Parâmetros detalhados
        story.extend(self._criar_secao_parametros(dados))
        story.append(Spacer(1, 0.3*inch))
        
        # Documentos consultados
        story.extend(self._criar_secao_documentos(dados))
        story.append(Spacer(1, 0.3*inch))
        
        # Conclusões e recomendações
        story.extend(self._criar_secao_conclusoes(dados))
        
        # Rodapé final
        story.extend(self._criar_rodape_final())
        
        # Construir PDF
        doc.build(story)
        
        # Retornar bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
    
    def _criar_capa(self, dados: Dict) -> List:
        """Cria página de capa"""
        
        story = []
        
        # Logo/Cabeçalho (simulado)
        story.append(Spacer(1, 1*inch))
        
        # Título
        titulo = "RELATÓRIO DE ANÁLISE URBANÍSTICA"
        story.append(Paragraph(titulo, self.styles['TituloPrincipal']))
        story.append(Spacer(1, 0.5*inch))
        
        # Subtítulo com endereço
        endereco = dados.get('endereco', 'Endereço não informado')
        zona = dados.get('zona', 'Zona não identificada')
        subtitulo = f"Endereço: {endereco}<br/>Zona: {zona}"
        story.append(Paragraph(subtitulo, self.styles['Subtitulo']))
        story.append(Spacer(1, 1*inch))
        
        # Status geral
        conformidade = dados.get('conformidade_geral', 'CONFORME')
        cor_status = colors.green if 'CONFORME' in conformidade else colors.red
        
        status_texto = f"""
        <b>STATUS GERAL:</b><br/>
        <font color="{cor_status.hexval()}">{conformidade}</font>
        """
        story.append(Paragraph(status_texto, self.styles['Subtitulo']))
        story.append(Spacer(1, 1*inch))
        
        # Informações do relatório
        data_atual = datetime.now().strftime("%d/%m/%Y às %H:%M")
        info_relatorio = f"""
        <b>Data do Relatório:</b> {data_atual}<br/>
        <b>Versão:</b> 1.0<br/>
        <b>Gerado por:</b> Assistente de Regulamentação Civil<br/>
        <b>Base Legal:</b> Lei Municipal de Zoneamento de Curitiba
        """
        story.append(Paragraph(info_relatorio, self.styles['TextoResultado']))
        
        # QR Code (simulado)
        story.append(Spacer(1, 1*inch))
        qr_texto = "QR Code para validação: [código seria gerado aqui]"
        story.append(Paragraph(qr_texto, self.styles['Normal']))
        
        return story
    
    def _criar_resumo_executivo(self, dados: Dict) -> List:
        """Cria seção de resumo executivo"""
        
        story = []
        
        story.append(Paragraph("RESUMO EXECUTIVO", self.styles['Subtitulo']))
        
        # Tabela resumo
        dados_tabela = [
            ['Parâmetro', 'Status', 'Observação'],
            ['Endereço', dados.get('endereco', 'N/A'), ''],
            ['Zona', dados.get('zona', 'N/A'), ''],
            ['Status Geral', dados.get('conformidade_geral', 'N/A'), ''],
            ['Parâmetros Conformes', f"{dados.get('parametros_conformes', 0)}/{dados.get('total_parametros', 0)}", ''],
            ['Data da Análise', datetime.now().strftime("%d/%m/%Y"), '']
        ]
        
        tabela = Table(dados_tabela, colWidths=[4*cm, 4*cm, 6*cm])
        tabela.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472c4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f2f2f2')),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(tabela)
        
        return story
    
    def _criar_secao_dados_projeto(self, dados: Dict) -> List:
        """Cria seção com dados do projeto"""
        
        story = []
        
        story.append(Paragraph("DADOS DO PROJETO", self.styles['Subtitulo']))
        
        # Dados básicos
        parametros_projeto = dados.get('parametros_projeto', {})
        
        dados_projeto = [
            ['Parâmetro', 'Valor Proposto', 'Unidade'],
            ['Taxa de Ocupação', str(parametros_projeto.get('taxa_ocupacao', 'N/A')), '%'],
            ['Coeficiente de Aproveitamento', str(parametros_projeto.get('coeficiente_aproveitamento', 'N/A')), ''],
            ['Altura da Edificação', str(parametros_projeto.get('altura_edificacao', 'N/A')), 'metros'],
            ['Área do Terreno', str(parametros_projeto.get('area_terreno', 'N/A')), 'm²'],
            ['Área Construída', str(parametros_projeto.get('area_construida', 'N/A')), 'm²'],
            ['Área Permeável', str(parametros_projeto.get('area_permeavel', 'N/A')), '%'],
        ]
        
        tabela_projeto = Table(dados_projeto, colWidths=[6*cm, 4*cm, 3*cm])
        tabela_projeto.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2e75b6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(tabela_projeto)
        
        return story
    
    def _criar_secao_conformidade(self, dados: Dict) -> List:
        """Cria seção de análise de conformidade"""
        
        story = []
        
        story.append(Paragraph("ANÁLISE DE CONFORMIDADE", self.styles['Subtitulo']))
        
        # Análise por parâmetro
        analises = dados.get('analises_parametros', {})
        
        dados_conformidade = [['Parâmetro', 'Projeto', 'Permitido', 'Status']]
        
        for param, info in analises.items():
            status = info.get('status', 'N/A')
            cor_status = 'green' if status == 'CONFORME' else 'red'
            
            dados_conformidade.append([
                param,
                str(info.get('valor_projeto', 'N/A')),
                str(info.get('valor_limite', 'N/A')),
                status
            ])
        
        tabela_conf = Table(dados_conformidade, colWidths=[4*cm, 3*cm, 3*cm, 4*cm])
        tabela_conf.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4e79')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            # Colorir coluna de status
            ('TEXTCOLOR', (3, 1), (3, -1), colors.black),
        ]))
        
        story.append(tabela_conf)
        
        return story
    
    def _criar_secao_parametros(self, dados: Dict) -> List:
        """Cria seção detalhada de parâmetros da zona"""
        
        story = []
        
        story.append(Paragraph("PARÂMETROS DA ZONA", self.styles['Subtitulo']))
        
        zona = dados.get('zona', 'N/A')
        parametros_zona = dados.get('parametros_zona', {})
        
        texto_parametros = f"""
        <b>Zona:</b> {zona}<br/><br/>
        
        <b>Parâmetros Urbanísticos Vigentes:</b><br/>
        • Taxa de Ocupação: {parametros_zona.get('taxa_ocupacao', 'N/A')}<br/>
        • Coeficiente de Aproveitamento: {parametros_zona.get('coeficiente_aproveitamento', 'N/A')}<br/>
        • Altura Máxima: {parametros_zona.get('altura_maxima', 'N/A')}<br/>
        • Recuo Frontal: {parametros_zona.get('recuo_frontal', 'N/A')}<br/>
        • Recuos Laterais: {parametros_zona.get('recuos_laterais', 'N/A')}<br/>
        • Recuo de Fundos: {parametros_zona.get('recuo_fundos', 'N/A')}<br/>
        • Área Permeável: {parametros_zona.get('area_permeavel', 'N/A')}<br/><br/>
        
        <b>Base Legal:</b> Lei Municipal de Zoneamento de Curitiba
        """
        
        story.append(Paragraph(texto_parametros, self.styles['TextoResultado']))
        
        return story
    
    def _criar_secao_documentos(self, dados: Dict) -> List:
        """Cria seção de documentos consultados"""
        
        story = []
        
        story.append(Paragraph("DOCUMENTOS CONSULTADOS", self.styles['Subtitulo']))
        
        documentos = dados.get('documentos_consultados', [])
        
        if documentos:
            for i, doc in enumerate(documentos[:3], 1):  # Máximo 3 documentos
                texto_doc = f"""
                <b>Documento {i}:</b><br/>
                Fonte: {doc.get('source', 'Lei Municipal')}<br/>
                Tipo: {doc.get('tipo_conteudo', 'N/A')}<br/>
                Zona: {doc.get('zona_especifica', 'N/A')}<br/>
                <i>Conteúdo:</i> {doc.get('content', '')[:200]}...<br/><br/>
                """
                story.append(Paragraph(texto_doc, self.styles['TextoResultado']))
        else:
            story.append(Paragraph("Nenhum documento específico consultado.", self.styles['TextoResultado']))
        
        return story
    
    def _criar_secao_conclusoes(self, dados: Dict) -> List:
        """Cria seção de conclusões e recomendações"""
        
        story = []
        
        story.append(Paragraph("CONCLUSÕES E RECOMENDAÇÕES", self.styles['Subtitulo']))
        
        conformidade = dados.get('conformidade_geral', 'ANÁLISE PENDENTE')
        
        if 'CONFORME' in conformidade:
            conclusao = """
            <b>CONCLUSÃO:</b> O projeto apresentado está em CONFORMIDADE com os parâmetros 
            urbanísticos da zona analisada. Todos os índices e recuos atendem às exigências 
            da legislação municipal vigente.
            
            <b>RECOMENDAÇÕES:</b>
            • Prosseguir com o projeto conforme proposto
            • Verificar demais exigências do código de obras
            • Consultar órgãos competentes para aprovação final
            """
        else:
            conclusao = """
            <b>CONCLUSÃO:</b> O projeto apresenta NÃO CONFORMIDADES com os parâmetros 
            urbanísticos da zona. Ajustes são necessários para adequação à legislação.
            
            <b>RECOMENDAÇÕES:</b>
            • Revisar projeto para adequação aos parâmetros
            • Considerar alternativas de implantação
            • Consultar profissional habilitado para revisão
            • Nova análise após ajustes
            """
        
        story.append(Paragraph(conclusao, self.styles['TextoResultado']))
        
        return story
    
    def _criar_rodape_final(self) -> List:
        """Cria rodapé final do relatório"""
        
        story = []
        
        story.append(Spacer(1, 0.5*inch))
        
        rodape = """
        <hr/><br/>
        <i>Este relatório foi gerado automaticamente pelo Sistema de Assistente de 
        Regulamentação Civil. As informações apresentadas baseiam-se na legislação 
        vigente e nos dados fornecidos. Para aprovações oficiais, consulte sempre 
        os órgãos competentes.</i><br/><br/>
        
        <b>Sistema:</b> Assistente de Regulamentação Civil v2.0<br/>
        <b>Gerado em:</b> {}<br/>
        <b>Validade:</b> Este relatório tem caráter consultivo
        """.format(datetime.now().strftime("%d/%m/%Y às %H:%M"))
        
        story.append(Paragraph(rodape, self.styles['Normal']))
        
        return story

# Função principal para integração
def gerar_relatorio_pdf(dados_analise: Dict) -> bytes:
    """Função principal para gerar relatório PDF"""
    
    gerador = GeradorRelatorioPDF()
    return gerador.gerar_relatorio_completo(dados_analise)

def criar_botao_download_pdf(dados_analise: Dict):
    """Cria botão de download do relatório PDF"""
    
    if st.button("📄 Gerar Relatório PDF", help="Baixar relatório técnico completo"):
        
        with st.spinner("Gerando relatório PDF..."):
            try:
                pdf_bytes = gerar_relatorio_pdf(dados_analise)
                
                # Criar nome do arquivo
                endereco = dados_analise.get('endereco', 'endereco')
                endereco_limpo = ''.join(c for c in endereco if c.isalnum() or c in (' ', '-', '_'))[:30]
                data = datetime.now().strftime("%Y%m%d_%H%M")
                nome_arquivo = f"relatorio_urbanistico_{endereco_limpo}_{data}.pdf"
                
                # Botão de download
                st.download_button(
                    label="📥 Baixar Relatório PDF",
                    data=pdf_bytes,
                    file_name=nome_arquivo,
                    mime="application/pdf",
                    help="Clique para baixar o relatório em PDF"
                )
                
                st.success("✅ Relatório gerado com sucesso!")
                
            except Exception as e:
                st.error(f"❌ Erro ao gerar relatório: {str(e)}")

if __name__ == "__main__":
    # Teste do gerador de PDF
    st.title("🏗️ Gerador de Relatório PDF")
    
    # Dados de teste
    dados_teste = {
        'endereco': 'Rua das Flores, 123 - Curitiba/PR',
        'zona': 'ZR2',
        'conformidade_geral': 'PROJETO EM NÃO CONFORMIDADE',
        'parametros_conformes': 2,
        'total_parametros': 4,
        'parametros_projeto': {
            'taxa_ocupacao': 75,
            'coeficiente_aproveitamento': 2.5,
            'altura_edificacao': 15,
            'area_terreno': 500,
            'area_construida': 1250,
            'area_permeavel': 12
        },
        'parametros_zona': {
            'taxa_ocupacao': '70%',
            'coeficiente_aproveitamento': '2,0',
            'altura_maxima': '12 metros',
            'area_permeavel': '15%'
        },
        'analises_parametros': {
            'Taxa de Ocupação': {'valor_projeto': '75%', 'valor_limite': '70%', 'status': 'NÃO CONFORME'},
            'Coef. Aproveitamento': {'valor_projeto': '2.5', 'valor_limite': '2.0', 'status': 'NÃO CONFORME'},
        },
        'documentos_consultados': [
            {'source': 'Lei Municipal', 'tipo_conteudo': 'parametros_urbanisticos', 'zona_especifica': 'ZR2', 'content': 'Parâmetros da zona residencial...'}
        ]
    }
    
    criar_botao_download_pdf(dados_teste)