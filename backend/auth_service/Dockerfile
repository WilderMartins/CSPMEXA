FROM python:3.9-slim

WORKDIR /app

# Instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o código da aplicação
COPY ./app /app

# Comando para rodar a aplicação
EXPOSE 8000 # Expor a porta que o uvicorn (ou python app/main.py) vai usar
# O comando CMD será definido no docker-compose.yml para flexibilidade (ex: reload em dev)
# Se fosse definir aqui, seria algo como:
# CMD ["python", "/app/app/main.py"]
# ou para produção sem reload:
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
