from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.services.nlp_parser import nlp_parser
from typing import Any

router = APIRouter()

@router.post("/scan")
async def scan_receipt(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Scans a receipt image and returns extracted data.
    """
    # Validate file type
    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(status_code=400, detail="Unsupported image format. Please use JPEG, PNG, or WebP.")
    
    try:
        image_data = await file.read()
        result = await nlp_parser.scan_receipt(image_data, file.content_type)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to scan receipt: {str(e)}")
