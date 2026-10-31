import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models_all  # noqa: F401
from app.core import ratelimit
from app.core.errors import AppError
from app.db import Base, get_db, make_engine
from app.main import create_app
from app.modules.vehicles.vpic import get_vpic
from app.seed.__main__ import run as run_seed

FORD_F150_RAW = {
    "Make": "FORD",
    "MakeID": "460",
    "Model": "F-150",
    "ModelID": "1801",
    "ModelYear": "2015",
    "DisplacementL": "3.5",
    "EngineCylinders": "6",
    "EngineConfiguration": "V-Shaped",
    "FuelTypePrimary": "Gasoline",
    "EngineModel": "",
    "Trim": "XLT",
    "DriveType": "4WD/4-Wheel Drive/4x4",
    "BodyClass": "Pickup",
    "ErrorCode": "0",
    "ErrorText": "0 - VIN decoded clean. Check Digit (9th position) is correct",
}


class FakeVpic:
    """Stands in for NHTSA so tests are fast and work offline."""

    def __init__(self):
        self.decode_calls = 0
        self.model_calls = 0
        self.decode_result = dict(FORD_F150_RAW)
        self.fail = False
        self.models = {(474, 2012): [{"Model_ID": 1863, "Model_Name": "Civic"},
                                     {"Model_ID": 1861, "Model_Name": "Accord"}]}  # fmt: skip

    def decode_vin(self, vin):
        self.decode_calls += 1
        if self.fail:
            raise AppError("upstream_unavailable", 503, source="nhtsa_vpic")
        return dict(self.decode_result)

    def models_for_make_year(self, vpic_make_id, year):
        self.model_calls += 1
        if self.fail:
            raise AppError("upstream_unavailable", 503, source="nhtsa_vpic")
        return self.models.get((vpic_make_id, year), [])


@pytest.fixture
def db_session_factory():
    engine = make_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory() as db:
        run_seed(db)
    yield factory
    engine.dispose()


@pytest.fixture
def vpic():
    return FakeVpic()


@pytest.fixture
def client(db_session_factory, vpic):
    ratelimit.reset()
    app = create_app()

    def _db():
        with db_session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_vpic] = lambda: vpic
    with TestClient(app) as c:
        yield c


def register(client, email="tech@example.com", password="correct-horse-battery", name="Tech"):
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "display_name": name, "accept_terms": True},
    )
    assert r.status_code == 201, r.text
    return r


def csrf(client) -> dict:
    return {"x-csrf-token": client.cookies.get("cc_csrf")}
