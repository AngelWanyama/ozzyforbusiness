import io
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.invoice import Invoice, InvoiceItem, InvoiceStatus, InvoiceTemplate
from app.models.user import User
from app.models.item import Item
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch

class InvoiceService:
    async def create_invoice_number(self, db: AsyncSession, user_id: Any) -> str:
        stmt = select(func.count(Invoice.id)).where(Invoice.user_id == user_id)
        result = await db.execute(stmt)
        count = result.scalar() or 0
        return f"INV-{(count + 1):04d}"

    def generate_pdf(self, invoice: Invoice, user: User) -> bytes:
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        # Determine colors based on template
        primary_color = colors.black
        if invoice.template == InvoiceTemplate.PROFESSIONAL:
            primary_color = colors.blue
        elif invoice.template == InvoiceTemplate.MODERN:
            primary_color = colors.darkgreen

        # Business Info (Header)
        if invoice.template == InvoiceTemplate.MODERN:
             # Header Background
             c.setFillColor(primary_color)
             c.rect(0, height - 1.5 * inch, width, 1.5 * inch, fill=1)
             c.setFillColor(colors.white)
        else:
             c.setFillColor(primary_color)

        c.setFont("Helvetica-Bold", 16)
        c.drawString(1 * inch, height - 1 * inch, user.business_name or "My Business")
        
        if invoice.template == InvoiceTemplate.MODERN:
             c.setFont("Helvetica", 10)
        else:
             c.setFillColor(colors.black)
             c.setFont("Helvetica", 10)
        
        c.drawString(1 * inch, height - 1.2 * inch, f"Phone: {user.phone_number or 'N/A'}")
        
        # Invoice Header
        if invoice.template == InvoiceTemplate.MODERN:
             c.setFillColor(colors.white)
        else:
             c.setFillColor(primary_color)
             
        c.setFont("Helvetica-Bold", 24)
        c.drawRightString(width - 1 * inch, height - 1 * inch, "INVOICE")
        
        if invoice.template == InvoiceTemplate.MODERN:
             c.setFillColor(colors.white)
        else:
             c.setFillColor(colors.black)
             
        c.setFont("Helvetica", 10)
        c.drawRightString(width - 1 * inch, height - 1.3 * inch, f"Invoice #: {invoice.invoice_number}")
        c.drawRightString(width - 1 * inch, height - 1.5 * inch, f"Date: {invoice.created_at.strftime('%Y-%m-%d')}")
        
        c.setFillColor(colors.black)
        if invoice.due_date:
            c.drawRightString(width - 1 * inch, height - 1.7 * inch, f"Due Date: {invoice.due_date.strftime('%Y-%m-%d')}")

        # Customer Info
        c.setFont("Helvetica-Bold", 12)
        c.drawString(1 * inch, height - 2.2 * inch, "Bill To:")
        c.setFont("Helvetica", 10)
        c.drawString(1 * inch, height - 2.4 * inch, invoice.customer_name)
        if invoice.customer_phone:
            c.drawString(1 * inch, height - 2.6 * inch, f"Phone: {invoice.customer_phone}")
        if invoice.customer_address:
            c.drawString(1 * inch, height - 2.8 * inch, invoice.customer_address)

        # Table Header
        y = height - 3.5 * inch
        c.setStrokeColor(primary_color)
        c.setLineWidth(2)
        c.line(1 * inch, y, width - 1 * inch, y)
        y -= 0.2 * inch
        c.setFont("Helvetica-Bold", 10)
        c.drawString(1 * inch, y, "Description")
        c.drawString(4 * inch, y, "Qty")
        c.drawString(5 * inch, y, "Unit Price")
        c.drawRightString(width - 1 * inch, y, "Total")
        y -= 0.1 * inch
        c.setLineWidth(1)
        c.line(1 * inch, y, width - 1 * inch, y)
        
        # Items
        y -= 0.25 * inch
        c.setFont("Helvetica", 10)
        for item in invoice.items:
            c.drawString(1 * inch, y, item.description)
            c.drawString(4 * inch, y, str(item.quantity))
            c.drawString(5 * inch, y, f"{float(item.unit_price):,.2f}")
            c.drawRightString(width - 1 * inch, y, f"{float(item.total_price):,.2f}")
            y -= 0.2 * inch
            if y < 1.5 * inch:
                c.showPage()
                y = height - 1 * inch

        # Totals
        y -= 0.5 * inch
        c.setStrokeColor(primary_color)
        c.line(4 * inch, y + 0.15 * inch, width - 1 * inch, y + 0.15 * inch)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(4 * inch, y, "Total Amount:")
        c.drawRightString(width - 1 * inch, y, f"{invoice.currency} {float(invoice.total_amount):,.2f}")
        
        # Status Watermark if PAID
        if invoice.status == InvoiceStatus.PAID:
            c.saveState()
            c.rotate(45)
            c.setFont("Helvetica-Bold", 60)
            c.setFillColor(colors.lightgreen, alpha=0.3)
            c.drawString(5 * inch, 0, "PAID")
            c.restoreState()

        # Notes
        if invoice.notes:
            y -= 0.8 * inch
            c.setFont("Helvetica-Bold", 10)
            c.drawString(1 * inch, y, "Notes:")
            y -= 0.2 * inch
            c.setFont("Helvetica", 10)
            c.drawString(1.2 * inch, y, invoice.notes)

        # Footer
        c.setFont("Helvetica-Oblique", 8)
        c.drawCentredString(width/2, 0.5 * inch, "Thank you for your business!")

        c.save()
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

invoice_service = InvoiceService()
