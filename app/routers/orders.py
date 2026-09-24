from fastapi import APIRouter
router = APIRouter(prefix="/orders", tags=["Orders"])

@router.get("/test")
async def test_orders():
    return {"message": "Orders router is working"}
