from fastapi import APIRouter, Depends, HTTPException
from app.schemas.chat import ChatRequest
from app.schemas.nlp import NLPTransactionResponse
from app.services.nlp_parser import nlp_parser
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()

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