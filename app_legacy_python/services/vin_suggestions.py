from __future__ import annotations

from typing import Any

from sqlalchemy import text

from app.db import engine


def suggest_vehicles_by_vin(vin: str, limit: int = 5) -> list[dict[str, Any]]:
    normalized_vin = "".join(vin.upper().split())
    if len(normalized_vin) < 3:
        return []

    query = text(
        """
        SELECT v.make,
               v.model,
               v.year_from,
               v.year_to,
               vp.wmi,
               vp.vds_pattern,
               char_length(vp.wmi || vp.vds_pattern) AS matched_prefix_length
        FROM vin_patterns vp
        JOIN vehicles v ON v.id = vp.vehicle_id
        WHERE upper(vp.wmi || vp.vds_pattern) LIKE :prefix
        ORDER BY matched_prefix_length DESC, v.make, v.model
        LIMIT :limit
        """
    )

    with engine.begin() as connection:
        rows = connection.execute(
            query,
            {"prefix": f"{normalized_vin}%", "limit": limit},
        ).mappings().all()

    return [
        {
            "make": row["make"],
            "model": row["model"],
            "year_from": row["year_from"],
            "year_to": row["year_to"],
            "matched_prefix": row["wmi"] + row["vds_pattern"],
            "confidence": round(min(0.99, 0.55 + (len(normalized_vin) * 0.02)), 2),
        }
        for row in rows
    ]
