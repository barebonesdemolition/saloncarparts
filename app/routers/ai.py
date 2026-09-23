from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models
from app.db import get_db

router = APIRouter(prefix="/api/ai", tags=["AI Assistant"])


class AIQueryRequest(BaseModel):
    user_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    prompt: str = Field(..., min_length=1)


def _detect_category(prompt: str) -> str | None:
    prompt = prompt.lower()
    if any(keyword in prompt for keyword in ("brake", "squeak", "pad", "rotor", "stopping")):
        return "brakes"
    if any(keyword in prompt for keyword in ("oil", "filter", "lubricant", "service")):
        return "engine"
    if any(keyword in prompt for keyword in ("spark", "plug", "ignition", "misfire")):
        return "ignition"
    return None


@router.post("/advisor")
def auto_zone_ai_advisor(request: AIQueryRequest, db: Session = Depends(get_db)):
    prompt = request.prompt.lower()
    detected_category = _detect_category(prompt)
    recommended_parts = []
    vehicle_info = None

    if request.vehicle_id:
        vehicle = db.query(models.Vehicle).filter(models.Vehicle.id == request.vehicle_id).first()
        if vehicle:
            vehicle_info = f"{vehicle.year_from}-{vehicle.year_to} {vehicle.make} {vehicle.model}"

    if request.vehicle_id and detected_category:
        fitments = (
            db.query(models.PartFitment)
            .filter(models.PartFitment.vehicle_id == request.vehicle_id)
            .all()
        )
        part_ids = [fitment.part_id for fitment in fitments]
        if part_ids:
            parts = (
                db.query(models.Part)
                .filter(
                    models.Part.id.in_(part_ids),
                    models.Part.category == detected_category,
                )
                .all()
            )
            for part in parts:
                supplier_part = (
                    db.query(models.SupplierPart)
                    .join(models.Supplier)
                    .filter(
                        models.SupplierPart.part_id == part.id,
                        models.SupplierPart.stock > 0,
                        models.Supplier.is_active.is_(True),
                    )
                    .order_by(
                        models.SupplierPart.stock.desc(),
                        models.SupplierPart.lead_time_days.asc(),
                        models.SupplierPart.price.asc(),
                    )
                    .first()
                )
                recommended_parts.append(
                    {
                        "part_number": part.part_number,
                        "brand": part.brand,
                        "name": part.name,
                        "category": part.category,
                        "price": float(supplier_part.price) if supplier_part else None,
                        "currency": supplier_part.currency_code.strip() if supplier_part else "NLE",
                        "in_stock": bool(supplier_part and supplier_part.stock > 0),
                    }
                )

    if recommended_parts:
        ai_reply = f"Based on your query and active vehicle ({vehicle_info or 'Selected Vehicle'}), here are the exact verified fitment parts available:"
    elif vehicle_info:
        ai_reply = f"I checked your {vehicle_info}. I can help you find parts, troubleshoot symptoms, or verify maintenance schedules. What specific issue are you experiencing?"
    else:
        ai_reply = "I'm your Salon AutoZone Diagnostic Assistant. Please select a vehicle from your garage or tell me your car's make and model so I can recommend 100% compatible parts!"

    return {
        "reply": ai_reply,
        "category_detected": detected_category,
        "parts": recommended_parts,
    }
