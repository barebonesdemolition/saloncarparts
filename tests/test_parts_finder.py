from fastapi.testclient import TestClient

from app.main import app
from app.services.parts_finder import find_recommendations


def test_find_recommendations_returns_ranked_parts(monkeypatch):
    rows = [
        {
            "vehicle_id": "veh-1",
            "part_id": "part-1",
            "brand": "Toyota",
            "name": "Front brake pad set",
            "category": "brakes",
            "part_type": "oem",
            "supplier_part_id": "sp-1",
            "supplier_name": "Freetown Auto Parts",
            "price": "480.00",
            "currency_code": "NLE",
            "stock": 6,
            "lead_time_days": 0,
            "availability_status": "in_stock",
            "recommendation_rank": 1,
        }
    ]

    monkeypatch.setattr("app.services.parts_finder.fetch_all", lambda *args, **kwargs: rows)

    result = find_recommendations("JTDBR32E173000001")

    assert len(result) == 1
    assert result[0]["part_name"] == "Front brake pad set"
    assert result[0]["supplier_name"] == "Freetown Auto Parts"
    assert result[0]["price"] == "480.00"


def test_parts_finder_route_returns_json(monkeypatch):
    rows = [
        {
            "vehicle_id": "veh-1",
            "part_id": "part-1",
            "brand": "Toyota",
            "name": "Front brake pad set",
            "category": "brakes",
            "part_type": "oem",
            "supplier_part_id": "sp-1",
            "supplier_name": "Freetown Auto Parts",
            "price": "480.00",
            "currency_code": "NLE",
            "stock": 6,
            "lead_time_days": 0,
            "availability_status": "in_stock",
            "recommendation_rank": 1,
        }
    ]

    monkeypatch.setattr("app.main.find_recommendations", lambda vin, limit=10, make=None, model=None, year=None: rows)

    client = TestClient(app)
    response = client.get("/api/parts-finder?vin=JTDBR32E173000001")

    assert response.status_code == 200
    assert response.json()[0]["name"] == "Front brake pad set"
    assert response.json()[0]["supplier_name"] == "Freetown Auto Parts"


def test_parts_finder_falls_back_to_manual_vehicle_lookup(monkeypatch):
    rows = [
        {
            "vehicle_id": "veh-1",
            "part_id": "part-1",
            "brand": "Toyota",
            "name": "Front brake pad set",
            "category": "brakes",
            "part_type": "oem",
            "supplier_part_id": "sp-1",
            "supplier_name": "Freetown Auto Parts",
            "price": "480.00",
            "currency_code": "NLE",
            "stock": 6,
            "lead_time_days": 0,
            "availability_status": "in_stock",
            "recommendation_rank": 1,
        }
    ]

    monkeypatch.setattr("app.services.parts_finder.fetch_all", lambda vin=None, make=None, model=None, year=None, limit=10: rows)

    result = find_recommendations(vin="", make="Toyota", model="Corolla", year=2007)

    assert result[0]["part_name"] == "Front brake pad set"
    assert result[0]["supplier_name"] == "Freetown Auto Parts"


def test_parts_finder_requires_vin_or_vehicle_details():
    client = TestClient(app)
    response = client.get("/api/parts-finder")

    assert response.status_code == 400
    assert "Provide a VIN" in response.json()["detail"]


def test_parts_by_vin_route_returns_fitment_payload(monkeypatch):
    monkeypatch.setattr(
        "app.main.find_parts_by_vin",
        lambda vin: {
            "vin": vin,
            "decode_source": "local",
            "catalog_match": True,
            "vehicle": {"make": "Toyota", "model": "Corolla", "model_year": 2007},
            "parts": [],
        },
    )

    response = TestClient(app).get("/api/parts/by-vin/jtdbr32e173000001")

    assert response.status_code == 200
    assert response.json()["vin"] == "JTDBR32E173000001"
    assert response.json()["vehicle"]["model"] == "Corolla"


