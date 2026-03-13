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


def extract_client_info(text):
    """
    Extract client name, phone, email, and address from TintWiz worksheet header.

    TintWiz header format (first 3-4 lines):
      Line 1: <Client Name> (<Company Type>)   OR just <Client Name>
      Line 2: Phone: <phone>  Email: <email>
      Line 3: Address: <full address>
      Line 4: Project: ...

    Returns a dict with keys: name, phone, email, address
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    client = {
        "name": None,
        "phone": None,
        "email": None,
        "address": None,
    }

    # Line 0 — client/company name (stop before "Project:" line)
    for i, line in enumerate(lines[:6]):
        # Skip lines that look like data rows
        if line.startswith("Project:") or line.startswith("Phone:") or line.startswith("Address:"):
            break
        # First non-header line is the client name
        if not client["name"]:
            # Strip parenthetical company type if present: "NGS Films (Films and Graphics)"
            name_clean = re.sub(r"\s*\(.*?\)\s*$", "", line).strip()
            if name_clean:
                client["name"] = name_clean

    # Scan first 10 lines for phone/email/address
    for line in lines[:10]:
        # Phone and Email on same line: "Phone: 555-123-4567  Email: foo@bar.com"
        phone_match = re.search(
            r"Phone:\s*([\d\s\(\)\-\+\.]{7,20})", line, re.IGNORECASE
        )
        if phone_match:
            raw_phone = phone_match.group(1).strip().rstrip(".")
            # Normalize to digits only for validation, keep formatted
            digits = re.sub(r"\D", "", raw_phone)
            if len(digits) >= 7:
                client["phone"] = raw_phone

        email_match = re.search(
            r"Email:\s*([a-zA-Z0-9_.+\-]+@[a-zA-Z0-9\-]+\.[a-zA-Z0-9.\-]+)",
            line,
            re.IGNORECASE,
        )
        if email_match:
            client["email"] = email_match.group(1).strip()

        addr_match = re.search(r"Address:\s*(.+)", line, re.IGNORECASE)
        if addr_match:
            client["address"] = addr_match.group(1).strip()

    return client


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

    # Edge Pristine series — MUST come before Huper Ceramic checks to avoid false matches
    if "pristine" in raw:
        if "80" in raw:
            return "Edge Pristine 80"
        if "70" in raw:
            return "Edge Pristine 70"
        if "50" in raw:
            return "Edge Pristine 50"
        if "40" in raw:
            return "Edge Pristine 40"
        if "30" in raw:
            return "Edge Pristine 30"
        return "Edge Pristine 40"

    # Huper Optik Ceramic series
    if "ceramic 70" in raw:
        return "Huper Ceramic 70"
    if "ceramic 60" in raw:
        return "Huper Ceramic 60"
    if "ceramic 50" in raw:
        return "Huper Ceramic 50"
    if "ceramic 40" in raw:
        return "Huper Ceramic 40"
    if "ceramic 30" in raw:
        return "Huper Ceramic 30"
    if "ceramic 20" in raw:
        return "Huper Ceramic 20"
    if "multi-layer ceramic" in raw or "multilayer ceramic" in raw:
        return "Huper Multi-Layer Ceramic"
    if "single layer ceramic" in raw:
        return "Huper Single Layer Ceramic"
    if "klar 85" in raw:
        return "Huper KLAR 85"
    if "select drei" in raw:
        return "Huper Select Drei"
    if "select sech" in raw:
        return "Huper Select Sech"
    if "fusion 10" in raw:
        return "Huper Fusion 10"
    if "fusion 20" in raw:
        return "Huper Fusion 20"
    if "fusion 28" in raw:
        return "Huper Fusion 28"
    if "bronze 25" in raw:
        return "Huper Bronze 25"
    if "bronze 35" in raw:
        return "Huper Bronze 35"
    if "silver 18" in raw:
        return "Huper Silver 18"
    if "silver 30" in raw:
        return "Huper Silver 30"
    if "clearshield 4mil" in raw or "clear shield 4mil" in raw:
        return "Huper ClearShield 4mil"
    if "clearshield 8mil" in raw or "clear shield 8mil" in raw:
        return "Huper ClearShield 8mil"
    if "clearshield 14mil" in raw or "clear shield 14mil" in raw:
        return "Huper ClearShield 14mil"

    # Edge Reform
    if "reform" in raw:
        return "Edge Reform"

    # Edge Coal Alloy
    if "coal alloy" in raw:
        return "Edge Coal Alloy"

    # (Edge Pristine already handled above)

    # Edge Safety / Security
    if "guardian" in raw and "12mil" in raw:
        return "Guardian 12mil"
    if "guardian" in raw and "8mil" in raw:
        return "Guardian 8mil"
    if "guardian" in raw and "4mil" in raw:
        return "Guardian 4mil"
    if ("cs" in raw or "clear shield" in raw) and "14mil" in raw:
        return "CS 14mil"
    if ("cs" in raw or "clear shield" in raw) and "8mil" in raw:
        return "CS 8mil"
    if ("cs" in raw or "clear shield" in raw) and "4mil" in raw:
        return "CS 4mil"
    if "shield 35" in raw and "8mil" in raw:
        return "Shield 35 Neutral 8mil"

    # Solyx UltraSafe
    if "ultrasafe" in raw and "white" in raw:
        return "UltraSafe White Matte"
    if "ultrasafe" in raw and "8mil" in raw:
        return "UltraSafe 8mil"
    if "ultrasafe" in raw and "4mil" in raw:
        return "UltraSafe 4mil"
    if "ultrasafe" in raw and "2mil" in raw:
        return "UltraSafe 2mil"

    # Solyx SXF series
    if "sxf-5050" in raw or "sxf 5050" in raw or "5050" in raw:
        return "SXF-5050"
    if "sxf-5060" in raw or "sxf 5060" in raw or "5060" in raw:
        return "SXF-5060"
    if "sxf-5070" in raw or "sxf 5070" in raw or "5070" in raw:
        return "SXF-5070"
    if "sxf-5080" in raw or "sxf 5080" in raw or "5080" in raw:
        return "SXF-5080"

    # Decorative
    if "frost" in raw and "decorative" not in raw:
        return "Frost"
    if "blackout" in raw:
        return "Blackout"
    if "whiteout" in raw:
        return "Whiteout"

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
