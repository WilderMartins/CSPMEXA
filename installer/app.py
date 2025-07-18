import os
import re
import secrets
import subprocess
import time
from flask import Flask, render_template, request, redirect, flash

# Inicializa o aplicativo Flask
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Caminho onde o arquivo .env será criado (na raiz do projeto)
ENV_FILE_PATH = os.path.join('/app/config', '.env')
DOCKER_COMPOSE_YML_PATH = '/app/config'

def run_docker_command(command, capture=True):
    """Helper para executar comandos Docker Compose."""
    # Garante que o comando comece com 'docker compose'
    if command[0] == "docker" and command[1] != "compose":
        full_command = ["docker", "compose"] + command[1:]
    elif command[0] != "docker":
        full_command = ["docker", "compose"] + command
    else:
        full_command = command

    try:
        if capture:
            result = subprocess.run(
                full_command,
                check=True,
                cwd=DOCKER_COMPOSE_YML_PATH,
                capture_output=True,
                text=True
            )
            return result.stdout, result.stderr
        else:
            subprocess.run(
                full_command,
                check=True,
                cwd=DOCKER_COMPOSE_YML_PATH
            )
            return "", ""
    except subprocess.CalledProcessError as e:
        error_message = f"Comando falhou: {' '.join(full_command)}\n"
        error_message += f"Stdout: {e.stdout}\n"
        error_message += f"Stderr: {e.stderr}"
        raise RuntimeError(error_message)
    except FileNotFoundError:
        raise RuntimeError(f"Comando 'docker' não encontrado. O Docker está instalado e no PATH?")


@app.route('/')
def index():
    """Exibe a página inicial do assistente de instalação."""
    if os.path.exists(ENV_FILE_PATH):
        flash("Um arquivo .env já existe. Se você continuar, ele será sobrescrito.", "warning")
    return render_template('index.html')

def extract_vault_credentials_from_logs():
    """
    Espera o container vault-setup terminar e extrai as credenciais dos logs.
    """
    flash("Aguardando a configuração do Vault e geração de credenciais seguras...", "info")
    app.logger.info("Aguardando o container 'cspmexa-vault-setup' concluir...")

    # Espera o container terminar
    # Um loop de verificação com 'docker compose ps' é mais robusto que 'wait'
    while True:
        stdout, _ = run_docker_command(["compose", "ps", "--status=exited", "-q", "vault-setup"], capture=True)
        if "vault-setup" in stdout:
            break
        time.sleep(2)

    # Pega os logs
    logs, _ = run_docker_command(["compose", "logs", "vault-setup"], capture=True)
    app.logger.info("Logs do vault-setup obtidos.")

    # Extrai as credenciais usando regex
    credentials = {}
    patterns = {
        "AUTH_SERVICE_VAULT_ROLE_ID": r"AUTH_SERVICE_VAULT_ROLE_ID=([\w-]+)",
        "AUTH_SERVICE_VAULT_SECRET_ID": r"AUTH_SERVICE_VAULT_SECRET_ID=([\w-]+)",
        "COLLECTOR_SERVICE_VAULT_ROLE_ID": r"COLLECTOR_SERVICE_VAULT_ROLE_ID=([\w-]+)",
        "COLLECTOR_SERVICE_VAULT_SECRET_ID": r"COLLECTOR_SERVICE_VAULT_SECRET_ID=([\w-]+)",
        "NOTIFICATION_SERVICE_VAULT_ROLE_ID": r"NOTIFICATION_SERVICE_VAULT_ROLE_ID=([\w-]+)",
        "NOTIFICATION_SERVICE_VAULT_SECRET_ID": r"NOTIFICATION_SERVICE_VAULT_SECRET_ID=([\w-]+)",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, logs)
        if match:
            credentials[key] = match.group(1)
        else:
            app.logger.error(f"Não foi possível extrair a credencial '{key}' dos logs do Vault.")
            raise RuntimeError(f"Não foi possível extrair a credencial '{key}' dos logs do Vault. A configuração do Vault falhou.")

    flash("Credenciais do Vault geradas com sucesso!", "success")
    app.logger.info("Credenciais do Vault extraídas com sucesso.")
    return credentials

