#!/bin/bash
set -e

REPO_URL="https://raw.githubusercontent.com/Itex-Solucoes-TI/ServerWatch/main"
INSTALL_DIR="/opt/serverwatch"
ENV_FILE="$INSTALL_DIR/.env"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "================================================"
echo "       ServerWatch — Instalação"
echo "================================================"
echo ""

# Verifica dependências
for cmd in docker curl openssl; do
  if ! command -v $cmd &>/dev/null; then
    echo -e "${RED}Erro: '$cmd' não encontrado. Instale e tente novamente.${NC}"
    exit 1
  fi
done

if ! docker compose version &>/dev/null; then
  echo -e "${RED}Erro: 'docker compose' não encontrado. Atualize o Docker.${NC}"
  exit 1
fi

# Lê do terminal mesmo quando executado via pipe (curl | bash)
exec < /dev/tty

echo -e "${YELLOW}Configure a instalação (Enter para usar o valor padrão):${NC}"
echo ""

read -p "Seu usuário do Docker Hub: " DOCKERHUB_USER
if [ -z "$DOCKERHUB_USER" ]; then
  echo -e "${RED}Usuário do Docker Hub é obrigatório.${NC}"
  exit 1
fi

read -p "Nome da empresa [Minha Empresa]: " COMPANY_NAME
COMPANY_NAME="${COMPANY_NAME:-Minha Empresa}"

read -p "Email do administrador [admin@empresa.com]: " ADMIN_EMAIL
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@empresa.com}"

while true; do
  read -s -p "Senha do administrador (mín. 6 caracteres): " ADMIN_PASSWORD
  echo ""
  if [ ${#ADMIN_PASSWORD} -ge 6 ]; then
    break
  fi
  echo -e "${RED}A senha precisa ter no mínimo 6 caracteres.${NC}"
done

read -p "Porta de acesso web [80]: " PORT
PORT="${PORT:-80}"

read -p "Versão a instalar [latest]: " VERSION
VERSION="${VERSION:-latest}"

# Gera secrets aleatórios
DB_PASSWORD=$(openssl rand -hex 24)
JWT_SECRET=$(openssl rand -hex 48)

# Cria diretório de instalação
mkdir -p "$INSTALL_DIR"

# Baixa o docker-compose de produção
echo ""
echo "Baixando arquivos de configuração..."
curl -fsSL "$REPO_URL/docker-compose.prod.yml" -o "$INSTALL_DIR/docker-compose.yml"

# Cria o .env com valores já resolvidos (sem variáveis aninhadas)
cat > "$ENV_FILE" << EOF
BACKEND_IMAGE=${DOCKERHUB_USER}/serverwatch-backend:${VERSION}
FRONTEND_IMAGE=${DOCKERHUB_USER}/serverwatch-frontend:${VERSION}
DB_PASSWORD=${DB_PASSWORD}
JWT_SECRET=${JWT_SECRET}
DEFAULT_COMPANY_NAME=${COMPANY_NAME}
DEFAULT_ADMIN_EMAIL=${ADMIN_EMAIL}
DEFAULT_ADMIN_PASSWORD=${ADMIN_PASSWORD}
PORT=${PORT}
CORS_ORIGINS=*
EOF

chmod 600 "$ENV_FILE"

# Sobe os serviços
echo "Baixando imagens e iniciando ServerWatch..."
cd "$INSTALL_DIR"
docker compose pull
docker compose up -d

SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  ServerWatch instalado com sucesso!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "  Acesso: http://${SERVER_IP}:${PORT}"
echo "  Email:  ${ADMIN_EMAIL}"
echo ""
echo -e "${YELLOW}  Arquivos em: $INSTALL_DIR${NC}"
echo ""
