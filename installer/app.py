import os
import secrets
import subprocess
from flask import Flask, render_template, request, redirect, flash

# Inicializa o aplicativo Flask
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Chave secreta para mensagens flash

# Caminho onde o arquivo .env será criado (na raiz do projeto)
ENV_FILE_PATH = os.path.join('/app/config', '.env')

@app.route('/')
def index():
    """Exibe a página inicial do assistente de instalação."""
    # Verifica se o .env já existe. Se sim, talvez a instalação já foi feita.
    if os.path.exists(ENV_FILE_PATH):
        flash("Um arquivo .env já existe. Se você continuar, ele será sobrescrito.", "warning")
    return render_template('index.html')

@app.route('/install', methods=['POST'])
def install():
    """Processa os dados do formulário, cria o .env e inicia os serviços."""

    # Coleta os dados do formulário
    form_data = request.form.to_dict()

    # --- Geração de Segredos ---
    # Gera uma senha forte para o banco de dados se não for fornecida
    db_password = form_data.get('AUTH_DB_PASSWORD')
    if not db_password:
        db_password = secrets.token_urlsafe(16)
        flash("Uma nova senha segura para o banco de dados foi gerada.", "info")

    # Gera a chave secreta JWT, que é crucial para a segurança
    jwt_secret_key = secrets.token_hex(32)

    # Define o conteúdo do arquivo .env
    env_content = f"""
# Arquivo gerado automaticamente pelo Assistente de Instalação do CSPMEXA

# --- Configurações de Banco de Dados (PostgreSQL) ---
AUTH_DB_USER={form_data.get('AUTH_DB_USER', 'cspmexa_user')}
AUTH_DB_PASSWORD={db_password}
AUTH_DB_NAME={form_data.get('AUTH_DB_NAME', 'cspmexa_db')}
AUTH_DB_EXPOSED_PORT=5433

# --- Portas Expostas no Host para os Serviços ---
API_GATEWAY_PORT={form_data.get('API_GATEWAY_PORT', 8050)}
FRONTEND_PORT={form_data.get('FRONTEND_PORT', 3000)}
# Outras portas de serviço usarão o padrão do docker-compose se não definidas aqui
# AUTH_SERVICE_PORT=8000
# COLLECTOR_SERVICE_PORT=8001
# POLICY_ENGINE_SERVICE_PORT=8002

# --- Configurações de JWT (JSON Web Token) ---
JWT_SECRET_KEY={jwt_secret_key}
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# --- Configurações de OAuth do Google (para login no CSPMEXA) ---
GOOGLE_CLIENT_ID={form_data.get('GOOGLE_CLIENT_ID', '')}
GOOGLE_CLIENT_SECRET={form_data.get('GOOGLE_CLIENT_SECRET', '')}

# --- Configurações de TOTP (para MFA no CSPMEXA) ---
TOTP_ISSUER_NAME={form_data.get('TOTP_ISSUER_NAME', 'CSPMEXA')}

# --- Modo de Desenvolvimento ---
# Deixar desabilitado por padrão para instalações "finais"
DEBUG_MODE=false

# --- Outras Configurações (com valores padrão) ---
# Adicione outras variáveis com valores padrão aqui se necessário no futuro
"""

    # Escreve o conteúdo no arquivo .env
    try:
        with open(ENV_FILE_PATH, 'w') as f:
            f.write(env_content.strip())
    except IOError as e:
        flash(f"Erro Crítico: Não foi possível criar o arquivo .env. Verifique as permissões. Erro: {e}", "danger")
        return redirect('/')

    # Inicia os outros containers usando o perfil 'app'
    try:
        # Usamos 'docker' em vez de 'docker-compose' ou 'docker compose' porque estamos
        # executando de dentro de um container que tem o binário do docker (via docker.sock).
        # Usar 'compose' pode exigir a instalação do plugin compose dentro deste container.
        # O comando 'up' com --profile é a forma moderna e correta.
        # NOTA: O comando correto para a v2 do compose é `docker compose`, não `docker-compose`.
        # Vamos usar o comando completo para garantir.
        cmd = ["docker", "compose", "--profile", "app", "up", "--build", "-d"]

        # O diretório de trabalho deve ser a raiz do projeto onde está o docker-compose.yml
        working_dir = '/app/config'

        subprocess.run(cmd, check=True, cwd=working_dir, capture_output=True, text=True)

        # Passo 2: Executar a migração inicial do banco de dados no auth_service
        print("Executando migração inicial do banco de dados...")
        migrate_cmd = ["docker", "compose", "exec", "auth_service", "alembic", "upgrade", "head"]
        subprocess.run(migrate_cmd, check=True, cwd=working_dir, capture_output=True, text=True)
        print("Migração inicial concluída.")

        # Passo 3: Redirecionar para a página de sucesso
        frontend_port = form_data.get('FRONTEND_PORT', '3000')
        return redirect(f'/success?frontend_port={frontend_port}')

    except subprocess.CalledProcessError as e:
        # Se o comando falhar, mostra o erro para o usuário
        error_message = f"Falha ao iniciar os serviços do aplicativo. Verifique os logs do Docker.<br><pre>{e.stdout}{e.stderr}</pre>"
        flash(error_message, "danger")
        return redirect('/')
    except FileNotFoundError:
        flash("Erro: O comando 'docker' não foi encontrado. O socket do Docker foi montado corretamente?", "danger")
        return redirect('/')

@app.route('/success')
def success():
    """Exibe uma mensagem de sucesso mais útil após a instalação."""
    frontend_port = request.args.get('frontend_port', '3000')

    # Obtém o IP do host a partir do cabeçalho da requisição, se disponível
    host_ip = request.host.split(':')[0]

    # Monta a URL de acesso, usando o IP detectado ou um placeholder
    access_url = f"http://{host_ip}:{frontend_port}"

    return f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Instalação Concluída</title>
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f4f4f9; color: #333; text-align: center; padding: 50px; }}
            .container {{ max-width: 600px; margin: auto; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            h1 {{ color: #28a745; }}
            a {{ color: #0056b3; font-weight: bold; font-size: 1.2em; }}
            p {{ margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Instalação Concluída com Sucesso!</h1>
            <p>O CSPMEXA foi configurado e todos os serviços estão sendo iniciados em segundo plano.</p>
            <p>Pode levar um ou dois minutos para que o sistema esteja totalmente operacional.</p>
            <p>Quando estiver pronto, clique no link abaixo para acessar a aplicação:</p>
            <a href="{access_url}" target="_blank">{access_url}</a>
            <p><small>Se o link não funcionar, certifique-se de que o endereço de IP está correto e que a porta <strong>{frontend_port}</strong> está acessível.</small></p>
        </div>
    </body>
    </html>
    """

if __name__ == '__main__':
    # O comando `flask run` usará estas configurações.
    # O host 0.0.0.0 torna o servidor acessível de fora do container.
    app.run(host='0.0.0.0', port=8080)
