FROM python:3.9-slim

WORKDIR /app

# Instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o código da aplicação
COPY ./app /app

# Comando para rodar a aplicação (será ajustado no main.py)
# EXPOSE 8000 # Expor a porta que o uvicorn vai usar
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
