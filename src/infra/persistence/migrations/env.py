import logging

from alembic import context
from sqlalchemy import create_engine, pool

from src.infra.persistence.orm import Base
import src.infra.persistence.orm  # noqa


config = context.config

logger = logging.getLogger(__name__)
logger.debug("Alembic env loaded config_file=%s", config.config_file_name)

target_metadata = Base.metadata


def _db_url() -> str:
    return config.get_main_option("sqlalchemy.url")


def run_migrations_offline() -> None:
    context.configure(
        url=_db_url(),
        target_metadata=target_metadata,
        render_as_batch=True,
        compare_type=True,
        compare_server_default=True,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    logger.info("Alembic online migration context begin")
    connectable = create_engine(
        _db_url(),
        future=True,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()
    logger.info("Alembic online migration context complete")


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
