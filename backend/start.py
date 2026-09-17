import os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from sqlalchemy import inspect
from alembic.config import Config
from alembic import command
from backend.app.config import settings
from backend.app.database import engine

settings.validate_runtime()
cfg=Config("backend/alembic.ini")
tables=set(inspect(engine).get_table_names())
if "leads" in tables and "alembic_version" not in tables:
    command.stamp(cfg,"0001")
command.upgrade(cfg,"head")
os.execvp("uvicorn",["uvicorn","backend.app.main:app","--host","0.0.0.0","--port","8000"])
