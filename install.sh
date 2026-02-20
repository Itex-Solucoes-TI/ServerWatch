#!/bin/bash
set -e

REPO_URL="https://raw.githubusercontent.com/Itex-Solucoes-TI/ServerWatch/main"
INSTALL_DIR="/opt/serverwatch"
COMPOSE_FILE="$INSTALL_DIR/docker-compose.yml"
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
for cmd in docker curl; do
  if ! command -v $cmd &>/dev/null; then
    echo -e "${RED}Erro: '$cmd' não encontrado. Instale e tente novamente.${NC}"
    exit 1
  fi
done

if ! docker compose version &>/dev/null; then
  echo -e "${RED}Erro: 'docker compose' não encontrado. Atualize o Docker.${NC}"
  exit 1
fi

# Coleta configurações
echo -e "${YELLOW}Configure a instalação (Enter para usar o valor padrão):${NC}"
echo ""

read -p "Nome da empresa [Minha Empresa]: " COMPANY_NAME
COMPANY_NAME="${COMPANY_NAME:-Minha Empresa}"

read -p "Email do administrador [admin@empresa.com]: " ADMIN_EMAIL
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@empresa.com}"

while true; do
  read -s -p "Senha do administrador: " ADMIN_PASSWORD
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

read -p "Seu usuário do Docker Hub [itex]: " DOCKERHUB_USER
DOCKERHUB_USER="${DOCKERHUB_USER:-itex}"

# Gera secrets aleatórios
DB_PASSWORD=$(openssl rand -hex 24)
JWT_SECRET=$(openssl rand -hex 48)

# Cria diretório de instalação
mkdir -p "$INSTALL_DIR"

# Baixa o docker-compose de produção
echo ""
echo "Baixando arquivos de configuração..."
curl -fsSL "$REPO_URL/docker-compose.prod.yml" -o "$COMPOSE_FILE"

# Cria o .env
cat > "$ENV_FILE" << EOF
DOCKER_IMAGE_BACKEND=${DOCKERHUB_USER}/serverwatch-backend
DOCKER_IMAGE_FRONTEND=${DOCKERHUB_USER}/serverwatch-frontend
VERSION=${VERSION}
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
echo "Iniciando ServerWatch..."
cd "$INSTALL_DIR"
docker compose -f docker-compose.yml pull
docker compose -f docker-compose.yml up -d

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  ServerWatch instalado com sucesso!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "  Acesso: http://$(curl -s ifconfig.me 2>/dev/null || echo 'IP_DO_SERVIDOR'):${PORT}"
echo "  Email:  ${ADMIN_EMAIL}"
echo ""
echo -e "${YELLOW}  Guarde as credenciais em local seguro.${NC}"
echo "  Arquivos em: $INSTALL_DIR"
echo ""
