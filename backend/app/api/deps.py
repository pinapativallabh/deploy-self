from typing import Generator

def get_db() -> Generator[None, None, None]:
    """
    Dependency generator for database sessions.
    Returns None for now as Postgres is not yet wired in.
    """
    try:
        yield None
    finally:
        pass
