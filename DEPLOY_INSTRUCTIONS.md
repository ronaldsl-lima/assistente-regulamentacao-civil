# 🚀 INSTRUÇÕES DE DEPLOY - STREAMLIT COMMUNITY CLOUD

## ✅ STATUS DO PROJETO
- **Repositório:** https://github.com/ronaldsl-lima/assistente-regulamentacao-civil
- **Branch:** main
- **Último commit:** ✅ API POSITIONSTACK funcionando perfeitamente
- **Requirements:** Otimizado para deploy
- **Arquivos principais:** ✅ app.py, requirements.txt, .streamlit/config.toml

## 🚀 PASSOS PARA DEPLOY

### 1. Acessar Streamlit Community Cloud
- Vá para: https://share.streamlit.io/
- Faça login com sua conta GitHub

### 2. Criar Nova Aplicação
- Clique em **"New app"**
- Repository: `ronaldsl-lima/assistente-regulamentacao-civil`
- Branch: `main`
- Main file path: `app.py`
- App URL (custom): `assistente-regulamentacao-civil`

### 3. ⚠️ CONFIGURAR SECRETS (OBRIGATÓRIO)
Antes de fazer deploy, adicione no painel "Secrets":

```toml
[secrets]
GOOGLE_API_KEY = "AIzaSyA5Dz_ttb5Y1wm4Iu24P9C1U2GDEH0gA5Y"
GEOCODING_API_KEY = "5d74e43398ad3ab452ad6472deb2d155"
```

### 4. Deploy
- Clique em **"Deploy!"**
- Aguardar build (2-3 minutos)

## 🌐 URL FINAL ESPERADA
```
https://assistente-regulamentacao-civil.streamlit.app
```

## 🔧 TROUBLESHOOTING

### Se o deploy falhar:
1. Verificar se secrets foram adicionados
2. Verificar se requirements.txt está correto
3. Logs de erro aparecerão na interface

### Se a API não funcionar:
1. Verificar secrets no painel
2. Testar chave PositionStack: `5d74e43398ad3ab452ad6472deb2d155`

## 📋 FUNCIONALIDADES DISPONÍVEIS
- ✅ Consulta por endereço (PositionStack + Layer 36)
- ✅ Consulta por coordenadas (Layer 36 direto)
- ✅ Mapas interativos Folium
- ✅ Histórico de consultas
- ✅ Sistema de fallback robusto

## 🎯 TESTE RECOMENDADO
Após deploy, testar com:
- **Endereço:** "Rua XV de Novembro, 1000, Centro"
- **Coordenadas:** -25.428218, -49.264049

---
**Sistema preparado e otimizado para produção!** 🚀