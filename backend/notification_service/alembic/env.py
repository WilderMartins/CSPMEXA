from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
# target_metadata = None
from app.models.notification_channel_model import Base as NotificationChannelBase
from app.models.notification_rule_model import Base as NotificationRuleBase
# Adicione aqui outras bases de modelos se houver mais
# A melhor prática é ter uma única Base para todos os modelos
# from app.db.base import Base # Exemplo de uma base unificada
# target_metadata = Base.metadata
# Por enquanto, vamos unir os metadados manualmente se eles forem separados
# Esta abordagem não é ideal, mas funciona para modelos simples e separados.
# O ideal seria refatorar para usar uma única Base declarativa.
# target_metadata = [NotificationChannelBase.metadata, NotificationRuleBase.metadata]
# A abordagem acima com uma lista não funciona diretamente.
# Vamos assumir que os modelos serão adicionados a uma única Base no futuro.
# Por agora, para fazer funcionar, precisamos de uma Base unificada.
# Vamos criar uma em db/base.py e fazer os modelos herdarem dela.
# ---
# Supondo que você criou `app/db/base.py` com:
# from sqlalchemy.ext.declarative import declarative_base
# Base = declarative_base()
# E seus modelos herdam de `from app.db.base import Base`
from app.db.base import Base # Você precisará criar este arquivo
target_metadata = Base.metadata


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
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
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
