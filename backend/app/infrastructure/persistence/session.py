from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.paths import data_dir

DB_PATH = data_dir() / "optcg.db"

engine: Engine = create_engine(
    f"sqlite:///{DB_PATH}",
    echo=False,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    from app.infrastructure.persistence.models import Base
    Base.metadata.create_all(engine)
