from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config,pool
from backend.app.database import Base
from backend.app import models
from backend.app.config import settings
config=context.config
config.set_main_option("sqlalchemy.url",settings.database_url)
if config.config_file_name:fileConfig(config.config_file_name)
target_metadata=Base.metadata
def offline():
    context.configure(url=config.get_main_option('sqlalchemy.url'),target_metadata=target_metadata,literal_binds=True)
    with context.begin_transaction():context.run_migrations()
def online():
    connectable=engine_from_config(config.get_section(config.config_ini_section),prefix='sqlalchemy.',poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection,target_metadata=target_metadata)
        with context.begin_transaction():context.run_migrations()
offline() if context.is_offline_mode() else online()
