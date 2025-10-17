from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

def generate_invoice_pdf(invoice_dict):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Set initial coordinates
    x, y = 40, height - 40
    
    # Header Section
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width/2, y, "TAX INVOICE")
    y -= 30
    
    # Invoice Details
    c.setFont("Helvetica", 10)
    c.drawString(x, y, f"Invoice: {invoice_dict['invoice_number']}")
    c.drawString(width/2, y, f"Date: {invoice_dict['date']}")
    y -= 20
    
    # Seller Information
    c.drawString(x, y, f"Seller: {invoice_dict['seller']['name']}")
    c.drawString(width/2, y, f"GSTIN: {invoice_dict['seller'].get('gstin', '')}")
    y -= 20
    
    # Buyer Information
    c.drawString(x, y, f"Buyer: {invoice_dict['buyer'].get('name', '')}")
    c.drawString(width/2, y, f"State: {invoice_dict['buyer'].get('state', '')}")
    y -= 30
    
    # Table Header
    c.setFont("Helvetica-Bold", 10)
    headers = ["Sr", "Description", "HSN", "Qty", "Unit", "Taxable"]
    positions = [x, x+80, x+280, x+340, x+380, x+440]
    
    for header, pos in zip(headers, positions):
        c.drawString(pos, y, header)
    y -= 20
    
    # Table Items
    c.setFont("Helvetica", 9)
    for item in invoice_dict['items']:
        c.drawString(positions[0], y, str(item['sr']))
        c.drawString(positions[1], y, str(item['description'])[:35])
        c.drawString(positions[2], y, str(item.get('hsn', '')))
        c.drawString(positions[3], y, str(item['qty']))
        c.drawString(positions[4], y, f"{item['unit_price']:.2f}")
        c.drawString(positions[5], y, f"{item['taxable']:.2f}")
        y -= 15
        
        # Page break if needed
        if y < 100:
            c.showPage()
            y = height - 40
            c.setFont("Helvetica", 9)
    
    # Grand Total
    y -= 20
    c.setFont("Helvetica-Bold", 10)
    c.drawString(positions[4], y, "Grand Total:")
    c.drawString(positions[5], y, f"{invoice_dict['totals']['grand_total']:.2f}")
    
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.read()

def generate_invoice_image_bytes(invoice_dict, width=1000, row_height=30):
    rows = max(len(invoice_dict['items']), 1) + 6
    height = rows * row_height + 200
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("arial.ttf", 14)
        font_bold = ImageFont.truetype("arialbd.ttf", 14)
    except:
        font = ImageFont.load_default()
        font_bold = ImageFont.load_default()
    
    y = 30
    
    # Header
    draw.text((width/2 - 100, y), "TAX INVOICE", font=font_bold, fill="black")
    y += 40
    
    # Invoice Details
    draw.text((50, y), f"Invoice: {invoice_dict['invoice_number']}", font=font, fill="black")
    draw.text((width/2, y), f"Date: {invoice_dict['date']}", font=font, fill="black")
    y += 30
    
    # Seller & Buyer
    draw.text((50, y), f"Seller: {invoice_dict['seller']['name']}", font=font, fill="black")
    draw.text((width/2, y), f"GSTIN: {invoice_dict['seller'].get('gstin', '')}", font=font, fill="black")
    y += 25
    
    draw.text((50, y), f"Buyer: {invoice_dict['buyer'].get('name', '')}", font=font, fill="black")
    draw.text((width/2, y), f"State: {invoice_dict['buyer'].get('state', '')}", font=font, fill="black")
    y += 40
    
    # Table Header
    header_text = "Sr   Description               HSN   Qty   Unit   Taxable"
    draw.text((50, y), header_text, font=font_bold, fill="black")
    y += row_height
    
    # Table Items
    for item in invoice_dict['items']:
        item_text = (f"{item['sr']}   {item['description'][:20]:<20}   "
                    f"{item.get('hsn', ''):<8}   {item['qty']:<4}   "
                    f"{item['unit_price']:<6.2f}   {item['taxable']:<8.2f}")
        draw.text((50, y), item_text, font=font, fill="black")
        y += row_height
    
    # Grand Total
    y += 20
    draw.text((50, y), f"Grand Total: {invoice_dict['totals']['grand_total']:.2f}", 
              font=font_bold, fill="black")
    
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.getvalue()

def generate_invoice_xlsx_bytes(invoice_dict):
    df = pd.DataFrame(invoice_dict['items'])
    buffer = BytesIO()
    
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Items")
        totals_df = pd.DataFrame([invoice_dict['totals']])
        totals_df.to_excel(writer, index=False, sheet_name="Totals")
    
    buffer.seek(0)
    return buffer.getvalue()

def generate_invoice_csv_bytes(invoice_dict):
    df = pd.DataFrame(invoice_dict['items'])
    buffer = BytesIO()
    buffer.write(df.to_csv(index=False).encode('utf-8'))
    buffer.seek(0)
    return buffer.getvalue()