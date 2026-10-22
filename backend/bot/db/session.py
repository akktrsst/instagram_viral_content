from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import PROJECT_ROOT, settings
from bot.db.models import Base

# On Postgres the bot's tables live in their own schema; "public" belongs to Firebase SQL Connect,
# whose migrations would otherwise try to drop tables it does not know about.
POSTGRES_SCHEMA = "bot"


@lru_cache
def get_engine() -> Engine:
    if settings.cloudsql_instance:
        from google.cloud.sql.connector import Connector

        connector = Connector(timeout=30)

        def getconn():
            return connector.connect(
                settings.cloudsql_instance,
                "pg8000",
                user=settings.db_user,
                password=settings.db_password,
                db=settings.db_name,
            )

        return create_engine(
            "postgresql+pg8000://",
            creator=getconn,
            pool_pre_ping=True,
            pool_timeout=30,
            # Replace idle connections before they go stale (e.g. after a laptop sleeps).
            pool_recycle=240,
            execution_options={"schema_translate_map": {None: POSTGRES_SCHEMA}},
        )

    if settings.database_url:
        engine = create_engine(settings.database_url)
        if engine.dialect.name == "postgresql":
            engine = engine.execution_options(schema_translate_map={None: POSTGRES_SCHEMA})
        return engine
    db_path = PROJECT_ROOT / "output" / "bot.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{db_path}")


def get_session() -> Session:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)()


def init_db() -> None:
    engine = get_engine()
    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{POSTGRES_SCHEMA}"'))
    Base.metadata.create_all(engine)
