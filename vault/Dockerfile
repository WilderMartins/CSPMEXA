FROM alpine:latest

# Instala ferramentas necessárias:
# curl: para fazer requisições HTTP para a API do Vault
# jq: para processar respostas JSON do Vault
# bash: para rodar o script de setup com mais facilidade que o 'sh' padrão
RUN apk add --no-cache curl jq bash

WORKDIR /app

# Copia o script de setup para o container
COPY setup-vault.sh .

# Dá permissão de execução para o script
RUN chmod +x setup-vault.sh

# O comando que será executado quando o container iniciar
CMD ["./setup-vault.sh"]
