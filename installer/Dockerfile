# Usar uma imagem Python leve
FROM python:3.9-slim

# Instalar o cliente Docker
RUN apt-get update && apt-get install -y docker.io

# Definir o diretório de trabalho no container
WORKDIR /app

# Copiar o arquivo de dependências e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o resto do código do aplicativo
COPY . .

# Expor a porta que o Flask irá rodar
EXPOSE 8080

# Comando para rodar o aplicativo
CMD ["flask", "run", "--host=0.0.0.0", "--port=8080"]
