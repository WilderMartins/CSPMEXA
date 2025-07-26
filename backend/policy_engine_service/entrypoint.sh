#!/bin/bash
set -e

# Executa as migrações do Alembic
alembic upgrade head

# Executa o comando principal do contêiner (o CMD do Dockerfile)
exec "$@"
