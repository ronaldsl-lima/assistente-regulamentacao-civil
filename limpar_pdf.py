# limpar_pdf.py
from pathlib import Path
import pypdf

PASTA_DADOS = Path(__file__).parent / "dados" / "curitiba"
ARQUIVO_ORIGINAL = "00304472.pdf"
ARQUIVO_LIMPO = "lei_curitiba_limpa.pdf"
PAGINAS_PARA_MANTER = 97

caminho_original = PASTA_DADOS / ARQUIVO_ORIGINAL
caminho_limpo = PASTA_DADOS / ARQUIVO_LIMPO

if not caminho_original.exists():
    print(f"ERRO: Arquivo original '{ARQUIVO_ORIGINAL}' não encontrado.")
else:
    try:
        print(f"Lendo o arquivo original: {caminho_original.name}...")
        leitor = pypdf.PdfReader(caminho_original)
        escritor = pypdf.PdfWriter()
        print(f"Copiando as primeiras {PAGINAS_PARA_MANTER} páginas...")
        for i in range(PAGINAS_PARA_MANTER):
            if i < len(leitor.pages):
                escritor.add_page(leitor.pages[i])
        with open(caminho_limpo, "wb") as f:
            escritor.write(f)
        print(f"SUCESSO! Arquivo '{ARQUIVO_LIMPO}' criado com sucesso.")
    except Exception as e:
        print(f"Ocorreu um erro ao processar o PDF: {e}")