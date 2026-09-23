from __future__ import annotations

from typing import Any

from sqlalchemy import text

from app.db import engine


VIN_YEAR_CODES = {
    'A': 2010, 'B': 2011, 'C': 2012, 'D': 2013, 'E': 2014, 'F': 2015, 'G': 2016,
    'H': 2017, 'J': 2018, 'K': 2019, 'L': 2020, 'M': 2021, 'N': 2022, 'P': 2023,
    'R': 2024, 'S': 2025, 'T': 2026, 'V': 2027, 'W': 2028, 'X': 2029, 'Y': 2030,
    '1': 2001, '2': 2002, '3': 2003, '4': 2004, '5': 2005, '6': 2006, '7': 2007,
    '8': 2008, '9': 2009,
}


def _vin_model_year(vin: str) -> int | None:
    if len(vin) < 10:
        return None
    code = vin[9].upper()
    return VIN_YEAR_CODES.get(code)


def fetch_all(vin: str | None = None, make: str | None = None, model: str | None = None, year: int | None = None, limit: int = 10):
    normalized_vin = (vin or "").strip().upper()
    if normalized_vin:
        model_year = _vin_model_year(normalized_vin)
        if model_year is None:
            return []
        vehicle_condition = text("""
            FROM vin_patterns vp
            JOIN vehicles v ON v.id = vp.vehicle_id
            WHERE vp.wmi = upper(substr(:vin, 1, 3))
            AND vp.vds_pattern = upper(substr(:vin, 4, 5))
            LIMIT 1
        """)
        params = {"vin": normalized_vin, "model_year": model_year, "limit": limit}
    elif make and model and year:
        model_year = year
        vehicle_condition = text("""
            FROM vehicles v
            WHERE lower(v.make) = lower(:make)
              AND lower(v.model) = lower(:model)
              AND v.year_from <= :model_year
              AND v.year_to >= :model_year
            LIMIT 1
        """)
        params = {"make": make, "model": model, "model_year": model_year, "limit": limit}
    else:
        return []

    query = text(
        f"""
        WITH vehicle_match AS (
            SELECT v.id AS vehicle_id, v.make, v.model
            {vehicle_condition}
        ),
        ranked_parts AS (
            SELECT pf.vehicle_id,
                   p.id AS part_id,
                   p.brand,
                   p.name,
                   p.category,
                   p.part_type,
                   sp.id AS supplier_part_id,
                   s.name AS supplier_name,
                   sp.price,
                   sp.currency_code,
                   sp.stock,
                   sp.lead_time_days,
                   CASE WHEN sp.stock > 0 THEN 'in_stock' ELSE 'out_of_stock' END AS availability_status,
                   ROW_NUMBER() OVER (
                       PARTITION BY pf.vehicle_id, p.id
                       ORDER BY sp.stock DESC, sp.lead_time_days ASC, sp.price ASC
                   ) AS recommendation_rank
            FROM vehicle_match vm
            JOIN part_fitments pf ON pf.vehicle_id = vm.vehicle_id
            JOIN parts p ON p.id = pf.part_id
            JOIN supplier_parts sp ON sp.part_id = p.id
            JOIN suppliers s ON s.id = sp.supplier_id
            WHERE s.is_active = true
              AND pf.year_from <= :model_year
              AND pf.year_to >= :model_year
        )
        SELECT vehicle_id,
               part_id,
               brand,
               name,
               category,
               part_type,
               supplier_part_id,
               supplier_name,
               price,
               currency_code,
               stock,
               lead_time_days,
               availability_status,
               recommendation_rank
        FROM ranked_parts
        WHERE recommendation_rank = 1
        ORDER BY stock DESC, lead_time_days ASC, price ASC
        LIMIT :limit
        """
    )

    with engine.begin() as connection:
        rows = connection.execute(query, params).mappings().all()
    return [dict(row) for row in rows]


def find_recommendations(vin: str | None = None, make: str | None = None, model: str | None = None, year: int | None = None, limit: int = 10) -> list[dict[str, Any]]:
    rows = fetch_all(vin=vin, make=make, model=model, year=year, limit=limit)
    results = []
    for row in rows:
        results.append(
            {
                "vehicle_id": row.get("vehicle_id"),
                "part_id": row.get("part_id"),
                "part_name": row.get("name"),
                "brand": row.get("brand"),
                "category": row.get("category"),
                "part_type": row.get("part_type"),
                "supplier_part_id": row.get("supplier_part_id"),
                "supplier_name": row.get("supplier_name"),
                "price": row.get("price"),
                "currency_code": row.get("currency_code"),
                "stock": row.get("stock"),
                "lead_time_days": row.get("lead_time_days"),
                "availability_status": row.get("availability_status"),
                "recommendation_rank": row.get("recommendation_rank"),
            }
        )
    return results
