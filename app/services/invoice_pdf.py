import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch

PURPLE = colors.HexColor("#3F0071")
TEAL = colors.HexColor("#1EBFA3")
CREAM = colors.HexColor("#F7F1E3")
LEDGER_BROWN = colors.HexColor("#5C4326")


def _doc_title(invoice) -> str:
    return "RECEIPT" if invoice.status == "paid" or (hasattr(invoice.status, "value") and invoice.status.value == "paid") else "INVOICE"


def _money(currency: str, amount) -> str:
    return f"{currency} {float(amount):,.2f}"


def generate_invoice_pdf(invoice, user) -> bytes:
    template = (invoice.template or "clean_minimal").lower()
    if template == "bold_branded":
        return _render_bold_branded(invoice, user)
    if template == "classic_ledger":
        return _render_classic_ledger(invoice, user)
    return _render_clean_minimal(invoice, user)


def _draw_items_table(c, items, currency, x, y, width, header_color, text_color=colors.black):
    c.setFillColor(header_color)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x, y, "ITEM")
    c.drawString(x + width * 0.5, y, "QTY")
    c.drawString(x + width * 0.68, y, "UNIT PRICE")
    c.drawString(x + width * 0.85, y, "TOTAL")
    y -= 0.22 * inch
    c.setFillColor(text_color)
    c.setFont("Helvetica", 10)
    for item in items:
        c.drawString(x, y, str(item.description)[:40])
        c.drawString(x + width * 0.5, y, f"{item.quantity:g}")
        c.drawString(x + width * 0.68, y, _money(currency, item.unit_price))
        c.drawString(x + width * 0.85, y, _money(currency, item.total_price))
        y -= 0.22 * inch
    return y


def _render_clean_minimal(invoice, user) -> bytes:
    """Quiet, professional. Best for formal/corporate billing."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    x = 1 * inch

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(x, height - 1 * inch, _doc_title(invoice))
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#555555"))
    c.drawString(x, height - 1.25 * inch, f"#{invoice.invoice_number}")
    c.drawRightString(width - 1 * inch, height - 1 * inch, user.business_name or "My Business")
    c.drawRightString(width - 1 * inch, height - 1.2 * inch, user.business_location or "")

    c.setStrokeColor(colors.HexColor("#DDDDDD"))
    c.line(x, height - 1.5 * inch, width - 1 * inch, height - 1.5 * inch)

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x, height - 1.8 * inch, "BILL TO")
    c.setFont("Helvetica", 11)
    c.drawString(x, height - 2.0 * inch, invoice.customer_name)
    y = height - 2.2 * inch
    for line in [invoice.customer_phone, invoice.customer_email, invoice.customer_address]:
        if line:
            c.drawString(x, y, line)
            y -= 0.2 * inch

    c.drawRightString(width - 1 * inch, height - 1.8 * inch, f"Date: {invoice.created_at.strftime('%Y-%m-%d')}")
    if invoice.due_date:
        c.drawRightString(width - 1 * inch, height - 2.0 * inch, f"Due: {invoice.due_date.strftime('%Y-%m-%d')}")

    y = height - 2.8 * inch
    y = _draw_items_table(c, invoice.items, invoice.currency, x, y, width - 2 * inch, colors.HexColor("#555555"))

    y -= 0.15 * inch
    c.setStrokeColor(colors.HexColor("#DDDDDD"))
    c.line(x, y, width - 1 * inch, y)
    y -= 0.35 * inch
    c.setFont("Helvetica-Bold", 14)
    c.drawRightString(width - 1 * inch, y, f"Total: {_money(invoice.currency, invoice.total_amount)}")

    if invoice.notes:
        y -= 0.5 * inch
        c.setFont("Helvetica-Oblique", 9)
        c.setFillColor(colors.HexColor("#555555"))
        c.drawString(x, y, f"Notes: {invoice.notes}")

    c.save()
    return buffer.getvalue()


def _render_bold_branded(invoice, user) -> bytes:
    """Full Ozzy purple/teal, confident. Best for retail, fashion, beauty."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    x = 1 * inch

    c.setFillColor(PURPLE)
    c.rect(0, height - 2 * inch, width, 2 * inch, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 26)
    c.drawString(x, height - 1 * inch, _doc_title(invoice))
    c.setFont("Helvetica", 11)
    c.drawString(x, height - 1.3 * inch, f"#{invoice.invoice_number}")
    c.setFont("Helvetica-Bold", 14)
    c.drawRightString(width - 1 * inch, height - 1 * inch, user.business_name or "My Business")
    c.setFillColor(TEAL)
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(width - 1 * inch, height - 1.3 * inch, (user.business_location or "").upper())

    y = height - 2.4 * inch
    c.setFillColor(PURPLE)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x, y, "BILL TO")
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y - 0.22 * inch, invoice.customer_name)
    c.setFont("Helvetica", 10)
    yy = y - 0.42 * inch
    for line in [invoice.customer_phone, invoice.customer_email, invoice.customer_address]:
        if line:
            c.drawString(x, yy, line)
            yy -= 0.2 * inch

    c.setFillColor(colors.HexColor("#555555"))
    c.drawRightString(width - 1 * inch, y, f"Date: {invoice.created_at.strftime('%Y-%m-%d')}")
    if invoice.due_date:
        c.drawRightString(width - 1 * inch, y - 0.22 * inch, f"Due: {invoice.due_date.strftime('%Y-%m-%d')}")

    y = height - 3.2 * inch
    c.setFillColor(TEAL)
    c.rect(x, y, width - 2 * inch, 0.02 * inch, fill=True, stroke=False)
    y -= 0.3 * inch
    y = _draw_items_table(c, invoice.items, invoice.currency, x, y, width - 2 * inch, PURPLE)

    y -= 0.2 * inch
    c.setFillColor(TEAL)
    c.rect(x, y - 0.1 * inch, width - 2 * inch, 0.55 * inch, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 14)
    c.drawRightString(width - 1.15 * inch, y + 0.1 * inch, f"Total: {_money(invoice.currency, invoice.total_amount)}")

    if invoice.notes:
        y -= 0.7 * inch
        c.setFont("Helvetica-Oblique", 9)
        c.setFillColor(colors.HexColor("#555555"))
        c.drawString(x, y, f"Notes: {invoice.notes}")

    c.save()
    return buffer.getvalue()


