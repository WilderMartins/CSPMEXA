FROM alpine:latest

# Instalar curl, jq, bash e openssl
RUN apk --no-cache add curl jq bash openssl

# Copiar o script de setup
COPY setup-vault.sh /usr/local/bin/setup-vault.sh
RUN chmod +x /usr/local/bin/setup-vault.sh

# Definir o comando de entrada
ENTRYPOINT ["/usr/local/bin/setup-vault.sh"]
