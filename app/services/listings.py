from __future__ import annotations

from typing import Any

from sqlalchemy import text

from app.db import engine


def fetch_listings(limit: int = 10) -> list[dict[str, Any]]:
    query = text(
        """
        SELECT l.id AS listing_id,
               v.make,
               v.model,
               l.price,
               l.currency_code,
               l.condition,
               l.mileage_km,
               l.description,
               l.status,
               lp.url AS photo_url
        FROM listings l
        JOIN vehicles v ON v.id = l.vehicle_id
        LEFT JOIN LATERAL (
            SELECT url
            FROM listing_photos
            WHERE listing_id = l.id
            ORDER BY position ASC
            LIMIT 1
        ) lp ON true
        WHERE l.status = 'active'
        ORDER BY l.created_at DESC
        LIMIT :limit
        """
    )

    with engine.begin() as connection:
        rows = connection.execute(query, {"limit": limit}).mappings().all()
    return [dict(row) for row in rows]


def list_active_listings(limit: int = 10) -> list[dict[str, Any]]:
    rows = fetch_listings(limit=limit)
    return [
        {
            "listing_id": row.get("listing_id"),
            "make": row.get("make"),
            "model": row.get("model"),
            "price": str(row.get("price")) if row.get("price") is not None else None,
            "currency_code": row.get("currency_code"),
            "condition": row.get("condition"),
            "mileage_km": row.get("mileage_km"),
            "description": row.get("description"),
            "status": row.get("status"),
            "photo_url": row.get("photo_url"),
        }
        for row in rows
    ]
