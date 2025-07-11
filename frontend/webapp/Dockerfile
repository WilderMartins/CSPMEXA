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
COPY --from=builder /app/dist /usr/share/nginx/html

# Copia a configuração customizada do Nginx.
# Esta configuração é crucial para:
# 1. Lidar com client-side routing do React Router (`try_files`).
# 2. Fazer proxy reverso de chamadas /api/v1/* para o api_gateway_service.
COPY nginx.default.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
