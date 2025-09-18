# 🐍 CONFIGURAÇÃO PYTHON 3.11 NO STREAMLIT CLOUD

## ⚠️ PROBLEMA IDENTIFICADO
As dependências `geopandas==0.10.2` e `pyproj==3.2.1` requerem Python 3.11 para compatibilidade total.

## 🔧 SOLUÇÃO MANUAL NO STREAMLIT CLOUD

### 1. Acessar Configurações Avançadas
1. Vá para o dashboard da sua app no Streamlit Cloud
2. Clique em **"Settings"** (⚙️)
3. Procure por **"Advanced settings"** ou **"Python version"**

### 2. Especificar Python 3.11
- **Opção 1:** Campo "Python version" → selecione **3.11**
- **Opção 2:** Se houver campo de environment variables, adicione:
  ```
  PYTHON_VERSION=3.11
  ```

### 3. Redeployar
- Clique em **"Reboot"** ou **"Redeploy"**
- Aguarde novo build com Python 3.11

## 📁 ARQUIVOS CRIADOS AUTOMATICAMENTE

✅ **`.python-version`** → Contém: `3.11`
✅ **`runtime.txt`** → Contém: `python-3.11`

Estes arquivos podem ser detectados automaticamente pelo Streamlit Cloud.

## 🎯 RESULTADO ESPERADO
Com Python 3.11, as dependências geoespaciais devem instalar corretamente:
- ✅ geopandas==0.10.2
- ✅ pyproj==3.2.1
- ✅ Todas as outras dependências

## 🔗 URL FINAL
`https://assistente-regulamentacao-civil.streamlit.app`

---
**Após configurar Python 3.11, o deploy deve funcionar perfeitamente!** 🚀