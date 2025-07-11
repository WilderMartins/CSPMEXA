FROM python:3.9-slim

WORKDIR /app

# Instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o código da aplicação
COPY ./app /app

EXPOSE 8001
# CMD definido no docker-compose.yml
# CMD ["python", "/app/app/main.py"]
