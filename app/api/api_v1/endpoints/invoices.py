from fastapi import APIRouter, Depends, HTTPException, Response, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Optional
from uuid import UUID
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.invoice import Invoice, InvoiceItem, InvoiceStatus
from app.schemas.invoice import (
    Invoice as InvoiceSchema, 
    InvoiceCreate, 
    InvoiceUpdate, 
    InvoiceGenerateRequest
)
from app.services.nlp_parser import nlp_parser
from app.services.invoice_service import invoice_service
from decimal import Decimal

router = APIRouter()

@router.post("/generate", response_model=InvoiceSchema)
async def generate_invoice_from_text(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: InvoiceGenerateRequest
):
    parsed_data = await nlp_parser.parse_invoice(request.text)
    
    invoice_num = await invoice_service.create_invoice_number(db, current_user.id)
    
    db_invoice = Invoice(
        user_id=current_user.id,
        customer_name=parsed_data.get("customer_name", "Walk-in Customer"),
        invoice_number=invoice_num,
        status=InvoiceStatus.DRAFT,
        currency=parsed_data.get("currency", "UGX"),
        notes=parsed_data.get("notes"),
        due_date=parsed_data.get("due_date")
    )
    
    total_amount = Decimal("0")
    for item in parsed_data.get("items", []):
        qty = Decimal(str(item.get("quantity", 1)))
        price = Decimal(str(item.get("unit_price", 0)))
        line_total = qty * price
        total_amount += line_total
        
        invoice_item = InvoiceItem(
            description=item.get("description", "Item"),
            quantity=qty,
            unit_price=price,
            total_price=line_total
        )
        db_invoice.items.append(invoice_item)
        
    db_invoice.total_amount = total_amount
    
    db.add(db_invoice)
    await db.commit()
    # Eagerly load items for the response
    stmt = select(Invoice).where(Invoice.id == db_invoice.id)
    result = await db.execute(stmt)
    return result.scalar_one()

@router.get("/", response_model=List[InvoiceSchema])
async def list_invoices(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
):
    stmt = select(Invoice).where(Invoice.user_id == current_user.id).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/{invoice_id}", response_model=InvoiceSchema)
async def get_invoice(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Invoice).where(Invoice.id == invoice_id, Invoice.user_id == current_user.id)
    result = await db.execute(stmt)
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice

@router.put("/{invoice_id}", response_model=InvoiceSchema)
async def update_invoice(
    invoice_id: UUID,
    invoice_in: InvoiceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Invoice).where(Invoice.id == invoice_id, Invoice.user_id == current_user.id)
    result = await db.execute(stmt)
    db_invoice = result.scalar_one_or_none()
    if not db_invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    update_data = invoice_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_invoice, field, value)
    
    db.add(db_invoice)
    await db.commit()
    await db.refresh(db_invoice)
    return db_invoice

@router.delete("/{invoice_id}")
async def delete_invoice(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Invoice).where(Invoice.id == invoice_id, Invoice.user_id == current_user.id)
    result = await db.execute(stmt)
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    await db.delete(invoice)
    await db.commit()
    return {"message": "Invoice deleted"}

@router.get("/{invoice_id}/pdf")
async def get_invoice_pdf(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Invoice).where(Invoice.id == invoice_id, Invoice.user_id == current_user.id)
    result = await db.execute(stmt)
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    pdf_content = invoice_service.generate_pdf(invoice, current_user)
    filename = f"{invoice.invoice_number}.pdf"
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
