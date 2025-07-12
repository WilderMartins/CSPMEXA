# Fase 1: Build da aplicação React
FROM node:18-alpine AS builder
WORKDIR /app

# Argumento de build para a URL base da API, com um valor padrão.
# Este valor será usado pelo Vite durante o build se injetado via ENV.
ARG VITE_API_BASE_URL_ARG=/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL_ARG

COPY package.json package-lock.json* ./
RUN npm install
COPY . .
# O comando `npm run build` usará a ENV VITE_API_BASE_URL se o vite.config.ts
# estiver configurado para lê-la (ex: via `loadEnv` e `define`).
RUN npm run build

# Fase 2: Servir a aplicação com Nginx
FROM nginx:stable-alpine

# Instala openssl, gera certificados autoassinados e depois remove openssl
RUN apk add --no-cache openssl && \
    mkdir -p /etc/ssl/private && \
    mkdir -p /etc/ssl/certs && \
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/nginx-selfsigned.key \
    -out /etc/ssl/certs/nginx-selfsigned.crt \
    -subj "/C=BR/ST=SaoPaulo/L=SaoPaulo/O=CSPMEXA/OU=Development/CN=localhost" && \
    apk del openssl

COPY --from=builder /app/dist /usr/share/nginx/html

# Copia a configuração customizada do Nginx que agora inclui SSL e proxy reverso.
COPY nginx.default.conf /etc/nginx/conf.d/default.conf

# Expõe as portas HTTP e HTTPS
EXPOSE 80
EXPOSE 443

CMD ["nginx", "-g", "daemon off;"]
