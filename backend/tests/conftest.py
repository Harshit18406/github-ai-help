import os
os.environ["DATABASE_URL"]="sqlite:///./test.db"
os.environ["SECRET_KEY"]="test-secret"
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import Base, engine

@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine); Base.metadata.create_all(bind=engine)
    yield

@pytest.fixture
def client(): return TestClient(app)
