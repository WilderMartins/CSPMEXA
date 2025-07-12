#!/bin/bash

# Este script é o ponto de entrada para o container do auth_service.
# Ele garante que as migrações do banco de dados sejam aplicadas antes de iniciar a aplicação.

# O 'set -e' garante que o script sairá imediatamente se um comando falhar.
set -e

echo "Ponto de entrada do Auth Service iniciado..."

# 1. Aplicar migrações do Alembic
# O comando 'alembic upgrade head' atualiza o schema do banco de dados para a versão mais recente.
echo "Aplicando migrações do banco de dados..."
alembic upgrade head
echo "Migrações do banco de dados aplicadas com sucesso."

# 2. Iniciar a aplicação principal
# O "$@" executa o comando que foi passado como argumento para este script.
# No nosso docker-compose.yml, este será "python /app/app/main.py".
echo "Iniciando a aplicação principal..."
exec "$@"
