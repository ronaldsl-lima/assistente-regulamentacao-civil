# teste_extracao.py
import pypdf
from pathlib import Path

# --- Configuração do Teste ---
NOME_DO_ARQUIVO = "00304472.pdf"
PAGINA_PARA_ANALISAR = 65 # Página que contém o QUADRO XVII (ZR2)
# -----------------------------

# Constrói o caminho para o arquivo PDF dentro da pasta de dados
caminho_do_arquivo = Path(__file__).parent / "dados" / "curitiba" / NOME_DO_ARQUIVO

print(f"--- Iniciando teste de extração de texto ---")
print(f"Arquivo: {caminho_do_arquivo}")
print(f"Página Alvo: {PAGINA_PARA_ANALISAR}\n")

if not caminho_do_arquivo.exists():
    print("ERRO: Arquivo PDF não encontrado no caminho especificado. Verifique o nome e a localização do arquivo.")
else:
    try:
        leitor = pypdf.PdfReader(caminho_do_arquivo)
        
        # A contagem de páginas em pypdf começa em 0, então subtraímos 1
        pagina = leitor.pages[PAGINA_PARA_ANALISAR - 1]
        
        texto_extraido = pagina.extract_text()
        
        print(f"--- TEXTO EXTRAÍDO DA PÁGINA {PAGINA_PARA_ANALISAR} ---")
        if texto_extraido:
            print(texto_extraido)
        else:
            print("!!! ATENÇÃO: Nenhum texto foi extraído desta página. !!!")
        print("--- FIM DO TEXTO EXTRAÍDO ---")

    except Exception as e:
        print(f"Ocorreu um erro durante a leitura do PDF: {e}")