FROM python:3.9-slim

WORKDIR /app

# Instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o código da aplicação
COPY ./app /app

# EXPOSE 8001 # Porta diferente do auth-service
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
