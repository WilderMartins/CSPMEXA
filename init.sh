#!/bin/bash

# Cores para o output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# --- 1. Verificar se o Docker está em execução ---
echo "Verificando se o Docker está em execução..."
if ! docker info > /dev/null 2>&1; then
  echo -e "${YELLOW}Erro: O Docker não parece estar em execução.${NC}"
  echo "Por favor, inicie o Docker e tente novamente."
  exit 1
fi
echo -e "${GREEN}Docker está ativo.${NC}"

# --- 2. Verificar o arquivo de configuração .env ---
if [ ! -f .env ]; then
  echo -e "${YELLOW}Arquivo de configuração '.env' não encontrado.${NC}"
  echo "Copiando de '.env.example' para '.env'..."
  cp .env.example .env
  echo -e "${GREEN}Arquivo '.env' criado com sucesso.${NC}"
  echo ""
  echo -e "${YELLOW}AÇÃO NECESSÁRIA:${NC} O arquivo '.env' foi criado."
  echo "Você precisará preenchê-lo com as credenciais do Vault após a primeira execução."
  echo "Continue com a inicialização por enquanto."
else
  echo -e "${GREEN}Arquivo '.env' encontrado.${NC}"
fi

# --- 3. Iniciar o Vault para gerar as credenciais ---
echo ""
echo "Iniciando o Vault para gerar as credenciais AppRole..."
# Usamos 'up -d' para rodar em background e '--build' para garantir que as mudanças no Dockerfile do vault-setup sejam aplicadas
docker-compose up -d --build vault vault-setup

echo ""
echo "Aguardando o script de setup do Vault concluir..."
# O 'vault-setup' é um serviço que roda e sai. Podemos esperar que ele pare.
# O 'docker wait' espera o container parar e retorna o exit code.
if [ "$(docker wait cspmexa-vault-setup)" -ne 0 ]; then
    echo -e "${YELLOW}O script de setup do Vault encontrou um erro. Verifique os logs:${NC}"
    docker-compose logs vault-setup
    exit 1
fi

echo -e "${GREEN}Setup do Vault concluído. As credenciais foram impressas nos logs.${NC}"
echo "--------------------------------------------------"
echo -e "${YELLOW}AÇÃO NECESSÁRIA:${NC}"
echo "Copie as credenciais AppRole dos logs abaixo e cole-as no seu arquivo '.env'."
echo "Execute o seguinte comando para ver os logs e copiar as credenciais:"
echo ""
echo -e "${GREEN}docker-compose logs vault-setup${NC}"
echo ""
read -p "Após preencher o .env, pressione [Enter] para iniciar todos os outros serviços..."

# --- 4. Iniciar todos os serviços da aplicação ---
echo ""
echo "Iniciando todos os serviços da aplicação..."
# Usamos '--remove-orphans' para remover o container do vault-setup que já rodou
docker-compose up -d --build --remove-orphans app

echo -e "${GREEN}Todos os serviços foram iniciados em modo detached (-d).${NC}"
echo "Para ver os logs de todos os serviços, use o comando: ${GREEN}docker-compose logs -f${NC}"
echo "Para parar os serviços, use o comando: ${GREEN}docker-compose down${NC}"
