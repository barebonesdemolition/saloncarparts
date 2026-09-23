from app.services.parts_finder import find_recommendations
from app.services.vehicles import list_vehicle_catalog


def test_seeded_vehicle_catalog_is_available():
    catalog = list_vehicle_catalog()

    assert any(
        vehicle["make"] == "Toyota" and vehicle["model"] == "Corolla"
        for vehicle in catalog
    )


def test_seeded_vin_returns_compatible_parts():
    recommendations = find_recommendations("JTDBR32E173000001")

    assert recommendations
    assert any(part["supplier_name"] == "Freetown Auto Parts" for part in recommendations)