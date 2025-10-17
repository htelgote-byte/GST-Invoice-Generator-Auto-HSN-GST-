import io
import re
import pandas as pd # type: ignore
from PIL import Image # type: ignore
import pytesseract # type: ignore
import pdfplumber # type: ignore
from typing import List, Dict

def _text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    text = ""
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    except Exception:
        text = ""
    return text

def _ocr_image_bytes(img_bytes: bytes) -> str:
    try:
        img = Image.open(io.BytesIO(img_bytes))
        return pytesseract.image_to_string(img)
    except Exception:
        return ""

def ocr_extract_invoice_items(file_bytes: bytes, filename: str) -> List[Dict]:
    fname = filename.lower()
    text = ""
    if fname.endswith(".pdf"):
        text = _text_from_pdf_bytes(file_bytes)
    elif fname.endswith((".png",".jpg",".jpeg")):
        text = _ocr_image_bytes(file_bytes)
    elif fname.endswith(".csv"):
        try:
            df = pd.read_csv(io.BytesIO(file_bytes))
            return _items_from_dataframe(df)
        except:
            return []
    elif fname.endswith(".xlsx"):
        try:
            df = pd.read_excel(io.BytesIO(file_bytes))
            return _items_from_dataframe(df)
        except:
            return []

    if not text:
        return []

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    item_lines = []
    for line in lines:
        m = re.search(r"(.{3,100}?)\s+(\d{1,4})\s+([\d,]*\.\d{1,2}|\d+)", line)
        if m:
            desc = m.group(1).strip()
            qty = m.group(2)
            unit = m.group(3).replace(",","")
            try:
                item_lines.append({"Description": desc, "qty": int(qty), "unit_price": float(unit)})
            except:
                continue
    return item_lines

def _items_from_dataframe(df: pd.DataFrame):
    items = []
    for _, row in df.iterrows():
        try:
            items.append({"Description": str(row.iloc[0]), "qty": int(row.iloc[1]), "unit_price": float(row.iloc[2])})
        except:
            continue
    return items

def normalize_item_dicts(items: List[Dict], hsn_lookup):
    normalized = []
    for it in items:
        desc = it.get("Description","")
        qty = it.get("qty",1)
        unit = it.get("unit_price",0.0)
        sugg = hsn_lookup.suggest(desc, limit=1)
        if sugg:
            hsn_code = sugg[0]['hsn_code']
            rate = sugg[0]['rate']
        else:
            hsn_code = ""
            rate = 0.0
        normalized.append({"Description": desc, "qty": int(qty), "unit_price": float(unit), "hsn": hsn_code, "rate": float(rate)})
    return normalized

