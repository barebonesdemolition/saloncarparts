from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, func, String, cast

from app.db import get_db
from app import models

router = APIRouter(prefix="/api/search", tags=["Search"])


@router.get("/suggest")
async def suggest(
    q: str = Query(..., min_length=1),
    mode: str = Query("parts"),
    limit: int = Query(8, le=20),
    db: AsyncSession = Depends(get_db),
):
    q_lower = q.lower().strip()
    suggestions = []

    try:
        if mode == "vehicles":
            query = select(models.VehicleListing).where(
                models.VehicleListing.is_sold == False
            ).where(
                or_(
                    models.VehicleListing.title.ilike(f"%{q_lower}%"),
                    models.VehicleListing.make.ilike(f"%{q_lower}%"),
                    models.VehicleListing.model.ilike(f"%{q_lower}%"),
                    models.VehicleListing.location.ilike(f"%{q_lower}%"),
                    cast(models.VehicleListing.year, String).ilike(f"%{q_lower}%"),
                )
            ).limit(limit)

            result = await db.execute(query)
            vehicles = result.scalars().all()

            for v in vehicles:
                suggestions.append({
                    "type": "vehicle",
                    "id": v.id,
                    "label": f"{v.title} — {v.location}",
                    "sublabel": f"SLL {int(v.price_sll):,} • {v.year} • {v.transmission}",
                    "search_text": v.title,
                    "url": f"/vehicle/{v.id}",
                })
        else:
            query = select(models.PartListing).where(
                or_(
                    models.PartListing.name.ilike(f"%{q_lower}%"),
                    models.PartListing.category.ilike(f"%{q_lower}%"),
                    models.PartListing.compatible_make.ilike(f"%{q_lower}%"),
                    models.PartListing.location.ilike(f"%{q_lower}%"),
                    models.PartListing.condition.ilike(f"%{q_lower}%"),
                )
            ).limit(limit)

            result = await db.execute(query)
            parts = result.scalars().all()

            for p in parts:
                suggestions.append({
                    "type": "part",
                    "id": p.id,
                    "label": p.name,
                    "sublabel": f"SLL {int(p.price_sll):,} • {p.category} • {p.location}",
                    "search_text": p.name,
                    "url": f"/part/{p.id}",
                })

        return {"query": q, "mode": mode, "suggestions": suggestions}

    except Exception as e:
        import traceback
        print("SEARCH ERROR:", str(e))
        print(traceback.format_exc())
        return {"query": q, "mode": mode, "suggestions": [], "error": str(e)}


@router.get("/trending")
async def trending(
    mode: str = Query("parts"),
    db: AsyncSession = Depends(get_db),
):
    try:
        if mode == "vehicles":
            result = await db.execute(
                select(models.VehicleListing.make, func.count(models.VehicleListing.id).label("count"))
                .where(models.VehicleListing.is_sold == False)
                .group_by(models.VehicleListing.make)
                .order_by(func.count(models.VehicleListing.id).desc())
                .limit(6)
            )
            rows = result.all()
            return {"trending": [{"label": r.make, "count": r.count} for r in rows]}
        else:
            result = await db.execute(
                select(models.PartListing.category, func.count(models.PartListing.id).label("count"))
                .group_by(models.PartListing.category)
                .order_by(func.count(models.PartListing.id).desc())
                .limit(6)
            )
            rows = result.all()
            return {"trending": [{"label": r.category, "count": r.count} for r in rows]}
    except Exception as e:
        return {"trending": [], "error": str(e)}
