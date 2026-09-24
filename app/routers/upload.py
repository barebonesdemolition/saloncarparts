import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException

router = APIRouter(prefix="/api/upload", tags=["Upload"])

UPLOAD_DIR = "app/static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
MAX_SIZE = 5 * 1024 * 1024  # 5 MB


@router.post("/")
async def upload_image(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Use JPG, PNG, or WEBP. You sent: {file.content_type}"
        )

    contents = await file.read()

    if len(contents) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Max 5 MB.")

    ext = file.filename.split(".")[-1].lower()
    if ext not in ["jpg", "jpeg", "png", "webp"]:
        ext = "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(contents)

    return {
        "message": "Upload successful",
        "url": f"/static/uploads/{filename}",
        "filename": filename,
    }
