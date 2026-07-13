import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

logger = logging.getLogger("dataforge.database")

# Auto-detect SQLite vs PostgreSQL to apply correct configurations
is_sqlite = settings.DATABASE_URL.startswith("sqlite")

engine_options = {}
if is_sqlite:
    # SQLite does not support connection pool checks or multiple threads natively
    engine_options["connect_args"] = {"check_same_thread": False}
    logger.info("Initializing database engine: SQLite (local fallback)")
else:
    # PostgreSQL production configurations
    engine_options["pool_pre_ping"] = True
    engine_options["pool_size"] = 10
    engine_options["max_overflow"] = 20
    logger.info("Initializing database engine: PostgreSQL")

# Create Async Engine
try:
    engine = create_async_engine(settings.DATABASE_URL, **engine_options)
except Exception as e:
    logger.critical(f"Failed to create async database engine: {e}")
    raise e

# Create Async Session factory
SessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession
)

# SQLAlchemy Declarative Base Class
class Base(DeclarativeBase):
    pass

# FastAPI Dependency for obtaining an async session
async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


def get_session_factory():
    return SessionLocal

