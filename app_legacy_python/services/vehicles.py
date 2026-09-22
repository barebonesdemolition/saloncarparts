from __future__ import annotations

from typing import Any

from sqlalchemy import text

from app.db import engine


def list_vehicle_catalog() -> list[dict[str, Any]]:
    query = text(
        """
        SELECT make, model, min(year_from) AS year_from, max(year_to) AS year_to
        FROM vehicles
        GROUP BY make, model
        ORDER BY make, model
        """
    )
    with engine.begin() as connection:
        rows = connection.execute(query).mappings().all()
    return [dict(row) for row in rows]
