def compute_line(qty, unit_price, rate, seller_state, buyer_state):
    """
    Compute tax breakdown for one invoice line.
    If seller_state == buyer_state → CGST + SGST
    Else → IGST
    """
    taxable = qty * unit_price
    igst = cgst = sgst = 0.0
    if seller_state.strip().lower() == buyer_state.strip().lower():
        cgst = taxable * (rate/2) / 100
        sgst = taxable * (rate/2) / 100
    else:
        igst = taxable * rate / 100

    line_total = taxable + cgst + sgst + igst
    return {
        "taxable": taxable,
        "cgst": cgst,
        "sgst": sgst,
        "igst": igst,
        "line_total": line_total
    }

def money(val):
    """Round to 2 decimals consistently for money values."""
    return round(float(val), 2)

