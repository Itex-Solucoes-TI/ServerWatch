# ServerWatch

Sistema de monitoramento de infraestrutura multi-empresa. Gerencia servidores, containers Docker (local e remoto via TCP, TLS ou SSH), roteadores, topologia de rede, health checks e notificações. Controle de acesso por empresa e perfil (Admin, Operador, Visualizador).

## Desenvolvimento local (Docker)

```bash
docker compose -f docker-compose.yml up -d --build
```

Acesse http://localhost:8080 (frontend) — backend em :8000.

**Login:** admin@empresa.com / admin123

## Deploy produção

```bash
docker compose -f docker-compose.prod.yml up -d
```

## Dev com frontend local (Vite)

1. Subir Postgres e backend:
```bash
docker compose -f docker-compose.yml up -d postgres backend
```

2. Frontend:
```bash
cd frontend && npm run dev
```

Acesse http://localhost:5173.

3. Variáveis: copie `.env.example` para `.env` se necessário.

## Docker — Monitorar containers

Configure servidores em Servidores → Docker host (local, TCP, TLS ou SSH). Sincronização automática a cada 30 segundos.
