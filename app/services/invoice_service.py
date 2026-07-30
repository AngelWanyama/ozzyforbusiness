import io
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.invoice import Invoice, InvoiceItem, InvoiceStatus, InvoiceTemplate
from app.models.user import User
from app.models.business_profile import BusinessProfile
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from decimal import Decimal

class InvoiceService:
    async def create_invoice_number(self, db: AsyncSession, user_id: Any) -> str:
        # Format: INV-YYYYMMDD-XXX
        today_str = datetime.utcnow().strftime("%Y%m%d")
        stmt = select(func.count(Invoice.id)).where(
            Invoice.user_id == user_id,
            Invoice.invoice_number.like(f"INV-{today_str}-%")
        )
        result = await db.execute(stmt)
        count = result.scalar() or 0
        return f"INV-{today_str}-{(count + 1):03d}"

    def generate_pdf(self, invoice: Invoice, user: User) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
        elements = []
        styles = getSampleStyleSheet()
        
        # Get Business Profile
        # In a real scenario, this would be passed in or fetched. 
        # For simplicity, we assume 'user' object has it if joined, or we use defaults.
        profile = getattr(user, "business_profile", None)
        
        # Header: Business Name and Invoice Title
        header_data = [
            [
                Paragraph(profile.business_name if profile else (user.business_name or "My Business"), styles['Heading1']),
                Paragraph("INVOICE", ParagraphStyle(name='TitleStyle', parent=styles['Heading1'], alignment=2))
            ]
        ]
        header_table = Table(header_data, colWidths=[100*mm, 70*mm])
        elements.append(header_table)
        elements.append(Spacer(1, 5*mm))
        
        # Business and Invoice Info
        info_data = [
            [
                # From (Business)
                Paragraph(f"<b>From:</b><br/>"
                          f"{profile.address if profile and profile.address else ''}<br/>"
                          f"Phone: {profile.phone if profile and profile.phone else (user.phone_number or '')}<br/>"
                          f"Email: {profile.email if profile and profile.email else ''}", styles['Normal']),
                # Invoice Details
                Paragraph(f"<b>Invoice #:</b> {invoice.invoice_number}<br/>"
                          f"<b>Date:</b> {invoice.invoice_date.strftime('%Y-%m-%d')}<br/>"
                          f"<b>Due Date:</b> {invoice.due_date.strftime('%Y-%m-%d') if invoice.due_date else 'N/A'}<br/>"
                          f"<b>Status:</b> {invoice.status.upper()}", styles['Normal'])
            ]
        ]
        info_table = Table(info_data, colWidths=[100*mm, 70*mm])
        elements.append(info_table)
        elements.append(Spacer(1, 10*mm))
        
        # Bill To
        bill_to_data = [
            [
                Paragraph(f"<b>Bill To:</b><br/>"
                          f"{invoice.customer_name}<br/>"
                          f"{invoice.customer_company if invoice.customer_company else ''}<br/>"
                          f"{invoice.customer_address if invoice.customer_address else ''}<br/>"
                          f"Phone: {invoice.customer_phone if invoice.customer_phone else ''}", styles['Normal']),
                ""
            ]
        ]
        bill_to_table = Table(bill_to_data, colWidths=[100*mm, 70*mm])
        elements.append(bill_to_table)
        elements.append(Spacer(1, 10*mm))
        
        # Table of items
        table_header = ["Description", "Qty", "Unit Price", "Disc %", "Tax %", "Total"]
        table_data = [table_header]
        
        for item in invoice.items:
            table_data.append([
                Paragraph(f"<b>{item.name}</b><br/>{item.description if item.description else ''}", styles['Normal']),
                str(item.quantity),
                f"{float(item.unit_price):,.2f}",
                f"{float(item.discount_pct)}%",
                f"{float(item.tax_pct)}%",
                f"{float(item.line_total):,.2f}"
            ])
            
        # Styles for templates
        t_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f2f2f2")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ])
        
        # Adjust style based on template_id
        if invoice.template_id == InvoiceTemplate.TEMPLATE_B:
            t_style.add('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#333333"))
            t_style.add('TEXTCOLOR', (0, 0), (-1, 0), colors.white)
        elif invoice.template_id == InvoiceTemplate.TEMPLATE_C:
            t_style.add('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0066cc"))
            t_style.add('TEXTCOLOR', (0, 0), (-1, 0), colors.white)

        items_table = Table(table_data, colWidths=[60*mm, 15*mm, 25*mm, 20*mm, 20*mm, 30*mm])
        items_table.setStyle(t_style)
        elements.append(items_table)
        elements.append(Spacer(1, 10*mm))
        
        # Totals
        totals_data = [
            ["", "Subtotal:", f"{invoice.currency} {float(invoice.subtotal):,.2f}"],
            ["", "Discount:", f"{invoice.currency} {float(invoice.total_discount):,.2f}"],
            ["", "Tax:", f"{invoice.currency} {float(invoice.total_tax):,.2f}"],
            ["", "Grand Total:", f"{invoice.currency} {float(invoice.grand_total):,.2f}"]
        ]
        totals_table = Table(totals_data, colWidths=[100*mm, 40*mm, 30*mm])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('FONTNAME', (1, 3), (2, 3), 'Helvetica-Bold'),
            ('LINEABOVE', (1, 3), (2, 3), 1, colors.black),
        ]))
        elements.append(totals_table)
        
        # Payment Methods
        if invoice.payment_methods:
            elements.append(Spacer(1, 10*mm))
            elements.append(Paragraph("<b>Payment Methods:</b>", styles['Normal']))
            for pm in invoice.payment_methods:
                elements.append(Paragraph(f"- {pm.get('type')}: {pm.get('instructions')}", styles['Normal']))
        
        # Notes
        if invoice.notes:
            elements.append(Spacer(1, 10*mm))
            elements.append(Paragraph(f"<b>Notes:</b><br/>{invoice.notes}", styles['Normal']))
            
        # Footer
        def footer(canvas, doc):
            canvas.saveState()
            canvas.setFont('Helvetica-Oblique', 8)
            canvas.drawCentredString(A4[0]/2, 10*mm, "Thank you for your business! Powered by Ozzy for Business.")
            canvas.restoreState()
            
        doc.build(elements, onFirstPage=footer, onLaterPages=footer)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

invoice_service = InvoiceService()
