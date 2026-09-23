from __future__ import annotations

from collections import OrderedDict
from typing import Any

from sqlalchemy import text

from app.db import engine
from app.services.parts_finder import VIN_YEAR_CODES
from app.services.vin_lookup import VinLookupError, lookup_vin


def _local_vehicle(vin: str) -> dict[str, Any] | None:
    query = text(
        """
        SELECT v.id, v.make, v.model, v.year_from, v.year_to
        FROM vin_patterns vp
        JOIN vehicles v ON v.id = vp.vehicle_id
        WHERE upper(vp.wmi) = substr(:vin, 1, 3)
          AND upper(vp.vds_pattern) = substr(:vin, 4, 5)
        LIMIT 1
        """
    )
    with engine.begin() as connection:
        row = connection.execute(query, {"vin": vin}).mappings().first()
    if not row:
        return None

    model_year = VIN_YEAR_CODES.get(vin[9])
    if model_year is not None and not (row["year_from"] <= model_year <= row["year_to"]):
        return None
    return dict(row) | {"model_year": model_year}


def _catalog_vehicle(make: str, model: str, year: int | None) -> dict[str, Any] | None:
    query = text(
        """
        SELECT id, make, model, year_from, year_to
        FROM vehicles
        WHERE lower(make) = lower(:make)
          AND lower(model) = lower(:model)
          AND (:year IS NULL OR (year_from <= :year AND year_to >= :year))
        ORDER BY year_from
        LIMIT 1
        """
    )
    with engine.begin() as connection:
        row = connection.execute(query, {"make": make, "model": model, "year": year}).mappings().first()
    return dict(row) if row else None


def _fitted_parts(vehicle_id: Any, model_year: int | None) -> list[dict[str, Any]]:
    query = text(
        """
        SELECT p.id AS part_id, p.part_number, p.brand, p.name, p.category, p.part_type,
               sp.id AS supplier_part_id, s.name AS supplier_name, sp.price,
               sp.currency_code, sp.stock, sp.lead_time_days
        FROM part_fitments pf
        JOIN parts p ON p.id = pf.part_id
        LEFT JOIN supplier_parts sp ON sp.part_id = p.id
        LEFT JOIN suppliers s ON s.id = sp.supplier_id AND s.is_active = true
        WHERE pf.vehicle_id = :vehicle_id
          AND (:year IS NULL OR (pf.year_from <= :year AND pf.year_to >= :year))
          AND (sp.id IS NULL OR s.id IS NOT NULL)
        ORDER BY p.name, sp.stock DESC NULLS LAST, sp.lead_time_days ASC NULLS LAST, sp.price ASC NULLS LAST
        """
    )
    with engine.begin() as connection:
        return [dict(row) for row in connection.execute(query, {"vehicle_id": vehicle_id, "year": model_year}).mappings().all()]


def _alternatives(part_ids: list[Any]) -> dict[Any, list[dict[str, Any]]]:
    if not part_ids:
        return {}
    query = text(
        """
        SELECT pa.part_id, ap.id AS alternative_part_id, ap.name, ap.brand,
               sp.id AS supplier_part_id, s.name AS supplier_name, sp.price,
               sp.currency_code, sp.stock, sp.lead_time_days
        FROM part_alternatives pa
        JOIN parts ap ON ap.id = pa.alternative_part_id
        LEFT JOIN supplier_parts sp ON sp.part_id = ap.id
        LEFT JOIN suppliers s ON s.id = sp.supplier_id AND s.is_active = true
        WHERE pa.part_id = ANY(:part_ids)
          AND (sp.id IS NULL OR s.id IS NOT NULL)
        ORDER BY ap.name, sp.stock DESC NULLS LAST, sp.price ASC NULLS LAST
        """
    )
    with engine.begin() as connection:
        rows = connection.execute(query, {"part_ids": part_ids}).mappings().all()

    result: dict[Any, list[dict[str, Any]]] = {}
    for row in rows:
        result.setdefault(row["part_id"], []).append(dict(row))
    return result


def _offer(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "supplier_name": row["supplier_name"],
        "supplier_part_id": str(row["supplier_part_id"]),
        "price": str(row["price"]),
        "currency_code": row["currency_code"].strip(),
        "stock": row["stock"],
        "lead_time_days": row["lead_time_days"],
    }


def find_parts_by_vin(vin: str) -> dict[str, Any] | None:
    normalized_vin = vin.strip().upper()
    local = _local_vehicle(normalized_vin)
    decode_source = "local"

    if local:
        vehicle = local
        model_year = local["model_year"]
    else:
        try:
            decoded = lookup_vin(normalized_vin)
        except (VinLookupError, ValueError):
            return None
        decoded_vehicle = decoded["vehicle"]
        try:
            model_year = int(decoded_vehicle["model_year"]) if decoded_vehicle.get("model_year") else None
        except (TypeError, ValueError):
            model_year = None
        vehicle = _catalog_vehicle(decoded_vehicle["make"], decoded_vehicle["model"], model_year)
        decode_source = "nhtsa"
        if not vehicle:
            return {
                "vin": normalized_vin,
                "decode_source": decode_source,
                "catalog_match": False,
                "vehicle": {"make": decoded_vehicle["make"], "model": decoded_vehicle["model"], "model_year": model_year},
                "parts": [],
                "message": "We don't have parts fitment data for this vehicle.",
            }

    rows = _fitted_parts(vehicle["id"], model_year)
    grouped: OrderedDict[Any, dict[str, Any]] = OrderedDict()
    for row in rows:
        part = grouped.setdefault(
            row["part_id"],
            {
                "part_id": str(row["part_id"]),
                "part_number": row["part_number"],
                "brand": row["brand"],
                "name": row["name"],
                "category": row["category"],
                "part_type": row["part_type"],
                "offers": [],
            },
        )
        if row["supplier_part_id"] is not None:
            part["offers"].append(_offer(row))

    alternatives = _alternatives(list(grouped))
    for part_id, part in grouped.items():
        part["in_stock"] = any(offer["stock"] > 0 for offer in part["offers"])
        alternative_parts: OrderedDict[Any, dict[str, Any]] = OrderedDict()
        for row in alternatives.get(part_id, []):
            alternative = alternative_parts.setdefault(
                row["alternative_part_id"],
                {"part_id": str(row["alternative_part_id"]), "name": row["name"], "brand": row["brand"], "offers": []},
            )
            if row["supplier_part_id"] is not None:
                alternative["offers"].append(_offer(row))
        part["alternatives"] = list(alternative_parts.values())

    return {
        "vin": normalized_vin,
        "decode_source": decode_source,
        "catalog_match": True,
        "vehicle": {"make": vehicle["make"], "model": vehicle["model"], "model_year": model_year},
        "parts": list(grouped.values()),
    }