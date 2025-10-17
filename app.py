import streamlit as st
import pdfplumber  # ADD THIS LINE - for PDF text extraction
import pandas as pd
import fitz  # PyMuPDF for PDF text extraction
import fitz  # PyMuPDF
import pytesseract
import io
import difflib
import re
import os
import json
from hsn_lookup import HSNLookup
from tax_calc import compute_line, money # type: ignore
from invoice_generator import generate_invoice_pdf, generate_invoice_csv_bytes
from utils import ocr_extract_invoice_items, normalize_item_dicts # type: ignore
from PIL import Image

# ---------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------
st.set_page_config(page_title="GST Invoice Generator", layout="wide")

# ---------------------------------------------------
# BRANDING INFO (Edit as per your real details)
# ---------------------------------------------------
COMPANY_INFO = {
    "name": "Friends Group Company Pvt. Ltd.",
    "gstin": "27ABCDE1234F1Z5",
    "address": "Wiman Nagar, Pune, Maharashtra",
    "contact": "+8207050123",
    "email": "info@mycompany.com",
    "logo_path": "data/logo.png"  # optional, will be shown if exists
}

# ---------------------------------------------------
# CUSTOM CSS STYLING
# ---------------------------------------------------
st.markdown("""
    <style>
        .main, .stApp {
            background-color: #f7faff;
        }
        h1, h2, h3, h4 {
            color: #0b5394;
        }
        .invoice-box {
            background-color: white;
            padding: 25px 35px;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin-bottom: 25px;
        }
        .company-header {
            text-align: center;
            background-color: #008000;
            color: white;
            padding: 15px 0;
            border-radius: 8px;
            margin-bottom: 15px;
        }
        .company-header h2 {
            margin: 0;
            font-weight: 700;
        }
        .company-header p {
            margin: 2px 0;
            font-size: 13px;
        }
        .stTextInput>div>div>input, .stNumberInput>div>div>input {
            border-radius: 5px;
            border: 1px solid #c5d9f1;
            background-color: #fbfdff;
        }
        .stDownloadButton>button, .stButton>button {
            background-color: #0b5394 !important;
            color: white !important;
            border-radius: 6px !important;
            font-weight: 600 !important;
            padding: 8px 18px !important;
            border: none;
        }
        .stDownloadButton>button:hover, .stButton>button:hover {
            background-color: #083b73 !important;
            color: white !important;
        }
        .section-title {
            font-size: 22px;
            color: #008000;
            font-weight: 700;
            border-bottom: 2px solid #008000;
            margin-bottom: 12px;
            padding-bottom: 4px;
        }
        .item-box {
            background-color: #eef4fa;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 10px;
        }
        .summary-box {
            background-color: #eaf1fb;
            padding: 12px 18px;
            border-radius: 8px;
            font-weight: 600;
            margin-top: 15px;
            border-left: 4px solid #0b5394;
        }
        .success-box {
            background-color: #e6f4ea;
            color: #87CEEB;
            border-radius: 6px;
            padding: 10px 15px;
            font-weight: 600;
        }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------
# COMPANY HEADER
# ---------------------------------------------------
if os.path.exists(COMPANY_INFO["logo_path"]):
    st.image(COMPANY_INFO["logo_path"], width=140)

st.markdown(f"""
<div class="company-header">
    <h2>{COMPANY_INFO["name"]}</h2>
    <p>{COMPANY_INFO["address"]}</p>
    <p>GSTIN: {COMPANY_INFO["gstin"]} | 📞 {COMPANY_INFO["contact"]} | ✉️ {COMPANY_INFO["email"]}</p>
</div>
""", unsafe_allow_html=True)

st.title("🧾 GST Invoice Generator (Auto HSN & GST)")
st.write("Generate authentic GST invoices with automatic HSN lookup, tax calculation, and downloadable PDF or Excel files.")

# ---------------------------------------------------
# LOAD HSN LOOKUP
# ---------------------------------------------------
hsn = HSNLookup("Data/HSN DATA 400.csv")

# ---------------------------------------------------
# SINGLE INVOICE SECTION (Multiple Products)
# ---------------------------------------------------
st.markdown('<div class="invoice-box">', unsafe_allow_html=True)
st.markdown('<div class="section-title">Single Invoice</div>', unsafe_allow_html=True)

seller_name = st.text_input("Seller Name", value=COMPANY_INFO["name"])
buyer_name = st.text_input("Buyer Name")
customer_id = st.text_input("Invoice / Customer ID")


# Initialize session state
if "invoice_items" not in st.session_state:
    st.session_state.invoice_items = []

# Number input
num_items = st.number_input("Number of Items", min_value=1, max_value=500, value=1)

# Two buttons side by side
col1, col2 = st.columns(2)

with col1:
    if st.button("➕ Add Items"):
        for _ in range(int(num_items)):
            st.session_state.invoice_items.append({
                "description": "",
                "qty": 1,
                "unit_price": 0.0,
                "hsn": "",
                "rate": 0.0
            })
       
with col2:
    if st.button("➖ Remove Items"):
        if len(st.session_state.invoice_items) > 0:
            remove_count = min(int(num_items), len(st.session_state.invoice_items))
            st.session_state.invoice_items = st.session_state.invoice_items[:-remove_count]
        else:
            st.info("No items to remove.")


items = st.session_state.invoice_items

# Display editable fields for each item
for i, it in enumerate(items):
    st.markdown(f'<div class="item-box"><b>Item {i+1}</b>', unsafe_allow_html=True)
    it["description"] = st.text_input(f"Item Name {i+1}", value=it["description"], key=f"item{i}")
    it["qty"] = st.number_input(f"Quantity {i+1}", min_value=1, value=it["qty"], key=f"qty{i}")
    it["unit_price"] = st.number_input(f"Amount (per unit) {i+1}", min_value=0.0, value=it["unit_price"], key=f"amt{i}")

    # Lookup HSN and GST
    if it["description"]:
        sugg = hsn.suggest(it["description"], limit=1)
        if sugg:
            it["hsn"] = sugg[0]['hsn_code']
            it["rate"] = sugg[0]['rate']
            st.caption(f"Auto HSN: {it['hsn']} | GST Rate: {it['rate']}%")
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------
# GENERATE INVOICE
# ---------------------------------------------------
if st.button("Generate Invoice"):
    if not items:
        st.warning("Please add at least one item to generate the invoice.")
    else:
        totals = {"taxable_value": 0, "cgst": 0, "sgst": 0, "igst": 0, "grand_total": 0}
        lines = []
        sr = 1

        for it in items:
            res = compute_line(it['qty'], it['unit_price'], it['rate'], "Maharashtra", "Karnataka")
            line = {
                **it,
                "sr": sr,
                "rate": float(it['rate']),
                "taxable": float(res['taxable']),
                "cgst": float(res['cgst']),
                "sgst": float(res['sgst']),
                "igst": float(res['igst']),
                "line_total": float(res['line_total'])
            }
            lines.append(line)
            for k in totals.keys():
                if k in res:
                    totals[k] += res[k]
            totals["grand_total"] += res["line_total"]
            sr += 1

        invoice = {
            "invoice_number": f"INV-{customer_id}",
            "date": "2025-10-07",
            "seller": {"name": seller_name, "gstin": COMPANY_INFO["gstin"], "state": "Maharashtra"},
            "buyer": {"name": buyer_name, "gstin": "", "state": "Karnataka"},
            "items": lines,
            "totals": {k: float(money(v)) for k, v in totals.items()}
        }

        # Show invoice summary box
        st.markdown(f"""
        <div class="summary-box">
            Subtotal: ₹{totals['taxable_value']:.2f}<br>
            CGST: ₹{totals['cgst']:.2f} | SGST: ₹{totals['sgst']:.2f} | IGST: ₹{totals['igst']:.2f}<br>
            <b>Grand Total: ₹{totals['grand_total']:.2f}</b>
        </div>
        """, unsafe_allow_html=True)

        # Download buttons
        col1, col2 = st.columns(2)
        with col1:
            st.download_button("📄 Download Invoice (PDF)",
                               data=generate_invoice_pdf(invoice),
                               file_name=f"invoice_{customer_id}.pdf",
                               mime="application/pdf")
        with col2:
            st.download_button("📊 Download Invoice (CSV)",
                               data=generate_invoice_csv_bytes(invoice),
                               file_name=f"invoice_{customer_id}.csv",
                               mime="text/csv")

st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------
# ---------------------------------------------------
# ---------------------------------------------------
# BULK INVOICE SECTION (Improved with Field Detection)
# ---------------------------------------------------
st.markdown('<div class="invoice-box">', unsafe_allow_html=True)
st.markdown('<div class="section-title">Bulk Invoice Upload (Merge Generated & Uploaded Invoices)</div>', unsafe_allow_html=True)

uploaded_bulk = st.file_uploader(
    "Upload multiple invoice files (PDF/IMG/CSV/XLSX)",
    type=['pdf', 'png', 'jpg', 'jpeg', 'csv', 'xlsx'],
    accept_multiple_files=True
)

all_records = []

# -------------------------
# Field Extraction Functions
# -------------------------
def extract_fields_from_text(text, filename):
    """Extract Seller, Buyer, Invoice No from text using regex patterns"""
    fields = {
        "seller": COMPANY_INFO["name"],  # Default to our company
        "buyer": "Unknown Buyer",
        "invoice_no": f"INV-{filename.split('.')[0]}",
        "items": []
    }
    
    if not text:
        return fields
    
    # Patterns for field extraction
    patterns = {
        "seller": [
            r"(?i)Seller\s*[:\-]\s*([^\n\r]+)",
            r"(?i)From\s*[:\-]\s*([^\n\r]+)",
            r"(?i)Supplier\s*[:\-]\s*([^\n\r]+)",
            r"(?i)Vendor\s*[:\-]\s*([^\n\r]+)",
        ],
        "buyer": [
            r"(?i)Buyer\s*[:\-]\s*([^\n\r]+)",
            r"(?i)Bill\s*To\s*[:\-]\s*([^\n\r]+)",
            r"(?i)Customer\s*[:\-]\s*([^\n\r]+)",
            r"(?i)Client\s*[:\-]\s*([^\n\r]+)",
            r"(?i)Sold\s*To\s*[:\-]\s*([^\n\r]+)",
        ],
        "invoice_no": [
            r"(?i)Invoice\s*No\.?\s*[:\-]\s*([A-Za-z0-9\-_/]+)",
            r"(?i)Inv\s*#?\s*[:\-]\s*([A-Za-z0-9\-_/]+)",
            r"(?i)Invoice\s*[:\-]\s*([A-Za-z0-9\-_/]+)",
            r"(?i)Bill\s*No\.?\s*[:\-]\s*([A-Za-z0-9\-_/]+)",
        ]
    }
    
    # Extract Seller
    for pattern in patterns["seller"]:
        match = re.search(pattern, text)
        if match:
            seller_name = match.group(1).strip()
            seller_name = re.sub(r'[,\-]\s*(GSTIN|GST|State|Address).*', '', seller_name, flags=re.IGNORECASE)
            seller_name = seller_name.strip(' ,:-')
            if seller_name and len(seller_name) > 3:
                fields["seller"] = seller_name
            break
    
    # Extract Buyer
    for pattern in patterns["buyer"]:
        match = re.search(pattern, text)
        if match:
            buyer_name = match.group(1).strip()
            buyer_name = re.sub(r'[,\-]\s*(GSTIN|GST|State|Address).*', '', buyer_name, flags=re.IGNORECASE)
            buyer_name = buyer_name.strip(' ,:-')
            if buyer_name and len(buyer_name) > 3:
                fields["buyer"] = buyer_name
            break
    
    # Extract Invoice Number
    for pattern in patterns["invoice_no"]:
        match = re.search(pattern, text)
        if match:
            invoice_no = match.group(1).strip()
            if invoice_no and len(invoice_no) > 3:
                fields["invoice_no"] = invoice_no
            break
    
    return fields

def extract_text_from_file(file_bytes, filename):
    """Extract text from different file types"""
    try:
        if filename.lower().endswith(".pdf"):
            # Extract text from PDF
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text() + "\n"
            doc.close()
            return text
            
        elif filename.lower().endswith((".png", ".jpg", ".jpeg")):
            # Extract text from image using OCR
            img = Image.open(io.BytesIO(file_bytes))
            text = pytesseract.image_to_string(img)
            return text
            
        elif filename.lower().endswith(".csv"):
            # For CSV, read as string
            df = pd.read_csv(io.BytesIO(file_bytes))
            return df.astype(str).to_string(index=False)
            
        elif filename.lower().endswith(".xlsx"):
            # For Excel, read as string
            df = pd.read_excel(io.BytesIO(file_bytes))
            return df.astype(str).to_string(index=False)
            
    except Exception as e:
        st.error(f"Text extraction error for {filename}: {e}")
    
    return ""

# Include generated invoice in bulk (if it exists)
if "invoice_items" in st.session_state and st.session_state.invoice_items:
    invoice_id = customer_id or "GEN-001"
    
    for it in st.session_state.invoice_items:
        if it.get("description") and it.get("qty", 0) > 0:
            rate = it.get("rate", 0)
            res = compute_line(it["qty"], it["unit_price"], rate, "Maharashtra", "Karnataka")
            all_records.append({
                "SourceFile": "Generated Invoice",
                "Seller": COMPANY_INFO["name"],
                "Buyer": buyer_name,
                "Invoice_No.": invoice_id,
                "Item": it.get("description", ""),
                "HSN": it.get("hsn", ""),
                "Rate%": it.get("rate", 0.0),
                "Qty": it.get("qty", 0),
                "UnitPrice": it.get("unit_price", 0.0),
                "Taxable": float(res["taxable"]),
                "CGST": float(res["cgst"]),
                "SGST": float(res["sgst"]),
                "IGST": float(res["igst"]),
                "Total": float(res["line_total"])
            })

if uploaded_bulk and st.button("Process Bulk Files"):
    for up in uploaded_bulk:
        name = up.name
        st.info(f"Processing {name} ...")
        
        try:
            file_bytes = up.read()
            extracted_text = ""
            detected_fields = {}
            items_list = []
            
            # Step 1: Extract text and detect fields for all file types
            if name.lower().endswith(".csv"):
                df = pd.read_csv(io.BytesIO(file_bytes))
                extracted_text = df.astype(str).to_string(index=False)
                items_list = ocr_extract_invoice_items(file_bytes, filename=name)
                
            elif name.lower().endswith(".xlsx"):
                df = pd.read_excel(io.BytesIO(file_bytes))
                extracted_text = df.astype(str).to_string(index=False)
                items_list = ocr_extract_invoice_items(file_bytes, filename=name)
                
            else:  # PDF and Image files
                # Extract text for field detection
                extracted_text = extract_text_from_file(file_bytes, name)
                # Extract items using OCR
                items_list = ocr_extract_invoice_items(file_bytes, filename=name)
            
            # Step 2: Detect Seller, Buyer, Invoice No from extracted text
            detected_fields = extract_fields_from_text(extracted_text, name)
            
            # Display detected fields
            st.write(f"**Detected from {name}:**")
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"Seller: {detected_fields['seller']}")
                st.write(f"Buyer: {detected_fields['buyer']}")
            with col2:
                st.write(f"Invoice No: {detected_fields['invoice_no']}")
            
            # Step 3: Process items
            if not items_list:
                st.warning(f"No items found in {name}")
                continue
            
            # Normalize items with HSN lookup
            normalized_items = normalize_item_dicts(items_list, hsn)
            
            for idx, item in enumerate(normalized_items):
                desc = item.get("Description", "").strip()
                qty = item.get("qty", 0)
                unit_price = item.get("unit_price", 0)
                
                # Skip empty items
                if not desc or qty <= 0 or unit_price <= 0:
                    continue
                
                hsn_code = item.get("hsn", "")
                rate_pct = item.get("rate", 0.0)
                
                # Auto-suggest HSN if still missing
                if not hsn_code and desc:
                    try:
                        sugg = hsn.suggest(desc, limit=1)
                        if sugg:
                            hsn_code = sugg[0].get("hsn_code", "")
                            rate_pct = sugg[0].get("rate", 0.0)
                    except Exception:
                        pass
                
                # Calculate taxes
                res = compute_line(qty, unit_price, rate_pct, "Maharashtra", "Karnataka")
                
                all_records.append({
                    "SourceFile": name,
                    "Seller": detected_fields["seller"],
                    "Buyer": detected_fields["buyer"],
                    "Invoice_No.": detected_fields["invoice_no"],
                    "Item": desc,
                    "HSN": hsn_code,
                    "Rate%": rate_pct,
                    "Qty": qty,
                    "UnitPrice": unit_price,
                    "Taxable": money(res["taxable"]),
                    "CGST": money(res["cgst"]),
                    "SGST": money(res["sgst"]),
                    "IGST": money(res["igst"]),
                    "Total": money(res["line_total"])
                })
            
            st.success(f"✅ Successfully processed {len(normalized_items)} items from {name}")
            
        except Exception as e:
            st.error(f"Error processing {name}: {e}")

# Display and Download Results
if all_records:
    # Convert to DataFrame with proper data types
    df_all = pd.DataFrame(all_records)
    
    # Ensure numeric columns are properly typed
    numeric_cols = ["Qty", "UnitPrice", "Rate%", "Taxable", "CGST", "SGST", "IGST", "Total"]
    for col in numeric_cols:
        if col in df_all.columns:
            df_all[col] = pd.to_numeric(df_all[col], errors='coerce').fillna(0)
    
    # Show preview with better formatting
    st.markdown("### 📄 Preview of Merged Data")
    st.dataframe(df_all, use_container_width=True)
    
    # Summary statistics
    st.markdown("### 📊 Summary")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        unique_invoices = df_all['Invoice_No.'].nunique()
        st.metric("Total Invoices", unique_invoices)
    with col2:
        unique_buyers = df_all['Buyer'].nunique()
        st.metric("Unique Buyers", unique_buyers)
    with col3:
        total_items = len(df_all)
        st.metric("Total Items", total_items)
    with col4:
        grand_total = df_all['Total'].sum()
        st.metric("Grand Total", f"₹{grand_total:,.2f}")
    
    # Show detected buyers and sellers
    st.markdown("### 👥 Detected Parties")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Sellers:**")
        sellers = df_all['Seller'].unique()
        for seller in sellers:
            st.write(f"- {seller}")
    with col2:
        st.write("**Buyers:**")
        buyers = df_all['Buyer'].unique()
        for buyer in buyers:
            buyer_total = df_all[df_all['Buyer'] == buyer]['Total'].sum()
            st.write(f"- {buyer}: ₹{buyer_total:,.2f}")

    # ========== DOWNLOAD OPTIONS ==========
    # Excel Download
    out_excel = io.BytesIO()
    with pd.ExcelWriter(out_excel, engine="openpyxl") as writer:
        df_all.to_excel(writer, index=False, sheet_name="AllInvoices")
        
        # Auto-adjust column widths
        worksheet = writer.sheets["AllInvoices"]
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    out_excel.seek(0)

    # JSON Download
    json_records = df_all.to_dict('records')
    out_json = json.dumps(json_records, indent=4, ensure_ascii=False).encode('utf-8')

    # CSV Download
    out_csv = df_all.to_csv(index=False).encode('utf-8')

    st.success(f"✅ Successfully processed {len(all_records)} items across {unique_invoices} invoices!")

    # Download buttons
    st.markdown("### 💾 Download Options")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.download_button(
            label="⬇️ Download as Excel (.xlsx)",
            data=out_excel,
            file_name="combined_invoices.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    with col2:
        st.download_button(
            label="⬇️ Download as JSON (.json)",
            data=out_json,
            file_name="combined_invoices.json",
            mime="application/json"
        )
    
    with col3:
        st.download_button(
            label="⬇️ Download as CSV (.csv)",
            data=out_csv,
            file_name="combined_invoices.csv",
            mime="text/csv"
        )

else:
    st.info("📝 No invoice data available. Upload files or generate invoices above.")

st.markdown('</div>', unsafe_allow_html=True)