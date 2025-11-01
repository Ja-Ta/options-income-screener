from sqlalchemy import create_engine, text
from . import schema_sql_path

def get_engine(db_url: str):
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    with engine.connect() as con:
        con.execute(text("PRAGMA journal_mode=WAL;"))
        con.execute(text("PRAGMA synchronous=NORMAL;"))
    return engine
