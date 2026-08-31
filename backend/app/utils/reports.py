import io
import csv
from openpyxl import Workbook

def generate_excel_report(data, columns):
    wb = Workbook()
    ws = wb.active
    ws.append([col['header'] for col in columns])
    for row in data:
        ws.append([row.get(col['key'], '') for col in columns])
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output

def generate_csv_report(data, columns):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([col['header'] for col in columns])
    for row in data:
        writer.writerow([row.get(col['key'], '') for col in columns])
    return output.getvalue().encode('utf-8')
