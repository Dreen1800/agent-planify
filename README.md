# 🤖 Planify Agent - Assistente Financeiro WhatsApp

Assistente financeiro inteligente que funciona via WhatsApp, com personalidade de mordomo britânico sofisticado.

## 🚀 Deploy Rápido na VPS

### 1. Preparação da VPS

```bash
# Conecte na sua VPS
ssh root@seu-servidor

# Atualize o sistema
apt update && apt upgrade -y

# Clone o repositório
git clone https://github.com/seu-usuario/agent-planify.git
cd agent-planify
```

### 2. Configuração das Variáveis de Ambiente

```bash
# Copie o template e configure suas credenciais
cp env.template .env
nano .env
```

Configure as seguintes variáveis no arquivo `.env`:

```env
# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-api-key-here

# Z-API WhatsApp Configuration
Z_API_URL=https://api.z-api.io
Z_API_TOKEN=your-z-api-token-here
Z_API_INSTANCE=your-z-api-instance-here
Z_API_KEY=your-z-api-key-here
NUMBER_BOT=5511999999999

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key-here
```

### 3. Deploy Automático

```bash
# Execute o script de deploy
./deploy.sh
```

## 🌐 Configuração do Domínio web.nerai.com.br

### 1. Configurar DNS

No painel do seu provedor de domínio, configure:

```
Tipo: A
Nome: web
Valor: IP_DA_SUA_VPS
TTL: 300
```

### 2. Configurar SSL com Let's Encrypt

```bash
# Instalar Certbot
sudo apt install certbot python3-certbot-nginx

# Parar o Nginx temporariamente
docker-compose stop nginx

# Gerar certificado SSL
sudo certbot certonly --standalone -d web.nerai.com.br

# Copiar certificados para o diretório correto
sudo cp /etc/letsencrypt/live/web.nerai.com.br/fullchain.pem ./ssl/
sudo cp /etc/letsencrypt/live/web.nerai.com.br/privkey.pem ./ssl/
sudo chown $USER:$USER ./ssl/*

# Reiniciar containers
docker-compose up -d
```

### 3. Configurar Renovação Automática do SSL

```bash
# Adicionar ao crontab
sudo crontab -e

# Adicione esta linha para renovar automaticamente a cada 2 meses:
0 0 1 */2 * certbot renew --quiet && docker-compose restart nginx
```

## 🔧 Configuração do Webhook no Z-API

1. Acesse o painel do Z-API
2. Vá em **Webhooks**
3. Configure:
   - **URL**: `https://web.nerai.com.br/webhook`
   - **Eventos**: Marque todos os eventos de mensagem
   - **Método**: POST

## ✅ Verificação do Deploy

### Teste os Endpoints

```bash
# Health check
curl https://web.nerai.com.br/health

# Deve retornar:
# {"service":"Planify Agent","status":"healthy","timestamp":"..."}
```

### Monitorar Logs

```bash
# Ver logs em tempo real
docker-compose logs -f planify-agent

# Ver logs do nginx
docker-compose logs -f nginx
```

## 🛠️ Comandos Úteis

### Gerenciar Containers

```bash
# Ver status
docker-compose ps

# Reiniciar aplicação
docker-compose restart planify-agent

# Reiniciar tudo
docker-compose restart

# Parar tudo
docker-compose down

# Rebuild e restart
docker-compose up --build -d
```

### Backup e Manutenção

```bash
# Backup dos logs
tar -czf backup-logs-$(date +%Y%m%d).tar.gz logs/

# Limpar logs antigos (manter últimos 7 dias)
find logs/ -name "*.log" -mtime +7 -delete

# Ver uso de espaço
docker system df
docker system prune -f  # Limpar containers/imagens não usadas
```

## 🔒 Segurança Implementada

- ✅ Rate limiting no webhook (10 requests/minuto)
- ✅ HTTPS obrigatório com SSL
- ✅ Headers de segurança configurados
- ✅ Container rodando com usuário não-root
- ✅ Firewall via nginx (apenas endpoints necessários)
- ✅ Logs de auditoria

## 🚨 Troubleshooting

### Problema: Container não inicia

```bash
# Verificar logs
docker-compose logs planify-agent

# Verificar arquivo .env
cat .env

# Rebuild do container
docker-compose down
docker-compose up --build -d
```

### Problema: SSL não funciona

```bash
# Verificar certificados
ls -la ssl/

# Testar nginx config
docker-compose exec nginx nginx -t

# Recriar certificados
sudo certbot delete --cert-name web.nerai.com.br
sudo certbot certonly --standalone -d web.nerai.com.br
```

### Problema: Webhook não recebe mensagens

1. Verifique se o domínio está resolvendo: `nslookup web.nerai.com.br`
2. Teste o endpoint: `curl https://web.nerai.com.br/health`
3. Verifique a configuração no Z-API
4. Monitore os logs: `docker-compose logs -f`

## 📊 Monitoramento

O sistema inclui:

- **Health Check**: `https://web.nerai.com.br/health`
- **Logs estruturados**: Todos os eventos são logados
- **Rate limiting**: Proteção contra spam
- **Métricas de container**: Via Docker stats

## 🔄 Atualizações

Para atualizar o código:

```bash
git pull origin main
docker-compose up --build -d
```

## 📞 Suporte

Para suporte, monitore os logs e verifique:

1. Status dos containers: `docker-compose ps`
2. Logs da aplicação: `docker-compose logs planify-agent`
3. Conectividade: `curl https://web.nerai.com.br/health`
4. Configuração do webhook no Z-API

---

**✨ Seu assistente financeiro está pronto para ajudar seus usuários a prosperarem!**
