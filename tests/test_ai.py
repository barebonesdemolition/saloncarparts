from decimal import Decimal
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app import models
from app.db import get_db
from app.main import app


class FakeQuery:
    def __init__(self, entity, records):
        self.entity = entity
        self.records = records

    def filter(self, *criteria):
        return self

    def join(self, *entities):
        return self

    def order_by(self, *criteria):
        return self

    def first(self):
        return self.records[0] if self.records else None

    def all(self):
        return self.records


class FakeSession:
    def __init__(self):
        self.vehicle = SimpleNamespace(
            year_from=2003,
            year_to=2008,
            make="Toyota",
            model="Corolla",
        )
        self.fitment = SimpleNamespace(part_id="part-1")
        self.part = SimpleNamespace(
            id="part-1",
            part_number="04465-02220",
            brand="Toyota",
            name="Front brake pad set",
            category="brakes",
        )
        self.offer = SimpleNamespace(
            price=Decimal("480.00"),
            currency_code="NLE",
            stock=6,
        )

    def query(self, entity):
        records = {
            models.Vehicle: [self.vehicle],
            models.PartFitment: [self.fitment],
            models.Part: [self.part],
            models.SupplierPart: [self.offer],
        }
        return FakeQuery(entity, records.get(entity, []))


def override_db():
    yield FakeSession()


def test_ai_advisor_returns_fitment_recommendation():
    app.dependency_overrides[get_db] = override_db
    try:
        response = TestClient(app).post(
            "/api/ai/advisor",
            json={
                "vehicle_id": "vehicle-1",
                "prompt": "My brakes squeak when stopping",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["category_detected"] == "brakes"
    assert body["parts"][0]["part_number"] == "04465-02220"
    assert body["parts"][0]["in_stock"] is True
    assert "Toyota Corolla" in body["reply"]


def test_ai_advisor_without_vehicle_returns_guidance():
    app.dependency_overrides[get_db] = override_db
    try:
        response = TestClient(app).post(
            "/api/ai/advisor",
            json={"prompt": "What parts do I need?"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["category_detected"] is None
    assert body["parts"] == []
    assert "Diagnostic Assistant" in body["reply"]


def test_ai_advisor_requires_prompt():
    response = TestClient(app).post("/api/ai/advisor", json={})

    assert response.status_code == 422
