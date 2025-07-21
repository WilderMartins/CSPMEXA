import os
import re
import secrets
import shutil
import subprocess
import time
from flask import Flask, render_template, request, redirect, flash, url_for, jsonify
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

def check_prerequisites():
    """Verifica se todos os pré-requisitos para a instalação estão atendidos."""
    app.logger.info("Iniciando verificação de pré-requisitos...")
    prereqs = {
        'docker_installed': False,
        'docker_running': False,
        'docker_permission': False,
        'docker_compose_installed': False,
    }

    # 1. Docker está instalado?
    if shutil.which("docker"):
        prereqs['docker_installed'] = True
        app.logger.info("Verificação 'docker_installed': SUCESSO")
    else:
        app.logger.error("Verificação 'docker_installed': FALHA - Comando 'docker' não encontrado.")
        return prereqs # Encerra se o Docker não estiver instalado

    # 2. Docker está em execução e com permissões corretas?
    try:
        # Tenta executar um comando Docker que requer conexão com o daemon
        subprocess.run(
            ["docker", "info"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True
        )
        prereqs['docker_running'] = True
        prereqs['docker_permission'] = True
        app.logger.info("Verificação 'docker_running': SUCESSO")
        app.logger.info("Verificação 'docker_permission': SUCESSO")
    except subprocess.CalledProcessError as e:
        if "permission denied" in e.stderr.lower():
            prereqs['docker_running'] = True # O daemon está rodando, mas o usuário não tem permissão
            app.logger.warning("Verificação 'docker_running': SUCESSO")
            app.logger.error("Verificação 'docker_permission': FALHA - Permissão negada para acessar o Docker daemon.")
        else:
            app.logger.error(f"Verificação 'docker_running': FALHA - Docker daemon não parece estar em execução. Erro: {e.stderr}")
    except FileNotFoundError:
        # Este caso já é coberto por shutil.which, mas é uma boa prática mantê-lo
        app.logger.error("Verificação 'docker_installed': FALHA - Comando 'docker' não encontrado ao tentar executar 'docker info'.")


    # 3. Docker Compose está instalado?
    # O Docker Compose V2 é um plugin, então `docker compose` (sem hífen) é o comando preferido.
    try:
        subprocess.run(
            ["docker", "compose", "version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True
        )
        prereqs['docker_compose_installed'] = True
        app.logger.info("Verificação 'docker_compose_installed': SUCESSO")
    except (subprocess.CalledProcessError, FileNotFoundError):
        app.logger.error("Verificação 'docker_compose_installed': FALHA - 'docker compose' não funciona.")

    app.logger.info(f"Resultado da verificação de pré-requisitos: {prereqs}")
    return prereqs


def run_docker_command(command, wait=True, ignore_errors=False, log_file_path=None):
    """Helper para executar comandos Docker Compose."""
    try:
        if not wait and log_file_path:
            # Para execução em segundo plano com log, redirecionamos stdout/stderr para um arquivo.
            log_file = open(log_file_path, 'w')
            process = subprocess.Popen(
                command,
                cwd=DOCKER_COMPOSE_YML_PATH,
                stdout=log_file,
                stderr=log_file,
                text=True
            )
            # Não esperamos, apenas retornamos o processo. O arquivo de log capturará a saída.
            return process, None, None
        else:
            # Comportamento de espera padrão
            process = subprocess.Popen(
                command,
                cwd=DOCKER_COMPOSE_YML_PATH,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
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
    """Página inicial que executa a verificação de pré-requisitos."""
    prereqs = check_prerequisites()
    all_ok = all(prereqs.values())
    return render_template('pre_install.html', prereqs=prereqs, all_ok=all_ok)

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


@app.route('/install', methods=['POST'])
def perform_install():
    """Processa os dados do formulário, cria o .env e inicia os serviços."""
    try:
        # Coletar dados do formulário
        form_data = request.form.to_dict()

        # Validação de e-mails
        emails_to_validate = [
            'EMAILS_FROM_EMAIL',
            'DEFAULT_CRITICAL_ALERT_RECIPIENT_EMAIL',
            'GOOGLE_WORKSPACE_DELEGATED_ADMIN_EMAIL'
        ]
        for email_field in emails_to_validate:
            email = form_data.get(email_field)
            if email and not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                flash(f"O endereço de e-mail fornecido para '{email_field}' é inválido.", "danger")
                return redirect(url_for('install_page'))

        db_password = form_data.get('AUTH_DB_PASSWORD') or secrets.token_urlsafe(16)
        jwt_secret_key = secrets.token_hex(32)

        # Criar o conteúdo do .env com todos os campos do formulário
        env_content = f"""
AUTH_DB_USER={form_data.get('AUTH_DB_USER', 'cspmexa_user')}
AUTH_DB_PASSWORD={db_password}
AUTH_DB_NAME={form_data.get('AUTH_DB_NAME', 'cspmexa_db')}
FRONTEND_PORT={form_data.get('FRONTEND_PORT', '3000')}
API_GATEWAY_PORT={form_data.get('API_GATEWAY_PORT', '8050')}
GOOGLE_CLIENT_ID={form_data.get('GOOGLE_CLIENT_ID', '')}
GOOGLE_CLIENT_SECRET={form_data.get('GOOGLE_CLIENT_SECRET', '')}
JWT_SECRET_KEY={jwt_secret_key}
AUTH_SERVICE_VAULT_ROLE_ID={form_data.get('AUTH_SERVICE_VAULT_ROLE_ID', '')}
AUTH_SERVICE_VAULT_SECRET_ID={form_data.get('AUTH_SERVICE_VAULT_SECRET_ID', '')}
EMAILS_FROM_EMAIL={form_data.get('EMAILS_FROM_EMAIL', '')}
DEFAULT_CRITICAL_ALERT_RECIPIENT_EMAIL={form_data.get('DEFAULT_CRITICAL_ALERT_RECIPIENT_EMAIL', '')}
AWS_ACCESS_KEY_ID={form_data.get('AWS_ACCESS_KEY_ID', '')}
AWS_SECRET_ACCESS_KEY={form_data.get('AWS_SECRET_ACCESS_KEY', '')}
GOOGLE_WORKSPACE_DELEGATED_ADMIN_EMAIL={form_data.get('GOOGLE_WORKSPACE_DELEGATED_ADMIN_EMAIL', '')}
AZURE_SUBSCRIPTION_ID={form_data.get('AZURE_SUBSCRIPTION_ID', '')}
AZURE_TENANT_ID={form_data.get('AZURE_TENANT_ID', '')}
AZURE_CLIENT_ID={form_data.get('AZURE_CLIENT_ID', '')}
AZURE_CLIENT_SECRET={form_data.get('AZURE_CLIENT_SECRET', '')}
HUAWEICLOUD_SDK_AK={form_data.get('HUAWEICLOUD_SDK_AK', '')}
HUAWEICLOUD_SDK_SK={form_data.get('HUAWEICLOUD_SDK_SK', '')}
HUAWEICLOUD_SDK_PROJECT_ID={form_data.get('HUAWEICLOUD_SDK_PROJECT_ID', '')}
HUAWEICLOUD_SDK_DOMAIN_ID={form_data.get('HUAWEICLOUD_SDK_DOMAIN_ID', '')}
M365_CLIENT_ID={form_data.get('M365_CLIENT_ID', '')}
M365_CLIENT_SECRET={form_data.get('M365_CLIENT_SECRET', '')}
M365_TENANT_ID={form_data.get('M365_TENANT_ID', '')}
"""
        # Escrever o arquivo .env
        with open(ENV_FILE_PATH, 'w') as f:
            f.write(env_content.strip())

        app.logger.info("Arquivo .env criado com sucesso!")


        # Iniciar serviços em segundo plano e registrar a saída
        log_file_path = os.path.join(DOCKER_COMPOSE_YML_PATH, 'installation.log')
        app.logger.info(f"Iniciando a instalação dos serviços em segundo plano... Log em: {log_file_path}")

        # Limpa o log antigo, se existir
        if os.path.exists(log_file_path):
            os.remove(log_file_path)

        run_docker_command(
            ["docker", "compose", "--profile", "app", "up", "-d", "--build"],
            wait=False,
            log_file_path=log_file_path
        )


        # Redirecionar para a página de status para acompanhar o progresso
        return redirect(url_for('status'))

    except (IOError, ValueError) as e:
        flash(f"Ocorreu um erro: {e}", "danger")
        return redirect(url_for('install_page'))

from flask import jsonify

@app.route('/status')
def status():
    """Verifica e retorna o status da instalação como JSON."""
    services = [
        "postgres_auth_db", "vault", "vault-setup", "auth_service",
        "collector_service", "policy_engine_service", "notification_service",
        "api_gateway_service", "frontend_build", "nginx"
    ]
    statuses = {}
    for service in services:
        try:
            stdout, _ = run_docker_command(
                ["docker", "compose", "ps", "--format", "{{.State}}", service],
                wait=True,
                ignore_errors=True
            )
            status_text = stdout.strip()
            if not status_text:
                statuses[service] = "not_started"
            else:
                # Simplifica o status para facilitar a análise no frontend
                if 'running' in status_text:
                    statuses[service] = 'running'
                elif 'exited' in status_text:
                    statuses[service] = 'exited'
                else:
                    statuses[service] = 'starting'
        except Exception as e:
            statuses[service] = "error"
            app.logger.error(f"Erro ao obter status do serviço {service}: {e}")

    essential_services = [
        "api_gateway_service", "auth_service", "collector_service",
        "notification_service", "policy_engine_service", "nginx"
    ]
    is_done = all(statuses.get(s) == 'running' for s in essential_services)

    return jsonify(statuses=statuses, done=is_done)

@app.route('/logs/<service_name>')
def service_logs(service_name):
    """Retorna os logs de um serviço específico."""
    try:
        logs, _ = run_docker_command(
            ["docker", "compose", "logs", "--no-color", "--tail=100", service_name],
            wait=True,
            ignore_errors=True
        )
        return logs
    except Exception as e:
        app.logger.error(f"Erro ao obter logs para o serviço {service_name}: {e}")
        return f"Erro ao carregar logs para {service_name}."

@app.route('/installation-log')
def installation_log():
    """Exibe o log da instalação."""
    log_file_path = os.path.join(DOCKER_COMPOSE_YML_PATH, 'installation.log')
    try:
        with open(log_file_path, 'r') as f:
            log_content = f.read()
        return f"<pre>{log_content}</pre>"
    except FileNotFoundError:
        return "<pre>Arquivo de log da instalação ainda não foi criado. Aguarde um momento e atualize a página.</pre>"
    except Exception as e:
        return f"<pre>Erro ao ler o arquivo de log: {e}</pre>"

@app.route('/success')
def success():
    """Exibe a mensagem de sucesso."""
    return render_template('success.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
