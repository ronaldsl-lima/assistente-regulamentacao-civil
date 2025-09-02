# 🚀 Guia de Deploy - Streamlit Community Cloud

## 📋 Pré-requisitos

1. ✅ Conta no GitHub (gratuita)
2. ✅ Chave API do Google Gemini
3. ✅ Todos os arquivos estão prontos!

## 🔥 Passo a Passo (15 minutos)

### **Passo 1: Criar Repositório no GitHub**
1. Vá para [github.com](https://github.com) e faça login
2. Clique em **"New repository"**
3. Nome: `assistente-regulamentacao-civil`
4. Descrição: `Sistema AI para análise de conformidade urbanística - Curitiba`
5. ✅ **Public** (necessário para tier gratuito)
6. ✅ **Add README.md** (já temos um)
7. Clique **"Create repository"**

### **Passo 2: Upload dos Arquivos**
No terminal do Windows/Git Bash:
```bash
cd "C:\Users\User\assistente_final"
git init
git add .
git commit -m "Deploy inicial do Assistente de Regulamentação Civil"
git remote add origin https://github.com/SEU-USUARIO/assistente-regulamentacao-civil.git
git push -u origin main
```

### **Passo 3: Deploy no Streamlit Cloud**
1. Vá para [share.streamlit.io](https://share.streamlit.io)
2. Faça login com sua conta GitHub
3. Clique **"New app"**
4. Selecione:
   - **Repository**: `assistente-regulamentacao-civil`
   - **Branch**: `main`
   - **Main file path**: `app.py`
5. Clique **"Deploy!"**

### **Passo 4: Configurar Secrets (API Key)**
1. No painel do Streamlit Cloud, vá em **"Settings"**
2. Na aba **"Secrets"**, cole:
```toml
GOOGLE_API_KEY = "AIzaSyA5Dz_ttb5Y1wm4Iu24P9C1U2GDEH0gA5Y"
```
3. Clique **"Save"**

### **Passo 5: Aguardar Deploy**
- ⏱️ Tempo: 5-10 minutos
- 📊 Status: Acompanhe os logs em tempo real
- 🎉 **Pronto!** Seu link será: `https://assistente-regulamentacao-civil.streamlit.app`

## 🔗 Compartilhando com seu Amigo

Envie o link: **https://assistente-regulamentacao-civil.streamlit.app**

## 🛠️ Troubleshooting

**Erro de dependências?**
- Streamlit Cloud instala automaticamente via `requirements.txt`

**Erro de API Key?**
- Verifique se foi copiada corretamente nos Secrets

**Deploy lento?**
- Normal na primeira vez (instala todas as dependências)

## 📊 Monitoramento

- 📈 **Analytics**: Painel do Streamlit Cloud
- 🔄 **Updates**: Push no GitHub = redeploy automático
- 💾 **Logs**: Disponíveis no painel

---

🚀 **Seu sistema estará online em minutos!**