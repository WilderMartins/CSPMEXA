import os
import re
import secrets
import subprocess
import time
from flask import Flask, render_template, request, redirect, flash, url_for
import logging
import sys

# Inicializa o aplicativo Flask
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Configurar o logger do Flask
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

# Caminhos
ENV_FILE_PATH = os.path.join('/app/config', '.env')
DOCKER_COMPOSE_YML_PATH = '/app/config'

def run_docker_command(command, capture=True, ignore_errors=False):
    """Helper para executar comandos Docker Compose."""
    try:
        if capture:
            result = subprocess.run(
                command, check=not ignore_errors, cwd=DOCKER_COMPOSE_YML_PATH,
                capture_output=True, text=True
            )
            return result.stdout, result.stderr
        else:
            subprocess.run(
                command, check=not ignore_errors, cwd=DOCKER_COMPOSE_YML_PATH
            )
            return "", ""
    except subprocess.CalledProcessError as e:
        error_message = f"Comando falhou: {' '.join(command)}\nStdout: {e.stdout}\nStderr: {e.stderr}"
        if not ignore_errors:
            raise RuntimeError(error_message)
        else:
            app.logger.warning(error_message)
            return e.stdout, e.stderr
    except FileNotFoundError:
        raise RuntimeError(f"Comando 'docker' não encontrado. O Docker está instalado e no PATH?")

@app.route('/')
def pre_install_check():
    """Página inicial que oferece a opção de limpar o ambiente antes de instalar."""
    return render_template('pre_install.html')

@app.route('/cleanup')
def cleanup():
    """Executa a limpeza do ambiente Docker."""
    flash("Iniciando limpeza do ambiente Docker anterior...", "info")
    app.logger.info("Executando 'docker compose down' para limpar contêineres e volumes anônimos.")
    run_docker_command(["docker", "compose", "down", "-v", "--remove-orphans"], ignore_errors=True)
    flash("Ambiente limpo com sucesso! Você pode prosseguir com a instalação.", "success")
    return redirect(url_for('install_page'))

@app.route('/install', methods=['GET'])
def install_page():
    """Exibe a página de instalação principal."""
    if os.path.exists(ENV_FILE_PATH):
        flash("Um arquivo .env já existe. Se você continuar, ele será sobrescrito.", "warning")
    return render_template('index.html')

def extract_vault_credentials_from_logs():
    """Espera o container vault-setup terminar e extrai as credenciais dos logs."""
    flash("Aguardando a configuração do Vault...", "info")
    app.logger.info("Aguardando 'cspmexa-vault-setup' concluir...")

    # Loop de verificação para esperar o container terminar
    for _ in range(60): # Timeout de 2 minutos
        stdout, _ = run_docker_command(["docker", "compose", "ps", "--status=exited", "-q", "vault-setup"], capture=True)
        if "vault-setup" in stdout:
            break
        time.sleep(2)
    else:
        raise RuntimeError("Timeout esperando pelo container vault-setup. A configuração do Vault falhou.")

    logs, _ = run_docker_command(["docker", "compose", "logs", "vault-setup"], capture=True)
    app.logger.info("Logs do vault-setup obtidos.")

    credentials = {}
    patterns = {
        "AUTH_SERVICE_VAULT_ROLE_ID": r"AUTH_SERVICE_VAULT_ROLE_ID=([\w-]+)",
        # ... (outros patterns)
    }
    # (Lógica de extração de credenciais omitida para brevidade, mas permanece a mesma)

    flash("Credenciais do Vault geradas!", "success")
    return credentials

@app.route('/install', methods=['POST'])
def perform_install():
    """Processa os dados do formulário, cria o .env e inicia os serviços."""
    try:
        # 1. Iniciar o Vault
        flash("Iniciando Vault...", "info")
        run_docker_command(["docker", "compose", "up", "-d", "--build", "vault", "vault-setup"])

        # 2. Extrair credenciais (função simplificada para este exemplo)
        vault_creds = {"AUTH_SERVICE_VAULT_ROLE_ID": "dummy-role", "AUTH_SERVICE_VAULT_SECRET_ID": "dummy-secret"} # Placeholder

        # 3. Coletar e gerar dados do .env
        form_data = request.form.to_dict()
        db_password = form_data.get('AUTH_DB_PASSWORD') or secrets.token_urlsafe(16)
        jwt_secret_key = secrets.token_hex(32) # Gerado automaticamente

        env_content = f"""
# ... (conteúdo do .env como antes, usando os dados do form e do vault_creds) ...
JWT_SECRET_KEY={jwt_secret_key}
AUTH_DB_PASSWORD={db_password}
AUTH_SERVICE_VAULT_ROLE_ID={vault_creds['AUTH_SERVICE_VAULT_ROLE_ID']}
AUTH_SERVICE_VAULT_SECRET_ID={vault_creds['AUTH_SERVICE_VAULT_SECRET_ID']}
"""
        # 4. Escrever .env e iniciar serviços
        with open(ENV_FILE_PATH, 'w') as f:
            f.write(env_content.strip())

        flash("Iniciando serviços da aplicação...", "info")
        run_docker_command(["docker", "compose", "--profile", "app", "up", "--build", "-d"])

        flash("Executando migrações do banco de dados...", "info")
        time.sleep(15)
        run_docker_command(["docker", "compose", "exec", "auth_service", "alembic", "upgrade", "head"])

        return redirect(url_for('success'))

    except (RuntimeError, IOError, ValueError) as e:
        flash(str(e), "danger")
        return redirect(url_for('install_page'))

@app.route('/success')
def success():
    """Exibe a mensagem de sucesso."""
    return render_template('success.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
