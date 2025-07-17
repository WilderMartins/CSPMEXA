import pytest
from dotenv import load_dotenv
import os

# Carregar as variáveis de ambiente de teste ANTES de qualquer outra importação
# para garantir que as configurações da aplicação as utilizem.
@pytest.fixture(scope="session", autouse=True)
def load_test_env():
    # O caminho é relativo à raiz do projeto, onde o pytest é executado
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env.test')
    load_dotenv(dotenv_path=env_path)
