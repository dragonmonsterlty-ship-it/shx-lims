from collections.abc import Iterator
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker


test_database_url = os.getenv("TEST_DATABASE_URL")
database_url = os.getenv("DATABASE_URL")

if not test_database_url:
    raise RuntimeError("TEST_DATABASE_URL must be set for pytest; tests refuse to use DATABASE_URL.")
if database_url and test_database_url == database_url:
    raise RuntimeError("TEST_DATABASE_URL must not be the same as DATABASE_URL.")

test_url = make_url(test_database_url)
if not test_url.drivername.startswith("sqlite") and "test" not in (test_url.database or "").lower():
    raise RuntimeError("Non-SQLite TEST_DATABASE_URL database name must contain 'test'.")

os.environ["DATABASE_URL"] = test_database_url
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough")

from app.core.deps import get_db  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import create_engine_for_url  # noqa: E402
from app.main import app  # noqa: E402
import app.models as _models  # noqa: F401,E402
from app.models.user import User  # noqa: E402


engine = create_engine_for_url(test_database_url)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)


@pytest.fixture(autouse=True)
def reset_database() -> Iterator[None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session() -> Iterator[Session]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client() -> Iterator[TestClient]:
    def override_get_db() -> Iterator[Session]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def create_user(db_session: Session):
    def _create_user(
        username: str = "admin",
        password: str = "password123",
        role: str = "admin",
        must_change_password: bool = True,
    ) -> User:
        user = User(
            username=username,
            full_name="Test Admin",
            email=None,
            password_hash=hash_password(password),
            role=role,
            department=None,
            is_active=True,
            must_change_password=must_change_password,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _create_user
