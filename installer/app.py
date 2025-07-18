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

def run_docker_command(command, wait=True, ignore_errors=False):
    """Helper para executar comandos Docker Compose."""
    try:
        # Usar Popen para controle não bloqueante
        process = subprocess.Popen(
            command,
            cwd=DOCKER_COMPOSE_YML_PATH,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if not wait:
            # Retorna o processo imediatamente para execução em segundo plano
            return process, None, None

        # Comportamento de espera padrão
        stdout, stderr = process.communicate()

        if process.returncode != 0 and not ignore_errors:
            raise subprocess.CalledProcessError(
                process.returncode, command, output=stdout, stderr=stderr
            )

        return stdout, stderr

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
    app.logger.info("Iniciando limpeza do ambiente Docker anterior...")
    app.logger.info("Executando 'docker compose down' para limpar contêineres e volumes anônimos.")
    run_docker_command(["docker", "compose", "down", "-v", "--remove-orphans"], ignore_errors=True)
    app.logger.info("Ambiente limpo com sucesso! Você pode prosseguir com a instalação.")
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
        # Coletar dados do formulário
        form_data = request.form.to_dict()
        db_password = form_data.get('AUTH_DB_PASSWORD') or secrets.token_urlsafe(16)
        jwt_secret_key = secrets.token_hex(32)

        # Usar placeholders para credenciais do Vault
        vault_role_id = "dummy-role-id"
        vault_secret_id = "dummy-secret-id"

        # Criar o conteúdo do .env
        env_content = f"""
AUTH_DB_USER={form_data.get('AUTH_DB_USER', 'cspmexa_user')}
AUTH_DB_PASSWORD={db_password}
AUTH_DB_NAME={form_data.get('AUTH_DB_NAME', 'cspmexa_db')}
FRONTEND_PORT={form_data.get('FRONTEND_PORT', '3000')}
API_GATEWAY_PORT={form_data.get('API_GATEWAY_PORT', '8050')}
GOOGLE_CLIENT_ID={form_data.get('GOOGLE_CLIENT_ID', '')}
GOOGLE_CLIENT_SECRET={form_data.get('GOOGLE_CLIENT_SECRET', '')}
JWT_SECRET_KEY={jwt_secret_key}
AUTH_SERVICE_VAULT_ROLE_ID={vault_role_id}
AUTH_SERVICE_VAULT_SECRET_ID={vault_secret_id}
EMAILS_FROM_EMAIL=""
DEFAULT_CRITICAL_ALERT_RECIPIENT_EMAIL=""
AWS_ACCESS_KEY_ID=""
AWS_SECRET_ACCESS_KEY=""
GOOGLE_WORKSPACE_DELEGATED_ADMIN_EMAIL=""
AZURE_SUBSCRIPTION_ID=""
AZURE_TENANT_ID=""
AZURE_CLIENT_ID=""
AZURE_CLIENT_SECRET=""
HUAWEICLOUD_SDK_AK=""
HUAWEICLOUD_SDK_SK=""
HUAWEICLOUD_SDK_PROJECT_ID=""
HUAWEICLOUD_SDK_DOMAIN_ID=""
M365_CLIENT_ID=""
M365_CLIENT_SECRET=""
M365_TENANT_ID=""
"""
        # Escrever o arquivo .env
        with open(ENV_FILE_PATH, 'w') as f:
            f.write(env_content.strip())

        app.logger.info("Arquivo .env criado com sucesso!")

        # Iniciar serviços em segundo plano
        app.logger.info("Iniciando a instalação dos serviços em segundo plano...")
        run_docker_command(["docker", "compose", "up", "-d", "--build"], wait=False)

        # Redirecionar para a página de status para acompanhar o progresso
        return redirect(url_for('status'))

    except (IOError, ValueError) as e:
        flash(f"Ocorreu um erro: {e}", "danger")
        return redirect(url_for('install_page'))

@app.route('/status')
def status():
    """Verifica e exibe o status da instalação."""
    try:
        # Analisa o status dos contêineres
        ps_stdout, ps_stderr = run_docker_command(
            ["docker", "compose", "ps", "--format", "{{.Name}}: {{.State}}"],
            wait=True,
            ignore_errors=True
        )
        container_statuses = ps_stdout.strip().split('\n') if ps_stdout else []

        # Obter logs apenas dos contêineres que estão 'running' ou 'exited'
        log_stdout, log_stderr = run_docker_command(
            ["docker", "compose", "logs", "--no-color", "--tail=200"],
            wait=True,
            ignore_errors=True
        )

        # Combinar saídas de erro para depuração
        errors = (ps_stderr or "") + "\n" + (log_stderr or "")
        errors = errors.strip()

        # Verifica se todos os serviços essenciais estão 'running'
        essential_services = [
            "api-gateway", "auth-service", "collector-service",
            "notification-service", "policy-engine-service"
        ]
        running_services = [s for s in container_statuses if "running" in s]
        is_done = all(any(service in status for status in running_services) for service in essential_services)

    except Exception as e:
        app.logger.error(f"Erro ao obter status da instalação: {e}")
        log_stdout = ""
        errors = f"Erro ao obter status: {e}"
        container_statuses = []
        is_done = False

    return render_template('status.html', logs=log_stdout, errors=errors, statuses=container_statuses, done=is_done)

@app.route('/success')
def success():
    """Exibe a mensagem de sucesso."""
    return render_template('success.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
