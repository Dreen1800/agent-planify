#!/bin/bash

# Script de deploy para Planify Agent
# Execute este script na VPS após clonar o repositório

set -e

echo "🚀 Iniciando deploy do Planify Agent..."

# Verificar se Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Docker não encontrado. Instalando Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    sudo usermod -aG docker $USER
    echo "✅ Docker instalado. Você precisa fazer logout e login novamente."
    exit 1
fi

# Verificar se Docker Compose está instalado
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose não encontrado. Instalando..."
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# Verificar se arquivo .env existe
if [ ! -f .env ]; then
    echo "❌ Arquivo .env não encontrado!"
    echo "📝 Copie o arquivo env.template para .env e configure suas variáveis:"
    echo "   cp env.template .env"
    echo "   nano .env"
    exit 1
fi

# Criar diretórios necessários
echo "📁 Criando diretórios necessários..."
mkdir -p logs
mkdir -p ssl

# Parar containers existentes (se houver)
echo "🛑 Parando containers existentes..."
docker-compose down --remove-orphans || true

# Construir e iniciar containers
echo "🔨 Construindo e iniciando containers..."
docker-compose up --build -d

# Verificar status
echo "🔍 Verificando status dos containers..."
docker-compose ps

echo ""
echo "✅ Deploy concluído!"
echo ""
echo "📋 Próximos passos:"
echo "1. Configure seu domínio web.nerai.com.br para apontar para este servidor"
echo "2. Configure SSL com Let's Encrypt (veja instruções no README)"
echo "3. Configure o webhook no Z-API para: https://web.nerai.com.br/webhook"
echo "4. Teste o endpoint de saúde: https://web.nerai.com.br/health"
echo ""
echo "📊 Para monitorar logs:"
echo "   docker-compose logs -f planify-agent"
echo ""
echo "🔄 Para reiniciar:"
echo "   docker-compose restart"
echo ""
