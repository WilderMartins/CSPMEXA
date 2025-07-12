from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# Importar Base e modelos SQLAlchemy do seu app FastAPI
# Ajuste os imports conforme a estrutura do seu projeto FastAPI
import sys
from pathlib import Path
# Adiciona o diretório 'backend' ao sys.path para que possamos importar de outros serviços
# Isso assume que env.py está em backend/auth_service/alembic/
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Modelos do auth_service
from auth_service.app.db.session import Base as AuthBase
from auth_service.app.models.user_model import User as AuthUser

# Modelos do policy_engine_service (especificamente o AlertModel)
# Certifique-se que policy_engine_service.app.models.alert_model não tem dependências circulares
# ou complexas que dificultem a importação aqui.
try:
    from policy_engine_service.app.models.alert_model import Base as PolicyEngineAlertBase
    # O modelo Alert em si não é explicitamente necessário aqui se usarmos target_metadata = [AuthBase.metadata, PolicyEngineAlertBase.metadata]
    # from policy_engine_service.app.models.alert_model import Alert as PolicyEngineAlert
except ImportError as e:
    print(f"Erro ao importar modelos do policy_engine_service: {e}")
    print("Verifique se o policy_engine_service está estruturado corretamente e PYTHONPATH está configurado se rodar alembic CLI manualmente.")
    PolicyEngineAlertBase = None


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# target_metadata = Base.metadata # Antigo

# Para múltiplos MetaData de diferentes Bases (de diferentes serviços/modelos)
target_metadata_list = [AuthBase.metadata]
if PolicyEngineAlertBase:
    target_metadata_list.append(PolicyEngineAlertBase.metadata)
target_metadata = target_metadata_list

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def get_url_from_config():
    # Tenta pegar da config do alembic.ini primeiro
    url = config.get_main_option("sqlalchemy.url")
    if url:
        return url
    # Se não, tenta pegar das settings do app
    try:
        from app.core.config import settings
        return settings.DATABASE_URL
    except ImportError: # ou se settings não tiver DATABASE_URL
        raise Exception("DATABASE_URL not found in alembic.ini or app.core.config.settings")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.
    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.
    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_url_from_config()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.
    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Carrega a URL do banco de dados a partir da configuração da aplicação FastAPI
    # Isso garante que Alembic use a mesma configuração de DB que a aplicação.
    db_url = get_url_from_config()

    # Cria uma engine SQLAlchemy
    connectable = engine_from_config(
        {"sqlalchemy.url": db_url}, # Passa a URL para a engine config
        prefix="sqlalchemy.",       # Alembic espera que a URL esteja sob 'sqlalchemy.url'
        poolclass=pool.NullPool,
    )


    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
