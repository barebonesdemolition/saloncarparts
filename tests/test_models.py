from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import Order, OrderItem, User, Vehicle


def test_orm_models_match_seeded_schema():
    assert set(User.metadata.tables) == {
        "users",
        "user_cars",
        "vehicles",
        "vin_patterns",
        "parts",
        "part_fitments",
        "part_alternatives",
        "suppliers",
        "supplier_parts",
        "listings",
        "listing_photos",
        "orders",
        "order_items",
    }

    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(User)) > 0
        assert session.scalar(select(func.count()).select_from(Vehicle)) > 0
        assert session.scalar(select(func.count()).select_from(Order)) > 0
        assert session.scalar(select(func.count()).select_from(OrderItem)) > 0
