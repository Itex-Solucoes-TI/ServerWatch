#!/bin/bash
set -e

INSTALL_DIR="/opt/serverwatch"
COMPOSE_FILE="$INSTALL_DIR/docker-compose.yml"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "================================================"
echo "       ServerWatch — Atualização"
echo "================================================"
echo ""

if [ ! -f "$COMPOSE_FILE" ]; then
  echo "Instalação não encontrada em $INSTALL_DIR. Execute install.sh primeiro."
  exit 1
fi

read -p "Versão para atualizar [latest]: " VERSION
VERSION="${VERSION:-latest}"

# Atualiza a versão no .env
sed -i "s/^VERSION=.*/VERSION=${VERSION}/" "$INSTALL_DIR/.env"

cd "$INSTALL_DIR"

echo "Baixando novas imagens..."
docker compose -f docker-compose.yml pull

echo "Reiniciando serviços..."
docker compose -f docker-compose.yml up -d

echo ""
echo -e "${GREEN}Atualização concluída! Versão: ${VERSION}${NC}"
echo ""

# Remove imagens antigas não utilizadas
docker image prune -f --filter "label=org.opencontainers.image.title=serverwatch*" 2>/dev/null || true