@app.route('/install', methods=['POST'])
def install():
    """Processa os dados do formulário, cria o .env e inicia os serviços."""
    try:
        # 0. Limpar ambiente anterior para evitar conflitos
        flash("Limpando ambiente de instalação anterior...", "info")
        app.logger.info("Executando 'docker compose down' para limpar contêineres antigos.")
        # O -v remove volumes anônimos, --remove-orphans remove contêineres de serviços não definidos
        run_docker_command(["compose", "down", "-v", "--remove-orphans"])

        # 1. Iniciar o Vault e o setup
        flash("Iniciando o Vault para configuração inicial...", "info")
        app.logger.info("Iniciando containers vault e vault-setup...")
        run_docker_command(["docker", "compose", "up", "-d", "--build", "vault", "vault-setup"])

        # 2. Extrair credenciais do Vault
        vault_creds = extract_vault_credentials_from_logs()

        # 3. Coletar dados do formulário
        form_data = request.form.to_dict()

        # 4. Gerar outros segredos
        db_password = form_data.get('AUTH_DB_PASSWORD') or secrets.token_urlsafe(16)
        jwt_secret_key = secrets.token_hex(32)

        # 5. Criar o conteúdo do .env
        env_content = f"""
# Arquivo gerado automaticamente pelo Assistente de Instalação do CSPMEXA

# --- Configurações do Banco de Dados ---
AUTH_DB_USER={form_data.get('AUTH_DB_USER', 'cspmexa_user')}
AUTH_DB_PASSWORD={db_password}
AUTH_DB_NAME={form_data.get('AUTH_DB_NAME', 'cspmexa_db')}

# --- Portas Expostas ---
API_GATEWAY_PORT={form_data.get('API_GATEWAY_PORT', 8050)}
FRONTEND_PORT={form_data.get('FRONTEND_PORT', 3000)}

# --- Configurações de JWT ---
JWT_SECRET_KEY={jwt_secret_key}
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# --- Configurações de OAuth do Google ---
GOOGLE_CLIENT_ID={form_data.get('GOOGLE_CLIENT_ID', '')}
GOOGLE_CLIENT_SECRET={form_data.get('GOOGLE_CLIENT_SECRET', '')}

# --- Credenciais do Vault (Geradas Automaticamente) ---
AUTH_SERVICE_VAULT_ROLE_ID={vault_creds['AUTH_SERVICE_VAULT_ROLE_ID']}
AUTH_SERVICE_VAULT_SECRET_ID={vault_creds['AUTH_SERVICE_VAULT_SECRET_ID']}
COLLECTOR_SERVICE_VAULT_ROLE_ID={vault_creds['COLLECTOR_SERVICE_VAULT_ROLE_ID']}
COLLECTOR_SERVICE_VAULT_SECRET_ID={vault_creds['COLLECTOR_SERVICE_VAULT_SECRET_ID']}
NOTIFICATION_SERVICE_VAULT_ROLE_ID={vault_creds['NOTIFICATION_SERVICE_VAULT_ROLE_ID']}
NOTIFICATION_SERVICE_VAULT_SECRET_ID={vault_creds['NOTIFICATION_SERVICE_VAULT_SECRET_ID']}
"""

        # 6. Escrever o arquivo .env
        with open(ENV_FILE_PATH, 'w') as f:
            f.write(env_content.strip())
        flash("Arquivo de configuração .env criado com sucesso.", "success")
        app.logger.info("Arquivo .env criado com sucesso.")

        # 7. Iniciar os serviços da aplicação
        flash("Iniciando todos os serviços da aplicação...", "info")
        app.logger.info("Iniciando serviços com perfil 'app'...")
        run_docker_command(["docker", "compose", "--profile", "app", "up", "--build", "-d"])

        # 8. Executar migrações do banco de dados
        flash("Executando migrações do banco de dados...", "info")
        app.logger.info("Aguardando o auth_service ficar pronto para a migração...")
        time.sleep(15) # Dar um tempo para o serviço de autenticação iniciar
        app.logger.info("Executando 'alembic upgrade head'...")
        run_docker_command(["docker", "compose", "exec", "auth_service", "alembic", "upgrade", "head"])
        flash("Migrações concluídas.", "success")
        app.logger.info("Migrações do banco de dados concluídas.")

        # 9. Redirecionar para a página de sucesso
        frontend_port = form_data.get('FRONTEND_PORT', '3000')
        return redirect(f'/success?frontend_port={frontend_port}')

    except (RuntimeError, IOError) as e:
        app.logger.error(f"Falha na instalação: {e}")
        flash(str(e), "danger")
        return redirect('/')

@app.route('/success')
def success():
    """Exibe uma mensagem de sucesso mais útil após a instalação."""
    frontend_port = request.args.get('frontend_port', '3000')
    host_ip = request.host.split(':')[0]
    access_url = f"http://{host_ip}:{frontend_port}"

    return render_template('success.html', access_url=access_url, frontend_port=frontend_port)

if __name__ == '__main__':
    # Configurar o logger do Flask
    app.logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    app.logger.addHandler(handler)

    app.run(host='0.0.0.0', port=8080)
