import uuid
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from decimal import Decimal
from app.api.deps import get_db, require_owner
from app.models.user import User
from app.models.invoice import Invoice, InvoiceItem
from app.schemas.invoice import InvoiceCreate, InvoiceUpdate, InvoiceOut, InvoiceGenerateRequest
from app.services.invoice_parser import invoice_parser
from app.services.invoice_pdf import generate_invoice_pdf

router = APIRouter()


async def _next_invoice_number(db: AsyncSession, business_id) -> str:
    count_stmt = select(func.count()).select_from(Invoice).where(Invoice.business_id == business_id)
    result = await db.execute(count_stmt)
    count = result.scalar() or 0
    return f"INV-{count + 1:04d}"


async def _get_owned_invoice(db: AsyncSession, invoice_id: uuid.UUID, business_id) -> Invoice:
    stmt = select(Invoice).options(selectinload(Invoice.items)).where(
        Invoice.id == invoice_id, Invoice.business_id == business_id
    )
    result = await db.execute(stmt)
    invoice = result.scalars().first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    return invoice


def _build_items(items_in) -> list[InvoiceItem]:
    built = []
    for item in items_in:
        qty = Decimal(str(item.quantity if hasattr(item, "quantity") else item.get("quantity", 1)))
        price = Decimal(str(item.unit_price if hasattr(item, "unit_price") else item.get("unit_price", 0)))
        desc = item.description if hasattr(item, "description") else item.get("description", "Item")
        built.append(InvoiceItem(description=desc, quantity=qty, unit_price=price, total_price=qty * price))
    return built


@router.get("/", response_model=list[InvoiceOut])
async def list_invoices(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    effective_business_id = current_user.business_id or current_user.id
    stmt = (
        select(Invoice)
        .options(selectinload(Invoice.items))
        .where(Invoice.business_id == effective_business_id)
        .order_by(Invoice.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=InvoiceOut)
async def create_invoice(
    invoice_in: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    effective_business_id = current_user.business_id or current_user.id
    items = _build_items(invoice_in.items)
    total = sum((i.total_price for i in items), Decimal(0))

    invoice = Invoice(
        business_id=effective_business_id,
        created_by=current_user.id,
        invoice_number=await _next_invoice_number(db, effective_business_id),
        customer_name=invoice_in.customer_name,
        customer_email=invoice_in.customer_email,
        customer_phone=invoice_in.customer_phone,
        customer_address=invoice_in.customer_address,
        template=current_user.receipt_template,
        total_amount=total,
        currency=current_user.currency,
        notes=invoice_in.notes,
        due_date=invoice_in.due_date,
        items=items,
    )
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice, attribute_names=["items"])
    return invoice


@router.post("/generate", response_model=InvoiceOut)
async def generate_invoice(
    request: InvoiceGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    parsed = await invoice_parser.parse_invoice_text(request.text, currency=current_user.currency)
    effective_business_id = current_user.business_id or current_user.id
    items = _build_items(parsed.get("items", []))
    total = sum((i.total_price for i in items), Decimal(0))

    invoice = Invoice(
        business_id=effective_business_id,
        created_by=current_user.id,
        invoice_number=await _next_invoice_number(db, effective_business_id),
        customer_name=parsed.get("customer_name") or "Customer",
        customer_email=parsed.get("customer_email"),
        customer_phone=parsed.get("customer_phone"),
        template=current_user.receipt_template,
        total_amount=total,
        currency=current_user.currency,
        notes=parsed.get("notes"),
        items=items,
    )
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice, attribute_names=["items"])
    return invoice


@router.get("/{invoice_id}", response_model=InvoiceOut)
async def get_invoice(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    effective_business_id = current_user.business_id or current_user.id
    return await _get_owned_invoice(db, invoice_id, effective_business_id)


@router.put("/{invoice_id}", response_model=InvoiceOut)
async def update_invoice(
    invoice_id: uuid.UUID,
    invoice_in: InvoiceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    effective_business_id = current_user.business_id or current_user.id
    invoice = await _get_owned_invoice(db, invoice_id, effective_business_id)
    data = invoice_in.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(invoice, field, value)
    await db.commit()
    await db.refresh(invoice, attribute_names=["items"])
    return invoice


@router.delete("/{invoice_id}")
async def delete_invoice(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    effective_business_id = current_user.business_id or current_user.id
    invoice = await _get_owned_invoice(db, invoice_id, effective_business_id)
    await db.delete(invoice)
    await db.commit()
    return {"ok": True}


@router.get("/{invoice_id}/pdf")
async def get_invoice_pdf(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    effective_business_id = current_user.business_id or current_user.id
    invoice = await _get_owned_invoice(db, invoice_id, effective_business_id)
    pdf_bytes = generate_invoice_pdf(invoice, current_user)
    label = "receipt" if invoice.status == "paid" else "invoice"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={label}_{invoice.invoice_number}.pdf"},
    )
