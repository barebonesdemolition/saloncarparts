import os
import traceback
import google.generativeai as genai
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.db import get_db
from app import models
from app.config import get_settings

router = APIRouter(prefix="/api/ai", tags=["AI Assistant"])

settings = get_settings()
GEMINI_API_KEY = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


class ChatRequest(BaseModel):
    message: str
    history: List[dict] = []


@router.post("/chat")
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="AI not configured. Set GEMINI_API_KEY.")

    vehicles_result = await db.execute(
        select(models.VehicleListing).where(models.VehicleListing.is_sold == False).limit(20)
    )
    vehicles = vehicles_result.scalars().all()

    parts_result = await db.execute(select(models.PartListing).limit(20))
    parts = parts_result.scalars().all()

    vehicle_summary = "\n".join([
        f"- {v.title} | {v.year} | {v.transmission} | {v.fuel_type} | "
        f"SLL {int(v.price_sll):,} | {v.location} | Phone: {v.contact_phone or 'N/A'}"
        for v in vehicles
    ]) or "No vehicles currently listed."

    part_summary = "\n".join([
        f"- {p.name} | {p.category} | {p.condition} | SLL {int(p.price_sll):,} | {p.location}"
        for p in parts
    ]) or "No parts currently listed."

    system_prompt = f"""You are the Salon AutoZone AI Assistant for Sierra Leone's #1 automotive marketplace.

You help buyers and sellers with:
- Finding cars and parts from the marketplace
- VIN decoding explanations
- Advice on buying used cars in Sierra Leone
- Recommending cars based on budget, use case, and location

CURRENT MARKETPLACE INVENTORY:

Vehicles:
{vehicle_summary}

Parts:
{part_summary}

Guidelines:
- Prices are in Sierra Leone Leone (SLL). 1 USD is about 23,000 SLL in 2026.
- Common cities: Freetown, Bo, Kenema, Makeni, Koidu
- When recommending, mention specific cars from the inventory above
- Mention seller phone numbers when relevant
- Keep answers SHORT (2-3 paragraphs max)
- Be warm, helpful, and human
"""

    try:
        model = genai.GenerativeModel(
            model_name="gemini-3.6-flash",
            system_instruction=system_prompt,
        )

        chat_history = []
        for h in request.history[-10:]:
            role = "user" if h.get("role") == "user" else "model"
            chat_history.append({"role": role, "parts": [h.get("content", "")]})

        chat_session = model.start_chat(history=chat_history)
        response = chat_session.send_message(request.message)

        return {"reply": response.text, "success": True}
    except Exception as e:
        error_detail = f"{type(e).__name__}: {str(e)}"
        print("=" * 60)
        print("AI CHAT ERROR:", error_detail)
        print(traceback.format_exc())
        print("=" * 60)
        raise HTTPException(status_code=500, detail=error_detail)


@router.get("/status")
async def ai_status():
    return {
        "configured": bool(GEMINI_API_KEY),
        "model": "gemini-3.6-flash",
        "key_prefix": GEMINI_API_KEY[:5] if GEMINI_API_KEY else "none",
        "key_length": len(GEMINI_API_KEY) if GEMINI_API_KEY else 0,
    }
