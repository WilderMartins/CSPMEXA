#!/bin/bash

# --- Esperar o Vault ficar disponível ---
echo "Aguardando o Vault iniciar..."
while ! curl -s -f http://vault:8200/v1/sys/health; do
    sleep 1
done
echo "Vault está pronto!"

# --- Habilitar o motor de segredos KV v2 ---
# Usamos o KV v2 porque ele oferece versionamento de segredos.
echo "Habilitando o motor de segredos KV v2 em 'secret/'..."
curl -s --header "X-Vault-Token: $VAULT_TOKEN" --request POST \
     --data '{"type": "kv-v2"}' \
     http://vault:8200/v1/sys/mounts/secret || echo "Motor 'secret' já pode estar habilitado."

# --- Escrever segredos no Vault ---
# Em um cenário real, estes valores viriam de um local seguro, não hardcoded.
# Para este projeto, vamos definir valores padrão sensíveis.

# Segredos do Banco de Dados
DB_USER=${VAULT_DB_USER:-cspmexa_user}
DB_PASSWORD=${VAULT_DB_PASSWORD:-a_very_secure_password_from_vault}
echo "Escrevendo segredos do banco de dados em 'secret/database'..."
curl -s --header "X-Vault-Token: $VAULT_TOKEN" --request POST \
     --data "{\"data\": {\"user\": \"$DB_USER\", \"password\": \"$DB_PASSWORD\"}}" \
     http://vault:8200/v1/secret/data/database

# Segredo JWT (geramos um novo e seguro)
JWT_SECRET=${VAULT_JWT_SECRET:-$(openssl rand -hex 32)}
echo "Gerando e escrevendo novo JWT_SECRET_KEY em 'secret/jwt'..."
curl -s --header "X-Vault-Token: $VAULT_TOKEN" --request POST \
     --data "{\"data\": {\"key\": \"$JWT_SECRET\"}}" \
     http://vault:8200/v1/secret/data/jwt

# Segredos do Google OAuth (para login)
GOOGLE_CLIENT_ID=${VAULT_GOOGLE_CLIENT_ID:-COLOQUE_SEU_GOOGLE_CLIENT_ID_AQUI}
GOOGLE_CLIENT_SECRET=${VAULT_GOOGLE_CLIENT_SECRET:-COLOQUE_SEU_GOOGLE_CLIENT_SECRET_AQUI}
echo "Escrevendo placeholders para Google OAuth em 'secret/google_oauth'..."
curl -s --header "X-Vault-Token: $VAULT_TOKEN" --request POST \
     --data "{\"data\": {\"client_id\": \"$GOOGLE_CLIENT_ID\", \"client_secret\": \"$GOOGLE_CLIENT_SECRET\"}}" \
     http://vault:8200/v1/secret/data/google_oauth

# Segredos de SMTP (para notificações por email)
echo "Escrevendo placeholders para SMTP em 'secret/smtp'..."
curl -s --header "X-Vault-Token: $VAULT_TOKEN" --request POST \
     --data '{"data": {"host": "", "port": "587", "user": "", "password": ""}}' \
     http://vault:8200/v1/secret/data/smtp

# Segredos para Provedores de Nuvem (placeholders)
# O ideal é ter um caminho por provedor.
echo "Escrevendo placeholders para credenciais de nuvem..."
curl -s --header "X-Vault-Token: $VAULT_TOKEN" --request POST \
     --data '{"data": {"aws_access_key_id": "", "aws_secret_access_key": ""}}' \
     http://vault:8200/v1/secret/data/aws_credentials

curl -s --header "X-Vault-Token: $VAULT_TOKEN" --request POST \
     --data '{"data": {"azure_client_id": "", "azure_client_secret": "", "azure_tenant_id": "", "azure_subscription_id": ""}}' \
     http://vault:8200/v1/secret/data/azure_credentials

echo "--- Configuração do Vault concluída! ---"

# O script irá sair, e o container 'vault-setup' será encerrado.
# Isso é esperado e normal.
exit 0
