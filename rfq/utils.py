from datetime import datetime

from .models import RFQ

def generate_rfq_no(id):
    current_year = datetime.now().year
    next_year = current_year + 1
    sequential_number = id
    return f"RFQ/OAPL/{str(current_year)[-2:]}{str(next_year)[-2:]}/{sequential_number:04d}"

def getFormattedDate(date):
    date_string = str(date)
    date_obj = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S.%f%z")
    formatted_date = date_obj.strftime("%d-%m-%Y")
    return formatted_date