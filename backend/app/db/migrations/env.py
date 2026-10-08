from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from app.db.all_models import Base  # importing it registers every model on Base.metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# "how the database SHOULD look", read from the models. Autogenerate compares this with the real database.
target_metadata = Base.metadata


def get_url() -> str:
    # a caller (a test, a script) may hand in its own URL; otherwise the app's own setting is used
    url = config.get_main_option("sqlalchemy.url")
    if url:
        return url
    from app.core.config import settings

    return settings.database_url


def configure_kwargs(url: str) -> dict:
    return dict(
        target_metadata=target_metadata,
        compare_type=True,  # also notice a column whose type changed
        # SQLite cannot ALTER most things in place; "batch" mode builds a new table, copies the rows and swaps it in
        render_as_batch=url.startswith("sqlite"),
    )


def run_migrations_offline() -> None:
    """Write the SQL instead of running it (alembic upgrade head --sql)."""
    url = get_url()
    context.configure(url=url, literal_binds=True, **configure_kwargs(url))
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = get_url()
    engine = create_engine(url)
    with engine.connect() as connection:
        context.configure(connection=connection, **configure_kwargs(url))
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
