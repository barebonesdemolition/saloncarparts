from __future__ import annotations

from typing import Any

from sqlalchemy import text

from app.db import engine


def create_vehicle_listing(
    *,
    seller_id: str,
    make: str,
    model: str,
    year: int,
    price: str,
    currency_code: str = "NLE",
    condition: str = "used",
    vin: str | None = None,
    mileage_km: int | None = None,
    description: str | None = None,
    photo_url: str | None = None,
) -> dict[str, Any]:
    vehicle_query = text(
        """
        SELECT id, make, model, year_from, year_to
        FROM vehicles
        WHERE lower(make) = lower(:make)
          AND lower(model) = lower(:model)
          AND :year BETWEEN year_from AND year_to
        ORDER BY year_from DESC
        LIMIT 1
        """
    )
    seller_query = text("SELECT id FROM users WHERE id = CAST(:seller_id AS uuid) AND role = 'seller'")
    listing_query = text(
        """
        INSERT INTO listings (
            seller_id, vehicle_id, vin, price, currency_code, condition,
            mileage_km, description, status
        )
        VALUES (
            CAST(:seller_id AS uuid), :vehicle_id, :vin, CAST(:price AS numeric),
            :currency_code, CAST(:condition AS listing_condition),
            :mileage_km, :description, 'active'
        )
        RETURNING id, seller_id, vehicle_id, vin, price, currency_code,
                  condition, mileage_km, description, status
        """
    )
    photo_query = text(
        """
        INSERT INTO listing_photos (listing_id, url, position)
        VALUES (:listing_id, :url, 0)
        """
    )

    with engine.begin() as connection:
        seller = connection.execute(seller_query, {"seller_id": seller_id}).scalar_one_or_none()
        if seller is None:
            raise LookupError("Seller was not found or is not registered as a seller.")

        vehicle = connection.execute(
            vehicle_query,
            {"make": make.strip(), "model": model.strip(), "year": year},
        ).mappings().one_or_none()
        if vehicle is None:
            raise LookupError("No catalog vehicle matches the supplied make, model, and year.")

        listing = connection.execute(
            listing_query,
            {
                "seller_id": seller_id,
                "vehicle_id": vehicle["id"],
                "vin": vin.upper() if vin else None,
                "price": price,
                "currency_code": currency_code.upper(),
                "condition": condition.lower(),
                "mileage_km": mileage_km,
                "description": description,
            },
        ).mappings().one()
        if photo_url:
            connection.execute(
                photo_query,
                {"listing_id": listing["id"], "url": photo_url.strip()},
            )

    return {
        "listing_id": str(listing["id"]),
        "seller_id": str(listing["seller_id"]),
        "vehicle_id": str(listing["vehicle_id"]),
        "make": vehicle["make"],
        "model": vehicle["model"],
        "year": year,
        "price": str(listing["price"]),
        "currency_code": listing["currency_code"].strip(),
        "condition": listing["condition"],
        "vin": listing["vin"],
        "mileage_km": listing["mileage_km"],
        "description": listing["description"],
        "status": listing["status"],
        "photo_url": photo_url.strip() if photo_url else None,
    }
