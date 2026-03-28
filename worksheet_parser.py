# worksheet_parser.py
# East Coast Window Films — TintWiz Worksheet Parser v2.2
# Extracts window data, film names, notes, removal flags, and high-work indicators.

import pdfplumber
import re
from pricing_engine import detect_high_work


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

    if "view 35" in raw:  return "UltraView 35"
    if "view 25" in raw:  return "UltraView 25"
    if "view 20" in raw:  return "UltraView 20"
    if "view 15" in raw:  return "UltraView 15"
    if "view 5"  in raw:  return "UltraView 5"

    if "twilight 35" in raw: return "Twilight 35"
    if "twilight 30" in raw: return "Twilight 30"
    if "twilight 20" in raw: return "Twilight 20"
    if "twilight 10" in raw: return "Twilight 10"

    if "ceramic 70" in raw:                             return "Huper Ceramic 70"
    if "ceramic 50" in raw or "ceramic 60" in raw:      return "Huper Ceramic 50"
    if "multi-layer ceramic" in raw or "multilayer ceramic" in raw: return "Huper Ceramic 30"
    if "single layer ceramic" in raw:                   return "Huper Ceramic 40"
    if "klar 85" in raw:                                return "Huper KLAR 85"
    if "select drei" in raw:                            return "Huper Select Drei"
    if "select sech" in raw:                            return "Huper Select Sech"

    if "reform" in raw:          return "Edge Reform"
    if "coal alloy" in raw:      return "Edge Coal Alloy"
    if "pristine ceramic" in raw: return "Edge Pristine Ceramic"

    if "guardian" in raw and "12mil" in raw: return "Guardian 12mil"
    if "guardian" in raw and "8mil"  in raw: return "Guardian 8mil"
    if "guardian" in raw and "4mil"  in raw: return "Guardian 4mil"

    if "frost" in raw and "decorative" not in raw: return "Frost"
    if "blackout" in raw:  return "Blackout"
    if "whiteout" in raw:  return "Whiteout"

    return raw_name.strip()


