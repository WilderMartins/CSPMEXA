# Usar a imagem oficial do Docker que já inclui o cliente e o compose v2
FROM docker:latest

# Instalar Python e pip
RUN apk add --no-cache python3 py3-pip

# Definir o diretório de trabalho no container
WORKDIR /app

# Copiar o arquivo de dependências e instalar
COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Copiar o resto do código do aplicativo
COPY . .

# Expor a porta que o Flask irá rodar
EXPOSE 8080

# Comando para rodar o aplicativo
CMD ["flask", "run", "--host=0.0.0.0", "--port=8080"]
