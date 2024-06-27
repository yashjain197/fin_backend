from datetime import datetime
from .models import PurchaseOrder

def generate_po_no(id, purchaser_id):
    current_year = datetime.now().year
    next_year = current_year + 1
    sequential_number = id  # Get the count of existing RFQ objects and add 1
    if purchaser_id == 2:
        return f"PO/CHV/{str(current_year)[-2:]}{str(next_year)[-2:]}/{sequential_number:04d}"
    if purchaser_id == 3:
        return f"PO/SGOL/{str(current_year)[-2:]}{str(next_year)[-2:]}/{sequential_number:04d}"
    return f"PO/OAPL/{str(current_year)[-2:]}{str(next_year)[-2:]}/{sequential_number:04d}"

def get_status_display(status_value):
    for status, status_string in PurchaseOrder.STATUS_CHOICES:
        if status == status_value:
            return status_string
    return "Unknown Status"