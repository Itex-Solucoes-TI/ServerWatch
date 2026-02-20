# ServerWatch

Sistema de monitoramento de infraestrutura multi-empresa. Gerencia servidores, containers Docker (local e remoto via TCP, TLS ou SSH), roteadores, topologia de rede, health checks e notificações. Controle de acesso por empresa e perfil (Admin, Operador, Visualizador).

## Deploy completo

```bash
docker compose up -d
```

Acesse http://localhost (porta 80).

**Login padrão:** admin@empresa.com / admin123

## Desenvolvimento local

1. Subir PostgreSQL e backend:
```bash
docker compose up -d postgres backend
```

2. Frontend (Vite):
```bash
cd frontend && npm run dev
```

Acesse http://localhost:5173. O proxy redireciona /api para o backend na porta 8000.

3. Variáveis: copie `.env.example` para `.env` e ajuste se necessário.

## Docker — Monitorar containers

Configure servidores em Servidores → Docker host (local, TCP, TLS ou SSH). Sincronização automática a cada 30 segundos.
