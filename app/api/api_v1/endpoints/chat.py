from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from app.schemas.chat import ChatRequest
from app.schemas.nlp import NLPTransactionResponse
from app.schemas.receipt import ReceiptScanResponse
from app.services.nlp_parser import nlp_parser
from app.services.receipt_scanner import receipt_scanner
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()

ALLOWED_RECEIPT_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
MAX_RECEIPT_BYTES = 8 * 1024 * 1024  # 8MB

@router.post("/process", response_model=NLPTransactionResponse)
async def process_chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    try:
        result = await nlp_parser.parse_transaction(request.text, user_currency=current_user.currency)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scan-receipt", response_model=ReceiptScanResponse)
async def scan_receipt(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_RECEIPT_TYPES:
        raise HTTPException(status_code=400, detail="Please upload a PNG, JPEG, or WEBP photo of the receipt.")

    contents = await file.read()
    if len(contents) > MAX_RECEIPT_BYTES:
        raise HTTPException(status_code=400, detail="That photo is too large — please use one under 8MB.")

    try:
        result = await receipt_scanner.scan_receipt(contents, file.content_type, user_currency=current_user.currency)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))