def test_parts_by_vin_rejects_malformed_vin():
    response = TestClient(app).get("/api/parts/by-vin/TOOSHORT")

    assert response.status_code == 400
    assert response.json() == {"error": "invalid_vin"}


def test_parts_by_vin_returns_machine_readable_not_found(monkeypatch):
    monkeypatch.setattr("app.main.find_parts_by_vin", lambda vin: None)

    response = TestClient(app).get("/api/parts/by-vin/1NXBR32E205123456")

    assert response.status_code == 404
    assert response.json() == {"error": "vehicle_not_found"}


def test_parts_by_vin_returns_stable_internal_error(monkeypatch):
    def fail(vin):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr("app.main.find_parts_by_vin", fail)

    response = TestClient(app).get("/api/parts/by-vin/1NXBR32E205123456")

    assert response.status_code == 500
    assert response.json() == {"error": "internal_error", "message": "Something went wrong."}


def test_vin_lookup_route_returns_decoded_vehicle(monkeypatch):
    monkeypatch.setattr(
        "app.main.lookup_vin",
        lambda vin: {
            "vin": vin,
            "source": "NHTSA vPIC",
            "vehicle": {"make": "Toyota", "model": "Corolla", "model_year": "2007"},
            "recalls": [],
            "recalls_available": False,
        },
    )

    response = TestClient(app).get("/api/vin-lookup?vin=JTDBR32E173000001")

    assert response.status_code == 200
    assert response.json()["vehicle"]["model"] == "Corolla"
    assert response.json()["recalls"] == []


def test_vin_lookup_rejects_invalid_vin():
    response = TestClient(app).get("/api/vin-lookup?vin=invalid")

    assert response.status_code == 422


def test_dynamic_vin_lookup_returns_success_envelope(monkeypatch):
    async def fake_decode(vin):
        return {"vin": vin, "make": "Toyota", "model": "Corolla"}

    monkeypatch.setattr("app.main.decode_vin", fake_decode)

    response = TestClient(app).get("/api/vin/lookup/jtdbr32e173000001")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "data": {"vin": "JTDBR32E173000001", "make": "Toyota", "model": "Corolla"},
    }


def test_dynamic_vin_lookup_rejects_wrong_length():
    response = TestClient(app).get("/api/vin/lookup/TOOSHORT")

    assert response.status_code == 400
    assert response.json()["detail"] == "VIN must be exactly 17 characters."


def test_dynamic_vin_lookup_maps_decoder_value_error(monkeypatch):
    async def fake_decode(vin):
        raise ValueError("Could not decode VIN.")

    monkeypatch.setattr("app.main.decode_vin", fake_decode)

    response = TestClient(app).get("/api/vin/lookup/1NXBR32E205123456")

    assert response.status_code == 422
    assert response.json()["detail"] == "Could not decode VIN."


def test_dynamic_vin_lookup_maps_unexpected_error(monkeypatch):
    async def fake_decode(vin):
        raise RuntimeError("service unavailable")

    monkeypatch.setattr("app.main.decode_vin", fake_decode)

    response = TestClient(app).get("/api/vin/lookup/1NXBR32E205123456")

    assert response.status_code == 502
    assert response.json()["detail"] == "NHTSA lookup service unavailable."


def test_vin_suggestions_route(monkeypatch):
    monkeypatch.setattr(
        "app.main.suggest_vehicles_by_vin",
        lambda vin: [{
            "make": "Toyota",
            "model": "Corolla",
            "year_from": 2003,
            "year_to": 2008,
            "matched_prefix": "JTDBR32E",
            "confidence": 0.71,
        }],
    )

    response = TestClient(app).get("/api/vin-suggestions?vin=JTDBR32E")

    assert response.status_code == 200
    assert response.json()[0]["make"] == "Toyota"
    assert response.json()[0]["model"] == "Corolla"


