from fastapi import APIRouter, Depends, HTTPException
from app.schemas.chat import ChatRequest
from app.schemas.nlp import NLPTransactionResponse
from app.services.nlp_parser import nlp_parser

router = APIRouter()

@router.post("/process", response_model=NLPTransactionResponse)
async def process_chat(request: ChatRequest):
    try:
        result = await nlp_parser.parse_transaction(request.text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
