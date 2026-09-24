from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, func
from typing import Optional, List

from app.db import get_db
from app import models

router = APIRouter(prefix="/api/unified", tags=["Unified Search"])


@router.get("/parts")
async def unified_parts_search(
    q: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    make: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    include_catalog: bool = Query(True, description="Include supplier catalog (importable) parts"),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """
    Unified parts search that returns:
    - Local parts (available immediately)
    - Supplier catalog parts (importable from abroad)
    """
    local_parts = []
    catalog_parts = []

    # --- Local parts (PartListing) ---
    local_query = select(models.PartListing)
    if category:
        local_query = local_query.where(models.PartListing.category.ilike(f"%{category}%"))
    if make:
        local_query = local_query.where(models.PartListing.compatible_make.ilike(f"%{make}%"))
    if model:
        local_query = local_query.where(models.PartListing.compatible_model.ilike(f"%{model}%"))
    if location:
        local_query = local_query.where(models.PartListing.location.ilike(f"%{location}%"))
    if q:
        local_query = local_query.where(
            or_(
                models.PartListing.name.ilike(f"%{q}%"),
                models.PartListing.category.ilike(f"%{q}%"),
                models.PartListing.compatible_make.ilike(f"%{q}%"),
                models.PartListing.compatible_model.ilike(f"%{q}%"),
            )
        )
    local_query = local_query.limit(limit)
    result = await db.execute(local_query)
    for p in result.scalars().all():
        local_parts.append({
            "type": "local",
            "id": p.id,
            "name": p.name,
            "category": p.category,
            "compatible_make": p.compatible_make,
            "compatible_model": p.compatible_model,
            "price_sll": p.price_sll,
            "stock_quantity": p.stock_quantity,
            "condition": p.condition,
            "location": p.location,
            "image_url": p.image_url,
            "url": f"/part/{p.id}",
            "badge": "🇸🇱 Local Stock",
        })

    # --- Supplier catalog parts (importable) ---
    if include_catalog:
        cat_query = select(models.SupplierCatalog)
        if category:
            cat_query = cat_query.where(models.SupplierCatalog.category.ilike(f"%{category}%"))
        if q:
            cat_query = cat_query.where(
                or_(
                    models.SupplierCatalog.part_number.ilike(f"%{q}%"),
                    models.SupplierCatalog.vehicle_compatibility.ilike(f"%{q}%"),
                    models.SupplierCatalog.category.ilike(f"%{q}%"),
                )
            )
        if make:
            cat_query = cat_query.where(models.SupplierCatalog.vehicle_compatibility.ilike(f"%{make}%"))
        if model:
            cat_query = cat_query.where(models.SupplierCatalog.vehicle_compatibility.ilike(f"%{model}%"))
        cat_query = cat_query.limit(limit)
        result = await db.execute(cat_query)
        for c in result.scalars().all():
            catalog_parts.append({
                "type": "catalog",
                "id": c.id,
                "part_number": c.part_number,
                "name": f"{c.category or 'Part'} — {c.vehicle_compatibility or 'Universal'}",
                "category": c.category,
                "vehicle_compatibility": c.vehicle_compatibility,
                "brand_1": c.brand_1,
                "price_sll": c.price_1_sll,
                "price_cad": c.price_1_cad,
                "url": f"/catalog/{c.id}",
                "badge": "🌍 Import Available",
            })

    return {
        "query": q,
        "local_count": len(local_parts),
        "catalog_count": len(catalog_parts),
        "total": len(local_parts) + len(catalog_parts),
        "local_parts": local_parts,
        "catalog_parts": catalog_parts,
    }


@router.get("/suggest")
async def unified_suggest(
    q: str = Query(..., min_length=1),
    limit: int = Query(8, le=20),
    db: AsyncSession = Depends(get_db),
):
    """Predictive search that includes both local parts and catalog."""
    q_lower = q.lower().strip()
    suggestions = []

    # Local parts
    local_query = select(models.PartListing).where(
        or_(
            models.PartListing.name.ilike(f"%{q_lower}%"),
            models.PartListing.category.ilike(f"%{q_lower}%"),
            models.PartListing.compatible_make.ilike(f"%{q_lower}%"),
        )
    ).limit(limit)

    result = await db.execute(local_query)
    for p in result.scalars().all():
        suggestions.append({
            "type": "local",
            "label": p.name,
            "sublabel": f"SLL {int(p.price_sll):,} • {p.category} • {p.location}",
            "url": f"/part/{p.id}",
            "icon": "🔧",
        })

    # Catalog parts
    cat_query = select(models.SupplierCatalog).where(
        or_(
            models.SupplierCatalog.part_number.ilike(f"%{q_lower}%"),
            models.SupplierCatalog.vehicle_compatibility.ilike(f"%{q_lower}%"),
            models.SupplierCatalog.category.ilike(f"%{q_lower}%"),
        )
    ).limit(limit)

    result = await db.execute(cat_query)
    for c in result.scalars().all():
        suggestions.append({
            "type": "catalog",
            "label": f"{c.part_number} — {c.vehicle_compatibility or c.category or 'Part'}",
            "sublabel": f"🌍 Import from abroad • {c.category or 'Part'}",
            "url": f"/catalog/{c.id}",
            "icon": "🌍",
        })

    # Also search vehicles
    veh_query = select(models.VehicleListing).where(
        models.VehicleListing.is_sold == False
    ).where(
        or_(
            models.VehicleListing.title.ilike(f"%{q_lower}%"),
            models.VehicleListing.make.ilike(f"%{q_lower}%"),
        )
    ).limit(3)

    result = await db.execute(veh_query)
    for v in result.scalars().all():
        suggestions.append({
            "type": "vehicle",
            "label": v.title,
            "sublabel": f"SLL {int(v.price_sll):,} • {v.location}",
            "url": f"/vehicle/{v.id}",
            "icon": "🚗",
        })

    return {"query": q, "suggestions": suggestions[:limit]}


@router.get("/catalog/{part_id}")
async def get_catalog_part(part_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single catalog part with full details + search for compatible vehicles."""
    result = await db.execute(
        select(models.SupplierCatalog).where(models.SupplierCatalog.id == part_id)
    )
    part = result.scalars().first()
    if not part:
        raise HTTPException(status_code=404, detail="Catalog part not found")

    return {
        "id": part.id,
        "part_number": part.part_number,
        "category": part.category,
        "vehicle_compatibility": part.vehicle_compatibility,
        "brand_1": part.brand_1,
        "price_1_sll": part.price_1_sll,
        "price_1_cad": part.price_1_cad,
        "in_stock": part.in_stock,
        "supplier_note": "Ordered from our international supplier (typically 7-14 days)",
    }


from fastapi import HTTPException
