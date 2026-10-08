from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError

from app.db.all_models import Base

BACKEND = Path(__file__).resolve().parents[2]


@pytest.fixture
def url(tmp_path):
    # a file, not ":memory:": the migration opens its own connection
    return f"sqlite:///{(tmp_path / 'migrated.db').as_posix()}"


@pytest.fixture
def cfg(url):
    cfg = Config(str(BACKEND / "alembic.ini"))
    # absolute, so the test works from any folder
    cfg.set_main_option("script_location", (BACKEND / "app" / "db" / "migrations").as_posix())
    cfg.set_main_option("sqlalchemy.url", url)  # the test's own database, never the one in .env
    return cfg


def table_names(url):
    engine = create_engine(url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def versions_in_database(url):
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            return [row[0] for row in connection.execute(text("select version_num from alembic_version"))]
    finally:
        engine.dispose()


# ---------- the chain of migrations ----------

def test_there_is_exactly_one_latest_revision(cfg):
    # two heads happen when two branches each add a migration: Alembic then refuses to upgrade
    assert len(ScriptDirectory.from_config(cfg).get_heads()) == 1


def test_upgrade_builds_every_table_of_the_models(cfg, url):
    command.upgrade(cfg, "head")

    assert table_names(url) == set(Base.metadata.tables) | {"alembic_version"}


def test_models_and_migrations_agree(cfg, url):
    """The guard against forgetting a migration: a database built only from the migrations must look
    exactly like the models. If this fails, a model was changed without a migration:
    run  alembic revision --autogenerate -m "what changed"  and read the file it writes."""
    command.upgrade(cfg, "head")

    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(connection, opts={"compare_type": True})
            differences = compare_metadata(context, Base.metadata)
    finally:
        engine.dispose()

    assert differences == []


def test_downgrade_to_the_start_removes_everything(cfg, url):
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")

    assert table_names(url) == {"alembic_version"}  # Alembic keeps its own bookkeeping table


def test_upgrading_twice_changes_nothing(cfg, url):
    command.upgrade(cfg, "head")
    command.upgrade(cfg, "head")

    assert table_names(url) == set(Base.metadata.tables) | {"alembic_version"}


# ---------- a database that exists already ----------

def test_a_database_made_by_create_all_needs_stamp_not_upgrade(cfg, url):
    """The situation of a database from before Alembic was introduced: the tables are there, but
    Alembic has no record. Running the first migration would fail; stamping marks it as done."""
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    engine.dispose()

    with pytest.raises(OperationalError):  # "table users already exists"
        command.upgrade(cfg, "head")

    command.stamp(cfg, "head")
    command.upgrade(cfg, "head")  # now there is nothing left to do

    assert versions_in_database(url) == ScriptDirectory.from_config(cfg).get_heads()
