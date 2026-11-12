"""SQLAlchemy Session Lifecycle and Engine Setup."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import get_settings
from app.core.paths import ensure_app_dirs

ensure_app_dirs()
settings = get_settings()
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    """Ensure declared tables and migrated columns exist in the database."""
    from app.models import entities as _  # noqa: F401
    Base.metadata.create_all(bind=engine)
    if "sqlite" in settings.DATABASE_URL:
        from sqlalchemy import text
        with engine.connect() as conn:
            for stmt in [
                "ALTER TABLE targets ADD COLUMN project_path VARCHAR",
                "ALTER TABLE scans ADD COLUMN test_plan JSON",
                "ALTER TABLE scans ADD COLUMN category_results JSON DEFAULT '[]'",
                "ALTER TABLE scan_turns ADD COLUMN category VARCHAR DEFAULT 'UNKNOWN'",
                "ALTER TABLE scan_turns ADD COLUMN attempt_in_category INTEGER DEFAULT 0",
            ]:
                try:
                    conn.execute(text(stmt))
                    conn.commit()
                except Exception:
                    pass


# Ensure schema is initialized when init_db() is called by the application lifespan



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
