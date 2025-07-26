FROM python:3.9-slim

WORKDIR /app

# Instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o código da aplicação
COPY ./app /app
COPY alembic.ini /app/alembic.ini
COPY alembic/ /app/alembic

# Expor a porta que o serviço usa
EXPOSE 8000

# O CMD padrão pode ser definido aqui, mas será sobrescrito pelo docker-compose.
# Isso é útil para rodar o container de forma independente.
CMD ["python", "/app/app/main.py"]
