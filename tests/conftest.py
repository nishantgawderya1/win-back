import os
import sys
import tempfile
from pathlib import Path

# Ensure the repo root is importable so `import backend...` works under pytest.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Point the suite at a throwaway database BEFORE backend.config is imported —
# the async engine is built at import time from this value, and an environment
# variable outranks the .env file in pydantic-settings.
#
# Without this, tests that exercise a node (every node logs an audit row) write
# into the developer's real winback.db, and pass only because that file happens
# to exist with the right schema. Deleting it broke the suite for reasons that
# had nothing to do with the code under test.
_TEST_DB = Path(tempfile.gettempdir()) / "winback_test.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB.as_posix()}"

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402

from backend.db.models import Base  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _test_schema():
    """Create the schema once per session, on a fresh file.

    Built through a synchronous engine deliberately: creating it with the async
    engine would bind aiosqlite to whichever event loop the fixture ran on, and
    later tests run on their own loops.
    """
    _TEST_DB.unlink(missing_ok=True)
    engine = create_engine(f"sqlite:///{_TEST_DB}")
    Base.metadata.create_all(engine)
    engine.dispose()
    yield
    _TEST_DB.unlink(missing_ok=True)
