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

for cmd in docker curl openssl; do
  if ! command -v $cmd &>/dev/null; then
    echo -e "${RED}Erro: '$cmd' não encontrado.${NC}"
    exit 1
  fi
done

if ! docker compose version &>/dev/null; then
  echo -e "${RED}Erro: 'docker compose' não encontrado. Atualize o Docker.${NC}"
  exit 1
fi

DOCKERHUB_USER="${SW_DOCKERHUB_USER:-jefvonmuhlen}"
VERSION="${SW_VERSION:-latest}"
COMPANY_NAME="${SW_COMPANY:-Minha Empresa}"
ADMIN_EMAIL="${SW_ADMIN_EMAIL:-admin@empresa.com}"
ADMIN_PASSWORD="${SW_ADMIN_PASSWORD:-}"
PORT="${SW_PORT:-80}"

if [ -z "$ADMIN_PASSWORD" ]; then
  echo -e "${RED}Erro: SW_ADMIN_PASSWORD não definida.${NC}"
  echo ""
  echo "Use:"
  echo ""
  echo "  SW_ADMIN_PASSWORD=suasenha \\"
  echo "  SW_ADMIN_EMAIL=admin@empresa.com \\"
  echo "  SW_COMPANY=\"Nome da Empresa\" \\"
  echo "  bash <(curl -fsSL $REPO_URL/install.sh)"
  echo ""
  exit 1
fi

DB_PASSWORD=$(openssl rand -hex 24)
JWT_SECRET=$(openssl rand -hex 48)

mkdir -p "$INSTALL_DIR"

echo "Baixando arquivos de configuração..."
curl -fsSL "$REPO_URL/docker-compose.prod.yml" -o "$INSTALL_DIR/docker-compose.yml"

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

echo "Baixando imagens e iniciando ServerWatch..."
cd "$INSTALL_DIR"
docker compose pull
docker compose up -d

SERVER_IP=$(curl -s --max-time 3 ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')

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
