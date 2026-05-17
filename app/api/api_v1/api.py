from fastapi import APIRouter
from app.api.api_v1.endpoints import chat, transactions, reports, auth, inventory, accounting, users, summaries, payments

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["inventory"])
api_router.include_router(accounting.router, prefix="/reports", tags=["accounting"])
api_router.include_router(summaries.router, prefix="/summaries", tags=["summaries"])
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
