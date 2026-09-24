import os
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc
from typing import Optional, List
from datetime import datetime, timedelta

from app.db import get_db
from app import models
from app.config import get_settings

router = APIRouter(prefix="/api/admin", tags=["Admin"])
settings = get_settings()


async def verify_admin(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Dependency: only admin users can pass."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Login required")

    token = authorization.replace("Bearer ", "")

    # Decode JWT
    from jose import jwt, JWTError
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")

    # Check if admin
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    return user


# ---------- ENDPOINTS ----------

@router.get("/stats")
async def admin_stats(
    admin: models.User = Depends(verify_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get overall stats for the dashboard."""
    users = await db.execute(select(func.count(models.User.id)))
    vehicles = await db.execute(
        select(func.count(models.VehicleListing.id)).where(models.VehicleListing.is_sold == False)
    )
    parts = await db.execute(select(func.count(models.PartListing.id)))
    inquiries = await db.execute(select(func.count(models.Inquiry.id)))
    new_inquiries = await db.execute(
        select(func.count(models.Inquiry.id)).where(models.Inquiry.status == "new")
    )
    import_reqs = await db.execute(
        select(func.count(models.ImportRequest.id)).where(models.ImportRequest.status == "pending")
    )
    catalog = await db.execute(select(func.count(models.SupplierCatalog.id)))

    # Activity in last 7 days
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_users = await db.execute(
        select(func.count(models.User.id)).where(models.User.created_at >= week_ago)
    )
    recent_inquiries = await db.execute(
        select(func.count(models.Inquiry.id)).where(models.Inquiry.created_at >= week_ago)
    )

    return {
        "total_users": users.scalar() or 0,
        "recent_users_7d": recent_users.scalar() or 0,
        "active_vehicles": vehicles.scalar() or 0,
        "total_parts": parts.scalar() or 0,
        "total_inquiries": inquiries.scalar() or 0,
        "new_inquiries": new_inquiries.scalar() or 0,
        "recent_inquiries_7d": recent_inquiries.scalar() or 0,
        "pending_import_requests": import_reqs.scalar() or 0,
        "supplier_catalog_size": catalog.scalar() or 0,
    }


@router.get("/users")
async def admin_users(
    admin: models.User = Depends(verify_admin),
    db: AsyncSession = Depends(get_db),
    limit: int = 100,
):
    """List all users."""
    result = await db.execute(
        select(models.User).order_by(desc(models.User.created_at)).limit(limit)
    )
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "full_name": u.full_name,
            "email": u.email,
            "phone": u.phone,
            "is_vendor": u.is_vendor,
            "roles": u.roles,
            "is_admin": u.is_admin,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@router.get("/inquiries")
async def admin_inquiries(
    admin: models.User = Depends(verify_admin),
    db: AsyncSession = Depends(get_db),
    status: Optional[str] = None,
    limit: int = 200,
):
    """List all inquiries."""
    query = select(models.Inquiry)
    if status:
        query = query.where(models.Inquiry.status == status)
    query = query.order_by(desc(models.Inquiry.created_at)).limit(limit)
    result = await db.execute(query)
    inquiries = result.scalars().all()
    return [
        {
            "id": i.id,
            "listing_type": i.listing_type,
            "listing_id": i.listing_id,
            "listing_title": i.listing_title,
            "buyer_name": i.buyer_name,
            "buyer_phone": i.buyer_phone,
            "buyer_message": i.buyer_message,
            "seller_phone": i.seller_phone,
            "status": i.status,
            "created_at": i.created_at.isoformat() if i.created_at else None,
        }
        for i in inquiries
    ]


@router.get("/import-requests")
async def admin_import_requests(
    admin: models.User = Depends(verify_admin),
    db: AsyncSession = Depends(get_db),
    limit: int = 100,
):
    """List all import requests."""
    result = await db.execute(
        select(models.ImportRequest).order_by(desc(models.ImportRequest.created_at)).limit(limit)
    )
    reqs = result.scalars().all()
    return [
        {
            "id": r.id,
            "customer_name": r.customer_name,
            "customer_phone": r.customer_phone,
            "customer_location": r.customer_location,
            "part_name": r.part_name,
            "car_make": r.car_make,
            "car_model": r.car_model,
            "car_year": r.car_year,
            "quantity": r.quantity,
            "budget_sll": r.budget_sll,
            "urgency": r.urgency,
            "notes": r.notes,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in reqs
    ]


@router.get("/activity")
async def admin_recent_activity(
    admin: models.User = Depends(verify_admin),
    db: AsyncSession = Depends(get_db),
):
    """Recent activity feed — last 10 of each type."""
    # Recent users
    result = await db.execute(
        select(models.User).order_by(desc(models.User.created_at)).limit(5)
    )
    recent_users = result.scalars().all()

    # Recent inquiries
    result = await db.execute(
        select(models.Inquiry).order_by(desc(models.Inquiry.created_at)).limit(10)
    )
    recent_inq = result.scalars().all()

    # Recent import requests
    result = await db.execute(
        select(models.ImportRequest).order_by(desc(models.ImportRequest.created_at)).limit(5)
    )
    recent_imports = result.scalars().all()

    feed = []
    for u in recent_users:
        feed.append({
            "type": "user",
            "icon": "👤",
            "text": f"New user: {u.full_name} ({u.phone})",
            "timestamp": u.created_at.isoformat() if u.created_at else None,
        })
    for i in recent_inq:
        feed.append({
            "type": "inquiry",
            "icon": "💬",
            "text": f"Inquiry from {i.buyer_name} on {i.listing_title or 'listing'}",
            "timestamp": i.created_at.isoformat() if i.created_at else None,
        })
    for r in recent_imports:
        feed.append({
            "type": "import",
            "icon": "🌍",
            "text": f"Import request: {r.part_name} for {r.car_make} {r.car_model}",
            "timestamp": r.created_at.isoformat() if r.created_at else None,
        })

    # Sort by timestamp desc
    feed.sort(key=lambda x: x["timestamp"] or "", reverse=True)
    return feed[:20]


# ---------- USER MANAGEMENT ----------

@router.post("/promote/{user_id}")
async def promote_to_admin(
    user_id: int,
    admin: models.User = Depends(verify_admin),
    db: AsyncSession = Depends(get_db),
):
    """Promote a user to admin."""
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_admin = True
    await db.commit()
    return {"message": f"{user.full_name} is now admin", "user_id": user_id}


@router.put("/inquiry/{inquiry_id}/status")
async def update_inquiry_status(
    inquiry_id: int,
    status: str,
    admin: models.User = Depends(verify_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update inquiry status."""
    result = await db.execute(select(models.Inquiry).where(models.Inquiry.id == inquiry_id))
    inq = result.scalars().first()
    if not inq:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    inq.status = status
    await db.commit()
    return {"message": "Updated", "id": inquiry_id, "status": status}


@router.put("/import-request/{req_id}/status")
async def update_import_status(
    req_id: int,
    status: str,
    admin: models.User = Depends(verify_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update import request status."""
    result = await db.execute(
        select(models.ImportRequest).where(models.ImportRequest.id == req_id)
    )
    req = result.scalars().first()
    if not req:
        raise HTTPException(status_code=404, detail="Import request not found")
    req.status = status
    await db.commit()
    return {"message": "Updated", "id": req_id, "status": status}


# ---------- ONE-TIME SETUP ENDPOINT ----------
@router.post("/promote-first-admin")
async def promote_first_admin(
    email: str,
    key: str,
    db: AsyncSession = Depends(get_db),
):
    """
    One-time setup endpoint to promote a user to admin on a fresh DB.
    Requires a secret SETUP_KEY env var. Should be disabled after setup.
    """
    expected_key = os.getenv("SETUP_KEY", "")
    if not expected_key:
        raise HTTPException(status_code=403, detail="Setup not enabled. Set SETUP_KEY env var.")
    if key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid setup key.")

    result = await db.execute(select(models.User).where(models.User.email == email))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {email} not found. Register first.")

    user.is_admin = True
    await db.commit()
    await db.refresh(user)
    return {
        "message": f"{user.full_name} is now ADMIN",
        "user_id": user.id,
        "email": user.email,
        "is_admin": user.is_admin,
    }
