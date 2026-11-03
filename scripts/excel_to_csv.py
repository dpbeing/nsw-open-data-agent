from datetime import date, datetime
from pathlib import Path
import csv

from openpyxl import load_workbook


PROJECT_ROOT = Path(__file__).resolve().parents[1]
workbook_path = PROJECT_ROOT / "data" / "raw" / "rental_bonds_2025.xlsx"
csv_path = PROJECT_ROOT / "data" / "interim" / "rental_bonds_2025.csv"

expected_headers = [
    "Lodgement Date",
    "Postcode",
    "Dwelling Type",
    "Bedrooms",
    "Weekly Rent",
]


def cell_text(value):
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


workbook = load_workbook(workbook_path, read_only=True, data_only=True)
sheet = workbook["Year 2025 Rental Bond Lodgments"]

header_row = None
for row_number, row in enumerate(sheet.iter_rows(values_only=True), start=1):
    if [cell_text(value) for value in row[:5]] == expected_headers:
        header_row = row_number
        break

if header_row is None:
    raise ValueError("Could not find the expected column headers.")

csv_path.parent.mkdir(parents=True, exist_ok=True)
rows_written = 0

with csv_path.open("w", newline="", encoding="utf-8") as output_file:
    writer = csv.writer(output_file)
    writer.writerow([
        "lodgement_date",
        "postcode",
        "dwelling_type_raw",
        "bedrooms_raw",
        "weekly_rent_raw",
    ])

    for row in sheet.iter_rows(
            min_row=header_row + 1,
            max_col=5,
            values_only=True,
    ):
        if not any(value is not None for value in row):
            continue

        writer.writerow([cell_text(value) for value in row])
        rows_written += 1

workbook.close()

print("CSV created:", csv_path)
print("Rows written:", rows_written)
