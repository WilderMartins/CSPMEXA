FROM python:3.9-slim

WORKDIR /app

# Instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o código da aplicação
COPY ./app /app
COPY alembic.ini /app/alembic.ini
COPY alembic/ /app/alembic

# Copiar e configurar o ponto de entrada
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Expor a porta que o serviço usa
EXPOSE 8000

# Definir o ponto de entrada
ENTRYPOINT ["/app/entrypoint.sh"]

# O CMD padrão pode ser definido aqui, mas será sobrescrito pelo docker-compose.
# Isso é útil para rodar o container de forma independente.
CMD ["python", "/app/main.py"]
