# Fase 1: Build da aplicação React
FROM node:18-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
RUN npm run build

# Fase 2: Servir a aplicação com Nginx
FROM nginx:stable-alpine
COPY --from=builder /app/dist /usr/share/nginx/html

# Opcional: Copiar uma configuração customizada do Nginx se necessário
# Para lidar com client-side routing no Nginx, você geralmente precisa
# de uma configuração que redirecione todas as requisições não encontradas para /index.html.
# Exemplo de nginx.conf:
# server {
#   listen 80;
#   server_name localhost;
#
#   root /usr/share/nginx/html;
#   index index.html index.htm;
#
#   location / {
#     try_files $uri $uri/ /index.html;
#   }
#
#   # Proxy para o backend API se o Nginx também servir como gateway (não é nosso caso aqui, temos um API Gateway separado)
#   # location /api/ {
#   #   proxy_pass http://api-gateway-service:8050; # URL do seu API Gateway
#   #   proxy_set_header Host $host;
#   #   proxy_set_header X-Real-IP $remote_addr;
#   #   proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
#   #   proxy_set_header X-Forwarded-Proto $scheme;
#   # }
# }
# Se usar um nginx.conf customizado, descomente a linha abaixo:
# COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
