from __future__ import annotations

import json
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import httpx

VIN_PATTERN = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")
VPIC_URL = "https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValuesExtended/{vin}?format=json"
NHTSA_VIN_API_URL = "https://vpic.nhtsa.dot.gov/api/vehicles/decodevinvalues/{vin}?format=json"
RECALLS_URL = "https://api.nhtsa.gov/recalls/recallsByVin/{vin}?format=json"


class VinLookupError(ValueError):
    pass


async def decode_vin(vin: str) -> dict[str, Any]:
    """Decode a 17-character VIN using the NHTSA vPIC values endpoint."""
    cleaned_vin = vin.strip().upper()
    if len(cleaned_vin) != 17:
        raise ValueError("VIN must be exactly 17 characters long.")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(NHTSA_VIN_API_URL.format(vin=cleaned_vin))
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise VinLookupError("VIN decoder is temporarily unavailable.") from exc

    results = data.get("Results", [])[0] if data.get("Results") else {}
    make = results.get("Make")
    model = results.get("Model")
    year_value = results.get("ModelYear")

    if not make or not model or not year_value:
        raise ValueError("Could not decode vehicle details from the provided VIN.")

    try:
        year = int(year_value)
    except (TypeError, ValueError):
        year = None

    return {
        "vin": cleaned_vin,
        "make": make,
        "model": model,
        "year": year,
        "trim": results.get("Trim") or None,
        "body_class": results.get("BodyClass") or None,
        "engine_displacement": results.get("DisplacementL") or None,
        "engine_cylinders": results.get("EngineCylinders") or None,
        "drive_type": results.get("DriveType") or None,
    }


def _get_json(url: str) -> dict[str, Any]:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "Salon-AutoZone/1.0"})
    with urlopen(request, timeout=8) as response:
        return json.load(response)


def _result_values(payload: dict[str, Any]) -> dict[str, str]:
    return {
        item.get("Variable", ""): item.get("Value") or ""
        for item in payload.get("Results", [])
        if item.get("Variable")
    }


def lookup_vin(vin: str) -> dict[str, Any]:
    normalized_vin = vin.strip().upper()
    if not VIN_PATTERN.fullmatch(normalized_vin):
        raise VinLookupError("VIN must contain exactly 17 valid characters.")

    try:
        decode_payload = _get_json(VPIC_URL.format(vin=normalized_vin))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise VinLookupError("VIN decoder is temporarily unavailable.") from exc

    values = _result_values(decode_payload)
    if not values.get("Make") and not values.get("Model"):
        raise VinLookupError("No vehicle was found for this VIN.")

    recalls: list[dict[str, Any]] = []
    try:
        recall_payload = _get_json(RECALLS_URL.format(vin=normalized_vin))
        recalls = recall_payload.get("results", [])
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        pass

    return {
        "vin": normalized_vin,
        "source": "NHTSA vPIC",
        "vehicle": {
            "make": values.get("Make"),
            "model": values.get("Model"),
            "model_year": values.get("Model Year"),
            "trim": values.get("Trim"),
            "body_class": values.get("Body Class"),
            "engine": values.get("Engine Model"),
            "fuel_type": values.get("Fuel Type - Primary"),
            "plant_country": values.get("Plant Country"),
        },
        "recalls": recalls,
        "recalls_available": bool(recalls),
    }
