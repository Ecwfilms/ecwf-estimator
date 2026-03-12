# worksheet_parser.py
# Extracts data from TintWiz worksheet PDFs.

import pdfplumber
import re


def extract_text_from_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


def normalize_product_name(raw_name):
    raw = " ".join(raw_name.split()).strip().lower()

    # Edge / ASWF UltraView series
    if "view 25" in raw:
        return "UltraView 25"
    if "view 20" in raw:
        return "UltraView 20"
    if "view 15" in raw:
        return "UltraView 15"
    if "view 35" in raw:
        return "UltraView 35"
    if "view 5" in raw:
        return "UltraView 5"

    # ASWF Twilight series
    if "twilight 35" in raw:
        return "Twilight 35"
    if "twilight 30" in raw:
        return "Twilight 30"
    if "twilight 20" in raw:
        return "Twilight 20"
    if "twilight 10" in raw:
        return "Twilight 10"

    # Huper Optik Ceramic series
    if "ceramic 70" in raw:
        return "Huper Ceramic 70"
    if "ceramic 50" in raw or "ceramic 60" in raw:
        return "Huper Ceramic 50/60"
    if "multi-layer ceramic" in raw or "multilayer ceramic" in raw:
        return "Huper Multi-Layer Ceramic"
    if "single layer ceramic" in raw:
        return "Huper Single Layer Ceramic"
    if "klar 85" in raw:
        return "Huper KLAR 85"

    # Edge Reform
    if "reform" in raw:
        return "Edge Reform"

    # Edge Coal Alloy
    if "coal alloy" in raw:
        return "Edge Coal Alloy"

    # Edge Pristine Ceramic
    if "pristine ceramic" in raw:
        return "Edge Pristine Ceramic"

    # Safety / Security
    if "guardian" in raw and "8mil" in raw:
        return "Guardian 8mil"
    if "guardian" in raw and "4mil" in raw:
        return "Guardian 4mil"
    if "guardian" in raw and "12mil" in raw:
        return "Guardian 12mil"

    # Decorative
    if "frost" in raw and "decorative" not in raw:
        return "Frost"
    if "blackout" in raw:
        return "Blackout"

    return raw_name.strip()


def is_film_continuation_line(line):
    test = line.strip().lower()
    return (
        test.startswith("view ")
        or test.startswith("twilight ")
        or test.startswith("ceramic ")
        or test.startswith("dual reflective ")
        or test.startswith("reform ")
        or test.startswith("coal alloy ")
        or test.startswith("pristine ")
    )


def extract_window_data(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    windows = []
    current_section = None
    section_meta = {}
    project_total_sqft = None
    project_total_panes = None

    i = 0
    while i < len(lines):
        line = lines[i]

        m_project = re.match(
            r"Project:\s+.*Total:\s+(\d+)\s+sqft.*•\s+\d+\s+Sections\s+•\s+(\d+)\s+Panes",
            line,
            re.IGNORECASE
        )
        if m_project:
            project_total_sqft = int(m_project.group(1))
            project_total_panes = int(m_project.group(2))
            i += 1
            continue

        m_section = re.match(r"^(.*?)\s+\((\d+)\s+panes\)$", line, re.IGNORECASE)
        if m_section:
            current_section = m_section.group(1).strip()
            section_meta[current_section] = {
                "section_panes_header": int(m_section.group(2)),
                "room_total_panes": None,
                "room_total_sqft": None
            }
            i += 1
            continue

        m_room_total = re.match(r"ROOM TOTAL\s+(\d+)\s+[\d.]+\s+(\d+)", line, re.IGNORECASE)
        if m_room_total and current_section:
            section_meta[current_section]["room_total_panes"] = int(m_room_total.group(1))
            section_meta[current_section]["room_total_sqft"] = int(m_room_total.group(2))
            i += 1
            continue

        m_footer_total = re.match(r"PROJECT TOTAL\s+(\d+)\s+[\d.]+\s+(\d+)", line, re.IGNORECASE)
        if m_footer_total:
            project_total_panes = int(m_footer_total.group(1))
            project_total_sqft = int(m_footer_total.group(2))
            i += 1
            continue

        # Single-line item format
        m_single = re.match(
            r"^(Window|Door|Transom)\s+(.*?)\s+(\d+)\s+(\d+)\s+x\s+(\d+)\s+([\d.]+)\s+(\d+)$",
            line,
            re.IGNORECASE
        )

        if m_single:
            item_type = m_single.group(1)
            raw_film = m_single.group(2)

            if i + 1 < len(lines) and is_film_continuation_line(lines[i + 1]):
                raw_film = f"{raw_film} {lines[i + 1]}"
                skip_extra_line = True
            else:
                skip_extra_line = False

            qty = int(m_single.group(3))
            width = int(m_single.group(4))
            height = int(m_single.group(5))
            worksheet_lf = float(m_single.group(6))
            worksheet_sqft = int(m_single.group(7))

            film = normalize_product_name(raw_film)

            windows.append({
                "section": current_section if current_section else "Unassigned",
                "item_type": item_type,
                "film": film,
                "qty": qty,
                "width": width,
                "height": height,
                "worksheet_lf": worksheet_lf,
                "worksheet_sqft": worksheet_sqft
            })

            if skip_extra_line:
                i += 2
            else:
                i += 1
            continue

        # Three-line item format
        if line.startswith(("Window ", "Door ", "Transom ")):
            item_type = line.split()[0]
            first_part = line[len(item_type):].strip()

            if i + 2 < len(lines):
                film_line_2 = lines[i + 1]
                qty_line = lines[i + 2]

                m_qty = re.match(
                    r"^(\d+)\s+(\d+)\s+x\s+(\d+)\s+([\d.]+)\s+(\d+)$",
                    qty_line
                )

                if m_qty:
                    raw_film = f"{first_part} {film_line_2}".strip()
                    film = normalize_product_name(raw_film)

                    qty = int(m_qty.group(1))
                    width = int(m_qty.group(2))
                    height = int(m_qty.group(3))
                    worksheet_lf = float(m_qty.group(4))
                    worksheet_sqft = int(m_qty.group(5))

                    windows.append({
                        "section": current_section if current_section else "Unassigned",
                        "item_type": item_type,
                        "film": film,
                        "qty": qty,
                        "width": width,
                        "height": height,
                        "worksheet_lf": worksheet_lf,
                        "worksheet_sqft": worksheet_sqft
                    })

                    i += 3
                    continue

        i += 1

    return {
        "windows": windows,
        "section_meta": section_meta,
        "project_total_sqft": project_total_sqft,
        "project_total_panes": project_total_panes
    }
