from datetime import datetime

from .models import NOPA, PreNopa
def generate_pre_nopa_no(id, purchaser):
    current_year = datetime.now().year
    next_year = current_year + 1
    sequential_number = id # Get the count of existing RFQ objects and add 1
    if purchaser == 2:
        return f"NOPA/{str(current_year)[-2:]}{str(next_year)[-2:]}/{sequential_number:04d}"
    if purchaser == 3:
        return f"NOPA/{str(current_year)[-2:]}{str(next_year)[-2:]}/{sequential_number:04d}"
    return f"NOPA/{str(current_year)[-2:]}{str(next_year)[-2:]}/{sequential_number:04d}"

def generate_nopa_no(id, count):
    sequential_number = count # Get the count of existing RFQ objects and add 1
    return f"{id}/{sequential_number}"

def get_pre_nopa_status_display(status_value):
    for status, status_string in PreNopa.STATUS_CHOICES:
        if status == status_value:
            return status_string
    return "Unknown Status"

def get_nopa_status_display(status_value):
    for status, status_string in NOPA.STATUS_CHOICES:
        if status == status_value:
            return status_string
    return "Unknown Status"