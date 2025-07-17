# Fase 1: Build da aplicação React
FROM node:18-alpine AS builder
WORKDIR /app

# Argumento de build para a URL base da API
ARG VITE_API_BASE_URL_ARG=/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL_ARG

# Copiar apenas os arquivos de manifesto de dependência primeiro para aproveitar o cache do Docker
COPY package.json package-lock.json* ./
RUN npm install

# Copiar o restante dos arquivos fonte necessários para o build
COPY public ./public
COPY src ./src
COPY vite.config.ts .
COPY tsconfig.json .
COPY tsconfig.node.json .
COPY index.html .
COPY eslint.config.js .

# Executar o build
RUN npm run build

# Fase 2: Servir a aplicação com Nginx
FROM nginx:stable-alpine

# Copiar os arquivos estáticos do estágio de build
COPY --from=builder /app/dist /usr/share/nginx/html

# Copiar a configuração do Nginx
# Esta configuração deve lidar com o proxy reverso para a API e servir os arquivos estáticos.
# A configuração de SSL (certificados) deve ser gerenciada fora do Dockerfile,
# por exemplo, montando volumes no docker-compose.yml ou usando um Ingress no Kubernetes.
COPY nginx.default.conf /etc/nginx/conf.d/default.conf

# Expõe a porta 80 (a porta 443 será gerenciada pelo Nginx se os certificados forem fornecidos)
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
