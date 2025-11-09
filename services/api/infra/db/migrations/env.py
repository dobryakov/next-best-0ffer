from __future__ import annotations

import sys
from importlib import import_module
from logging.config import fileConfig
from pathlib import Path
from typing import Iterable, Iterator

from alembic import context
from sqlalchemy import engine_from_config, pool

# Добавляем корневую директорию репозитория в sys.path, чтобы alembic мог находить пакеты проекта.
def _discover_project_root() -> Path:
    path = Path(__file__).resolve()
    for candidate in [path.parent] + list(path.parents):
        if (candidate / "pyproject.toml").exists():
            return candidate
        if (candidate / ".git").exists():
            return candidate
    return path.parent


ROOT_DIR = _discover_project_root()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from infra.config.settings import get_settings  # noqa: E402
from infra.db.models import metadata  # noqa: E402

config = context.config


def _import_submodules(package_name: str) -> None:
    package = import_module(package_name)
    if not hasattr(package, "__path__"):
        return

    for module_info in _walk_packages(package.__path__, package.__name__ + "."):
        import_module(module_info)


def _walk_packages(path: Iterable[str], prefix: str) -> Iterator[str]:
    # ленивый импорт pkgutil только если действительно нужны модели
    import pkgutil

    yield from (module.name for module in pkgutil.walk_packages(path, prefix))


def _configure_logging() -> None:
    if config.config_file_name:
        fileConfig(config.config_file_name)


def get_target_metadata():
    _import_submodules("infra.db.models")
    return metadata


def run_migrations_offline() -> None:
    settings = get_settings()
    context.configure(
        url=str(settings.postgres_dsn),
        target_metadata=get_target_metadata(),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    settings = get_settings()
    config.set_main_option("sqlalchemy.url", str(settings.postgres_dsn))

    connectable = engine_from_config(
        config.get_section(config.config_ini_section) or {},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=get_target_metadata(),
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


def main() -> None:
    _configure_logging()
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        run_migrations_online()


main()