def _render_classic_ledger(invoice, user) -> bytes:
    """Cream paper, boxed like a familiar receipt book. Best for market vendors and traditional trade."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    x = 1 * inch

    c.setFillColor(CREAM)
    c.rect(0, 0, width, height, fill=True, stroke=False)

    box_top = height - 0.8 * inch
    box_bottom = 1 * inch
    c.setStrokeColor(LEDGER_BROWN)
    c.setLineWidth(1.5)
    c.rect(0.7 * inch, box_bottom, width - 1.4 * inch, box_top - box_bottom, fill=False, stroke=True)

    c.setFillColor(LEDGER_BROWN)
    c.setFont("Courier-Bold", 20)
    c.drawCentredString(width / 2, box_top - 0.4 * inch, (user.business_name or "MY BUSINESS").upper())
    c.setFont("Courier", 9)
    c.drawCentredString(width / 2, box_top - 0.6 * inch, user.business_location or "")

    c.setLineWidth(0.5)
    c.line(x, box_top - 0.8 * inch, width - 1 * inch, box_top - 0.8 * inch)

    c.setFont("Courier-Bold", 12)
    c.drawCentredString(width / 2, box_top - 1.05 * inch, f"{_doc_title(invoice)} #{invoice.invoice_number}")
    c.setFont("Courier", 9)
    c.drawCentredString(width / 2, box_top - 1.25 * inch, f"Date: {invoice.created_at.strftime('%Y-%m-%d')}")

    y = box_top - 1.6 * inch
    c.setFont("Courier-Bold", 9)
    c.drawString(x, y, f"CUSTOMER: {invoice.customer_name}")
    y -= 0.25 * inch

    c.line(x, y, width - 1 * inch, y)
    y -= 0.25 * inch
    c.setFont("Courier-Bold", 9)
    c.drawString(x, y, "ITEM")
    c.drawString(x + 3.2 * inch, y, "QTY")
    c.drawString(x + 3.9 * inch, y, "PRICE")
    c.drawString(x + 4.9 * inch, y, "TOTAL")
    y -= 0.22 * inch
    c.setFont("Courier", 9)
    for item in invoice.items:
        c.drawString(x, y, str(item.description)[:28])
        c.drawString(x + 3.2 * inch, y, f"{item.quantity:g}")
        c.drawString(x + 3.9 * inch, y, _money(invoice.currency, item.unit_price))
        c.drawString(x + 4.9 * inch, y, _money(invoice.currency, item.total_price))
        y -= 0.22 * inch

    y -= 0.05 * inch
    c.line(x, y, width - 1 * inch, y)
    y -= 0.3 * inch
    c.setFont("Courier-Bold", 13)
    c.drawCentredString(width / 2, y, f"TOTAL: {_money(invoice.currency, invoice.total_amount)}")

    if invoice.notes:
        y -= 0.4 * inch
        c.setFont("Courier-Oblique", 8)
        c.drawString(x, y, f"Note: {invoice.notes}")

    y -= 0.5 * inch
    c.setFont("Courier", 8)
    c.drawCentredString(width / 2, max(y, box_bottom + 0.3 * inch), "Thank you for your business!")

    c.save()
    return buffer.getvalue()
