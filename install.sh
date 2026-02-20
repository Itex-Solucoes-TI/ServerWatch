#!/bin/bash
set -e

# Se estiver sendo executado via pipe (curl | bash), baixa e re-executa
if [ -p /dev/stdin ]; then
  TMP=$(mktemp /tmp/sw-install.XXXXXX.sh)
  cat > "$TMP"
  bash "$TMP"
  rm -f "$TMP"
  exit $?
fi

REPO_URL="https://raw.githubusercontent.com/Itex-Solucoes-TI/ServerWatch/main"
INSTALL_DIR="/opt/serverwatch"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

echo ""
echo "================================================"
echo "       ServerWatch — Instalação"
echo "================================================"
echo ""

for cmd in curl openssl; do
  if ! command -v $cmd &>/dev/null; then
    echo -e "${RED}Erro: '$cmd' não encontrado. Instale e tente novamente.${NC}"
    exit 1
  fi
done

if ! command -v docker &>/dev/null; then
  echo "Docker não encontrado. Instalando..."
  curl -fsSL https://get.docker.com | sh
  systemctl enable docker
  systemctl start docker
  echo "Docker instalado."
fi

if ! docker compose version &>/dev/null; then
  echo -e "${RED}Erro: 'docker compose' não encontrado. Atualize o Docker para v2.${NC}"
  exit 1
fi

DB_PASSWORD=$(openssl rand -hex 24)
JWT_SECRET=$(openssl rand -hex 48)

mkdir -p "$INSTALL_DIR"

echo "Baixando arquivos de configuração..."
curl -fsSL "$REPO_URL/docker-compose.prod.yml" -o "$INSTALL_DIR/docker-compose.yml"

cat > "$INSTALL_DIR/.env" << EOF
BACKEND_IMAGE=jefvonmuhlen/serverwatch-backend:latest
FRONTEND_IMAGE=jefvonmuhlen/serverwatch-frontend:latest
DB_PASSWORD=${DB_PASSWORD}
JWT_SECRET=${JWT_SECRET}
DEFAULT_COMPANY_NAME=Minha Empresa
DEFAULT_ADMIN_EMAIL=admin@empresa.com
DEFAULT_ADMIN_PASSWORD=admin123
PORT=80
CORS_ORIGINS=*
EOF

chmod 600 "$INSTALL_DIR/.env"

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
echo "  Acesso: http://${SERVER_IP}"
echo "  Email:  admin@empresa.com"
echo "  Senha:  admin123"
echo ""
echo "  Troque a senha após o primeiro acesso."
echo ""
