import pytest
from dotenv import load_dotenv

@pytest.fixture(scope="session", autouse=True)
def load_test_env():
    load_dotenv(dotenv_path="backend/auth_service/.env.test")