def is_film_continuation_line(line):
    test = line.strip().lower()
    return (
        test.startswith("view ")
        or test.startswith("ultra ")
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
    client_info = {}

    # ── Extract client info from header ──────────────────────────────────────
    for line in lines[:15]:
        phone_m = re.search(r"Phone:\s*([\d\s\-\(\)]+)", line, re.IGNORECASE)
        if phone_m:
            client_info["phone"] = phone_m.group(1).strip()

        email_m = re.search(r"Email:\s*(\S+@\S+)", line, re.IGNORECASE)
        if email_m:
            client_info["email"] = email_m.group(1).strip()

        addr_m = re.search(r"Address:\s*(.+)", line, re.IGNORECASE)
        if addr_m:
            client_info["address"] = addr_m.group(1).strip()

        # Client name: first line that ends with (Company Name) or standalone name
        name_m = re.match(r"^([A-Za-z][A-Za-z\s]+?)\s*(?:\(|Phone:|Email:|$)", line)
        if name_m and "client_name" not in client_info:
            candidate = name_m.group(1).strip()
            if len(candidate) > 3 and not any(
                kw in candidate.lower() for kw in ["project", "phone", "east coast", "window"]
            ):
                client_info["client_name"] = candidate

    # ── Extract project-level info ────────────────────────────────────────────
    for line in lines:
        m = re.match(
            r"Project:\s+.*Total:\s+(\d+)\s+sqft.*•\s+\d+\s+Sections\s+•\s+(\d+)\s+Panes",
            line, re.IGNORECASE
        )
        if m:
            project_total_sqft  = int(m.group(1))
            project_total_panes = int(m.group(2))

        proj_type_m = re.match(r"Project:\s*(Commercial|Residential)", line, re.IGNORECASE)
        if proj_type_m:
            client_info["project_type"] = proj_type_m.group(1)

    i = 0
    while i < len(lines):
        line = lines[i]

        # ── Project / room totals ─────────────────────────────────────────────
        m_footer = re.match(r"PROJECT TOTAL\s+(\d+)\s+[\d.]+\s+(\d+)", line, re.IGNORECASE)
        if m_footer:
            project_total_panes = int(m_footer.group(1))
            project_total_sqft  = int(m_footer.group(2))
            i += 1
            continue

        m_room_total = re.match(r"ROOM TOTAL\s+(\d+)\s+[\d.]+\s+(\d+)", line, re.IGNORECASE)
        if m_room_total and current_section:
            section_meta[current_section]["room_total_panes"] = int(m_room_total.group(1))
            section_meta[current_section]["room_total_sqft"]  = int(m_room_total.group(2))
            i += 1
            continue

        # ── Section header ────────────────────────────────────────────────────
        m_section = re.match(r"^(.*?)\s+\((\d+)\s+panes\)$", line, re.IGNORECASE)
        if m_section:
            current_section = m_section.group(1).strip()
            section_meta[current_section] = {
                "section_panes_header": int(m_section.group(2)),
                "room_total_panes": None,
                "room_total_sqft":  None,
                "notes":            "",
                "has_removal":      False,
                "high_work":        False,
                "is_exterior":      False,
            }
            i += 1
            continue

        # ── Notes line ────────────────────────────────────────────────────────
        m_notes = re.match(r"Notes?:\s*(.+)", line, re.IGNORECASE)
        if m_notes and current_section:
            notes_text = m_notes.group(1).strip()
            section_meta[current_section]["notes"] = notes_text
            # Auto-detect high work and removal from notes
            section_meta[current_section]["high_work"]   = detect_high_work(notes_text)
            section_meta[current_section]["has_removal"] = bool(
                re.search(r"remov", notes_text, re.IGNORECASE)
            )
            i += 1
            continue

        # ── Single-line window item ───────────────────────────────────────────
        m_single = re.match(
            r"^(Window|Door|Transom)\s+(.*?)\s+(\d+)\s+(\d+)\s+x\s+(\d+)\s+([\d.]+)\s+(\d+)$",
            line, re.IGNORECASE
        )
        if m_single:
            item_type = m_single.group(1)
            raw_film  = m_single.group(2)

            skip_extra = False
            if i + 1 < len(lines) and is_film_continuation_line(lines[i + 1]):
                raw_film   = f"{raw_film} {lines[i + 1]}"
                skip_extra = True

            film = normalize_product_name(raw_film)
            windows.append({
                "section":       current_section or "Unassigned",
                "item_type":     item_type,
                "film":          film,
                "qty":           int(m_single.group(3)),
                "width":         int(m_single.group(4)),
                "height":        int(m_single.group(5)),
                "worksheet_lf":  float(m_single.group(6)),
                "worksheet_sqft": int(m_single.group(7)),
            })
            i += 2 if skip_extra else 1
            continue

        # ── Three-line window item ────────────────────────────────────────────
        if line.startswith(("Window ", "Door ", "Transom ")):
            item_type  = line.split()[0]
            first_part = line[len(item_type):].strip()

            if i + 2 < len(lines):
                film_line_2 = lines[i + 1]
                qty_line    = lines[i + 2]

                m_qty = re.match(
                    r"^(\d+)\s+(\d+)\s+x\s+(\d+)\s+([\d.]+)\s+(\d+)$",
                    qty_line
                )
                if m_qty:
                    raw_film = f"{first_part} {film_line_2}".strip()
                    film     = normalize_product_name(raw_film)
                    windows.append({
                        "section":        current_section or "Unassigned",
                        "item_type":      item_type,
                        "film":           film,
                        "qty":            int(m_qty.group(1)),
                        "width":          int(m_qty.group(2)),
                        "height":         int(m_qty.group(3)),
                        "worksheet_lf":   float(m_qty.group(4)),
                        "worksheet_sqft": int(m_qty.group(5)),
                    })
                    i += 3
                    continue

        i += 1

    return {
        "windows":            windows,
        "section_meta":       section_meta,
        "project_total_sqft": project_total_sqft,
        "project_total_panes": project_total_panes,
        "client_info":        client_info,
    }
