from __future__ import annotations

import csv
from datetime import datetime
from io import BytesIO, StringIO

from openpyxl import Workbook
from openpyxl.styles import Font

from app.models import Lead


EXPORT_HEADERS = [
    "ID",
    "İşletme Adı",
    "Telefon",
    "E-posta",
    "Website",
    "Adres",
    "Kategori",
    "Kaynak",
    "Durum",
    "Oluşturulma Tarihi",
]


def build_csv(leads: list[Lead]) -> bytes:
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(EXPORT_HEADERS)

    for lead in leads:
        writer.writerow(_lead_to_row(lead))

    return output.getvalue().encode("utf-8-sig")


def build_excel(leads: list[Lead]) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Leadler"
    worksheet.append(EXPORT_HEADERS)

    for cell in worksheet[1]:
        cell.font = Font(bold=True)

    for lead in leads:
        worksheet.append(_lead_to_row(lead))

    for column_cells in worksheet.columns:
        max_length = max(len(str(cell.value or "")) for cell in column_cells)
        worksheet.column_dimensions[column_cells[0].column_letter].width = min(max_length + 2, 40)

    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return output.read()


def create_export_filename(extension: str, selected: bool = False) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = "secilen_leadler" if selected else "tum_leadler"
    return f"{prefix}_{timestamp}.{extension}"


def _lead_to_row(lead: Lead) -> list[str | int]:
    return [
        lead.id,
        lead.business_name,
        lead.phone or "-",
        lead.email or "-",
        lead.website or "-",
        lead.address or "-",
        lead.category or "-",
        lead.source or "-",
        lead.status or "-",
        lead.created_at,
    ]
