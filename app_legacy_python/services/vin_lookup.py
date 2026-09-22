from __future__ import annotations

import json
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

VIN_PATTERN = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")
VPIC_URL = "https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValuesExtended/{vin}?format=json"
RECALLS_URL = "https://api.nhtsa.gov/recalls/recallsByVin/{vin}?format=json"


class VinLookupError(ValueError):
    pass


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
