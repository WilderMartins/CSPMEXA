import pytest
from installer.app import app as flask_app

@pytest.fixture
def app():
    yield flask_app

@pytest.fixture
def client(app):
    return app.test_client()

def test_prereq_check_success(client, mocker):
    """Testa a página de pré-requisitos quando todas as verificações passam."""
    mocker.patch('installer.app.check_prerequisites', return_value={
        'docker_installed': True,
        'docker_running': True,
        'docker_permission': True,
        'docker_compose_installed': True,
    })
    response = client.get('/')
    assert response.status_code == 200
    assert b"Tudo Certo!" in response.data
    assert b"Limpar Ambiente Anterior e Instalar" in response.data

def test_prereq_check_failure(client, mocker):
    """Testa a página de pré-requisitos quando uma verificação falha."""
    mocker.patch('installer.app.check_prerequisites', return_value={
        'docker_installed': True,
        'docker_running': False,
        'docker_permission': False,
        'docker_compose_installed': True,
    })
    response = client.get('/')
    assert response.status_code == 200
    assert b"Problemas Encontrados!" in response.data

def test_install_success(client, mocker):
    """Testa o envio do formulário de instalação com dados válidos."""
    mocker.patch('installer.app.run_docker_command')
    mocker.patch('os.path.exists', return_value=False)

    response = client.post('/install', data={
        'AUTH_DB_USER': 'testuser',
        'AUTH_DB_NAME': 'testdb',
        'FRONTEND_PORT': '3001',
        'API_GATEWAY_PORT': '8051',
        'EMAILS_FROM_EMAIL': 'test@example.com',
    })

    assert response.status_code == 302
    assert response.location == '/status'

def test_install_invalid_email(client):
    """Testa o envio do formulário de instalação com um e-mail inválido."""
    response = client.post('/install', data={
        'EMAILS_FROM_EMAIL': 'not-an-email',
    })

    assert response.status_code == 302
    assert response.location == '/install'
