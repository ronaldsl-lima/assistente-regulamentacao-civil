#!/usr/bin/env python3
"""
Script para adicionar inscrições imobiliárias reais ao sistema
Para adicionar a inscrição real do usuário que retorna ZCC.4
"""

def adicionar_inscricao_real():
    """
    Execute este script para adicionar a inscrição real do usuário
    """
    print("Script para Adicionar Inscricao Imobiliaria Real")
    print("=" * 50)
    
    print("""
PASSO A PASSO:

1. Abra o arquivo: app.py
2. Procure pela linha 85: 'INSCRIÇÃO_REAL_AQUI'
3. Substitua por sua inscrição real (apenas números)
4. Substitua 'area_terreno': None pela área real
5. Salve o arquivo

EXEMPLO:
DE:   'INSCRIÇÃO_REAL_AQUI': {
PARA: '12345678901': {

RESULTADO:
[OK] Sistema reconhecera sua inscricao
[OK] Retornara ZCC.4 - ZONA CENTRO CIVICO  
[OK] Dados reais serao preenchidos automaticamente
""")

    inscricao = input("Digite sua inscrição imobiliária (apenas números): ").strip()
    area = input("Digite a área do terreno (m²) ou deixe em branco: ").strip()
    
    if inscricao:
        print(f"""
CÓDIGO PARA ADICIONAR NO ARQUIVO app.py (linha 85):

'{inscricao}': {{
    'endereco': 'Centro Cívico, Curitiba-PR',
    'zona': 'ZCC.4',
    'zona_completa': 'ZONA CENTRO CÍVICO', 
    'area_terreno': {area if area else 'None'},
    'testada': None,
    'possui_app': False,
    'possui_drenagem': False,
    'quadra': None,
    'lote': None
}},

Depois de adicionar, teste no sistema!
""")

if __name__ == "__main__":
    adicionar_inscricao_real()