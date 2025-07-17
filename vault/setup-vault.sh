#!/bin/bash
set -e

# Função para esperar o Vault ficar disponível
wait_for_vault() {
  echo "Aguardando o Vault iniciar..."
  until curl -s -f http://vault:8200/v1/sys/health; do
    sleep 1
  done
  echo "Vault está pronto!"
}

# Função para fazer requisições à API do Vault
vault_request() {
  method=$1
  path=$2
  data=$3
  curl -s --header "X-Vault-Token: $VAULT_TOKEN" --request "$method" --data "$data" "http://vault:8200/v1/$path"
}

# Habilitar o motor de segredos KV v2
enable_kv_secrets() {
  echo "Habilitando o motor de segredos KV v2 em 'secret/'..."
  vault_request POST sys/mounts/secret '{"type": "kv-v2"}' || echo "Motor 'secret' já pode estar habilitado."
}

# Escrever os segredos no Vault
write_secrets() {
  echo "Escrevendo segredos no Vault..."
  # Segredos do Banco de Dados
  DB_USER=${VAULT_DB_USER:-cspmexa_user}
  DB_PASSWORD=${VAULT_DB_PASSWORD:-a_very_secure_password_from_vault}
  vault_request POST secret/data/database "{\"data\": {\"user\": \"$DB_USER\", \"password\": \"$DB_PASSWORD\"}}"

  # Segredo JWT
  JWT_SECRET=${VAULT_JWT_SECRET:-$(openssl rand -hex 32)}
  vault_request POST secret/data/jwt "{\"data\": {\"key\": \"$JWT_SECRET\"}}"

  # Outros segredos (placeholders)
  vault_request POST secret/data/google_oauth '{"data": {"client_id": "placeholder", "client_secret": "placeholder"}}'
  vault_request POST secret/data/smtp '{"data": {"host": "", "port": "587", "user": "", "password": ""}}'
  vault_request POST secret/data/aws_credentials '{"data": {"aws_access_key_id": "", "aws_secret_access_key": ""}}'
  vault_request POST secret/data/azure_credentials '{"data": {"azure_client_id": "", "azure_client_secret": "", "azure_tenant_id": "", "azure_subscription_id": ""}}'
}

# Habilitar e configurar a autenticação AppRole
setup_approle() {
  echo "Habilitando a autenticação AppRole..."
  vault_request POST sys/auth/approle '{"type": "approle"}' || echo "Autenticação AppRole já pode estar habilitada."

  # Políticas
  echo "Criando políticas..."
  vault_request POST sys/policy/auth-service-policy '{"policy": "path \"secret/data/database\" { capabilities = [\"read\"] } \n path \"secret/data/jwt\" { capabilities = [\"read\"] } \n path \"secret/data/google_oauth\" { capabilities = [\"read\"] }"}'
  vault_request POST sys/policy/collector-service-policy '{"policy": "path \"secret/data/aws_credentials\" { capabilities = [\"read\"] } \n path \"secret/data/azure_credentials\" { capabilities = [\"read\"] }"}'
  vault_request POST sys/policy/notification-service-policy '{"policy": "path \"secret/data/smtp\" { capabilities = [\"read\"] }"}'
  # O API Gateway e o Policy Engine não precisam de segredos por enquanto, mas podemos criar políticas vazias se necessário.

  # Criar AppRoles e obter RoleIDs
  echo "Criando AppRoles..."
  AUTH_ROLE_ID=$(vault_request GET auth/approle/role/auth-service/role-id | jq -r .data.role_id)
  COLLECTOR_ROLE_ID=$(vault_request GET auth/approle/role/collector-service/role-id | jq -r .data.role_id)
  NOTIFICATION_ROLE_ID=$(vault_request GET auth/approle/role/notification-service/role-id | jq -r .data.role_id)

  # Criar SecretIDs para os AppRoles
  echo "Criando SecretIDs..."
  AUTH_SECRET_ID=$(vault_request POST auth/approle/role/auth-service/secret-id '{}' | jq -r .data.secret_id)
  COLLECTOR_SECRET_ID=$(vault_request POST auth/approle/role/collector-service/secret-id '{}' | jq -r .data.secret_id)
  NOTIFICATION_SECRET_ID=$(vault_request POST auth/approle/role/notification-service/secret-id '{}' | jq -r .data.secret_id)

  echo "--------------------------------------------------"
  echo "Credenciais AppRole geradas. Adicione ao seu .env:"
  echo ""
  echo "# Credenciais para o auth_service"
  echo "AUTH_SERVICE_VAULT_ROLE_ID=$AUTH_ROLE_ID"
  echo "AUTH_SERVICE_VAULT_SECRET_ID=$AUTH_SECRET_ID"
  echo ""
  echo "# Credenciais para o collector_service"
  echo "COLLECTOR_SERVICE_VAULT_ROLE_ID=$COLLECTOR_ROLE_ID"
  echo "COLLECTOR_SERVICE_VAULT_SECRET_ID=$COLLECTOR_SECRET_ID"
  echo ""
  echo "# Credenciais para o notification_service"
  echo "NOTIFICATION_SERVICE_VAULT_ROLE_ID=$NOTIFICATION_ROLE_ID"
  echo "NOTIFICATION_SERVICE_VAULT_SECRET_ID=$NOTIFICATION_SECRET_ID"
  echo "--------------------------------------------------"
}

# Função principal
main() {
  wait_for_vault
  enable_kv_secrets
  write_secrets
  setup_approle
  echo "--- Configuração do Vault concluída! ---"
  exit 0
}

main