def test_part_order_checkout_route(monkeypatch):
    order_payload = {
        "order_id": "ord-1",
        "buyer_id": "buyer-1",
        "supplier_part_id": "sp-1",
        "quantity": 1,
        "payment_method": "mobile_money",
        "delivery_address": "Freetown",
        "status": "pending",
        "total_amount": "480.00",
        "currency_code": "NLE",
    }

    monkeypatch.setattr("app.main.create_part_order", lambda **kwargs: order_payload)

    client = TestClient(app)
    response = client.post(
        "/api/orders/parts",
        json={
            "buyer_id": "buyer-1",
            "supplier_part_id": "sp-1",
            "quantity": 1,
            "payment_method": "mobile_money",
            "delivery_address": "Freetown",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    assert response.json()["currency_code"] == "NLE"
    assert response.json()["total_amount"] == "480.00"


def test_order_payment_confirmation_route(monkeypatch):
    payment_payload = {
        "order_id": "ord-1",
        "buyer_id": "buyer-1",
        "status": "confirmed",
        "payment_status": "paid",
        "payment_reference": "manual-123",
        "total_amount": "480.00",
        "currency_code": "NLE",
    }
    monkeypatch.setattr("app.main.confirm_order_payment", lambda **kwargs: payment_payload)

    response = TestClient(app).post(
        "/api/orders/ord-1/confirm-payment",
        json={"payment_reference": "manual-123"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"
    assert response.json()["payment_status"] == "paid"


def test_order_status_route(monkeypatch):
    order_payload = {
        "order_id": "ord-1",
        "buyer_id": "buyer-1",
        "status": "pending",
        "payment_status": "unpaid",
        "payment_method": "mobile_money",
        "delivery_address": "Freetown",
        "total_amount": "480.00",
        "currency_code": "NLE",
        "item": {"supplier_part_id": "sp-1", "quantity": 1, "fulfillment_status": "pending"},
    }
    monkeypatch.setattr("app.main.get_part_order", lambda **kwargs: order_payload)

    response = TestClient(app).get("/api/orders/ord-1")

    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    assert response.json()["item"]["fulfillment_status"] == "pending"


def test_fulfillment_update_route(monkeypatch):
    fulfillment_payload = {
        "order_id": "ord-1",
        "status": "completed",
        "payment_status": "paid",
        "fulfillment_status": "delivered",
    }
    monkeypatch.setattr("app.main.update_fulfillment_status", lambda **kwargs: fulfillment_payload)

    response = TestClient(app).patch(
        "/api/orders/ord-1/fulfillment",
        json={"fulfillment_status": "delivered"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["fulfillment_status"] == "delivered"


def test_vehicle_catalog_route(monkeypatch):
    monkeypatch.setattr(
        "app.main.list_vehicle_catalog",
        lambda: [{"make": "Toyota", "model": "Corolla", "year_from": 2003, "year_to": 2008}],
    )

    response = TestClient(app).get("/api/vehicles")

    assert response.status_code == 200
    assert response.json()[0]["model"] == "Corolla"


def test_vehicle_listing_creation_route(monkeypatch):
    listing_payload = {
        "listing_id": "lst-1",
        "seller_id": "seller-1",
        "make": "Toyota",
        "model": "Corolla",
        "year": 2007,
        "price": "95000.00",
        "currency_code": "NLE",
        "condition": "used",
        "status": "active",
    }

    monkeypatch.setattr("app.main.create_vehicle_listing", lambda **kwargs: listing_payload)

    client = TestClient(app)
    response = client.post(
        "/api/listings/sell",
        json={
            "seller_id": "seller-1",
            "make": "Toyota",
            "model": "Corolla",
            "year": 2007,
            "price": "95000.00",
            "currency_code": "NLE",
            "condition": "used",
            "vin": "JTDBR32E173000001",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "active"
    assert response.json()["make"] == "Toyota"
    assert response.json()["model"] == "Corolla"
