# app.py
# East Coast Window Films — Internal Estimator v4.4
# Upgrades: ASWF full catalog, corrected labor adders (removal $2/sqft, ladder $1/sqft,
#           new construction $1/sqft), french panes $8/pane (not per sqft),
#           film lookup with width/price, session persistence.

import streamlit as st
from worksheet_parser import extract_text_from_pdf, extract_window_data, extract_client_info
from proposal_generator import generate_proposal_pdf
from pricing_engine import (
    optimize_for_roll_width,
    group_windows_by_section,
    calculate_material_cost,
    calculate_selling_price,
    calculate_line_item_labor,
    calculate_caulking_cost,
    go_nogo_decision,
    get_price_floor,
    is_safety_film,
    get_supplier,
    check_free_shipping,
    SOLO_INSTALLER_SQFT_PER_DAY,
    FILM_RATES,
    COMPLEXITY_ADDERS,
    FRENCH_PANE_RATE,
    GO_NOGO_MIN_MARGIN,
    GO_NOGO_WARN_MARGIN,
)
from pane_expander import expand_windows

# ─────────────────────────────────────────────
# Safety film caulking threshold (8mil and above)
# ─────────────────────────────────────────────
CAULKING_FILMS = {
    "Guardian 8mil", "Guardian 12mil",
    "CS 8mil", "CS 14mil",
    "Shield 35 Neutral 8mil",
    "UltraSafe 8mil", "UltraSafe White Matte",
    "Huper ClearShield 8mil", "Huper ClearShield 14mil",
    "Huper Shield 35 Neutral 8mil",
}

def needs_caulking(film_name: str) -> bool:
    """Return True if this film is 8mil+ safety/security and requires caulking option."""
    return film_name in CAULKING_FILMS or any(
        kw in film_name.lower() for kw in ["8mil", "12mil", "14mil"]
        if is_safety_film(film_name)
    )

# ─────────────────────────────────────────────
# Page Config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="ECWF Estimator",
    page_icon="🪟",
    layout="wide"
)

st.title("🪟 East Coast Window Films — Estimator")
st.caption("Internal use only. Upload a TintWiz worksheet PDF to begin.")

# ─────────────────────────────────────────────
# Session State — persist uploaded file data
# ─────────────────────────────────────────────
if "pdf_text" not in st.session_state:
    st.session_state["pdf_text"] = None
if "pdf_name" not in st.session_state:
    st.session_state["pdf_name"] = None
if "client_info" not in st.session_state:
    st.session_state["client_info"] = None

# ─────────────────────────────────────────────
# Sidebar: Job Settings
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Job Settings")

    buffer_lf = st.number_input(
        "Installer Buffer (LF)",
        min_value=0.0,
        value=10.0,
        step=5.0,
        help="Extra linear feet added to the recommended order as a safety buffer."
    )

    target_margin = st.slider(
        "Target Profit Margin (%)",
        min_value=20,
        max_value=70,
        value=45,
        step=5,
        help="Your desired gross profit margin. The Go/No-Go engine flags jobs below 40%."
    )

    daily_revenue_target = st.number_input(
        "Daily Revenue Target ($)",
        min_value=0.0,
        value=1500.0,
        step=100.0,
        help=f"Minimum job value based on production rate ({SOLO_INSTALLER_SQFT_PER_DAY} sqft/day)."
    )

    min_job_price = st.number_input(
        "Minimum Job Price ($)",
        min_value=0.0,
        value=350.0,
        step=50.0,
        help="The absolute minimum you will charge for any job."
    )

    st.divider()

    # Clear session button
    if st.session_state["pdf_name"]:
        st.caption(f"📄 Loaded: **{st.session_state['pdf_name']}**")
        if st.button("🗑️ Clear / Load New Job"):
            st.session_state["pdf_text"] = None
            st.session_state["pdf_name"] = None
            st.session_state["client_info"] = None
            st.rerun()
    else:
        st.caption("No worksheet loaded.")

    st.divider()
    st.caption("Film costs loaded from Edge, Huper Optik, and ASWF. Verified Mar 2026.")

# ─────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────
tab_estimator, tab_proposal, tab_lookup = st.tabs(["📋 Estimator", "📄 Proposal", "🔍 Film Lookup"])

# ═════════════════════════════════════════════
# TAB 1: ESTIMATOR
# ═════════════════════════════════════════════
with tab_estimator:

    # ── File uploader (only shown if no file in session) ──
    if st.session_state["pdf_text"] is None:
        uploaded_file = st.file_uploader(
            "Upload TintWiz Worksheet",
            type=["pdf"],
            accept_multiple_files=False,
            help="Export the worksheet from TintWiz as a PDF and upload it here."
        )
        if uploaded_file:
            raw_text = extract_text_from_pdf(uploaded_file)
            st.session_state["pdf_text"] = raw_text
            st.session_state["pdf_name"] = uploaded_file.name
            st.session_state["client_info"] = extract_client_info(raw_text)
            st.rerun()
    else:
        # Show a small re-upload option at the top
        with st.expander("📂 Upload a different worksheet"):
            new_file = st.file_uploader(
                "Replace current worksheet",
                type=["pdf"],
                key="replace_uploader",
                help="Upload a new worksheet to replace the current one."
            )
            if new_file:
                raw_text = extract_text_from_pdf(new_file)
                st.session_state["pdf_text"] = raw_text
                st.session_state["pdf_name"] = new_file.name
                st.session_state["client_info"] = extract_client_info(raw_text)
                st.rerun()

    # ── Main estimator content ──
    if st.session_state["pdf_text"]:
        text = st.session_state["pdf_text"]
        client = st.session_state["client_info"] or {}

        parsed = extract_window_data(text)

        windows = parsed["windows"]
        section_meta = parsed["section_meta"]
        project_total_sqft = parsed["project_total_sqft"]
        project_total_panes = parsed["project_total_panes"]

        if not windows:
            st.error(
                "No window data with film assignments could be parsed from this PDF. "
                "Make sure you have assigned film products to each room in TintWiz before exporting."
            )
            st.stop()

        section_groups = group_windows_by_section(windows)
        all_section_names = list(section_groups.keys())

        # ── Client Info Card ─────────────────────
        client_name = client.get("name")
        client_phone = client.get("phone")
        client_email = client.get("email")
        client_address = client.get("address")

        if any([client_name, client_phone, client_email, client_address]):
            st.subheader("👤 Client")
            info_parts = []

            if client_name:
                info_parts.append(f"**{client_name}**")

            if client_phone:
                # Format as tel: link (strip non-digits for href)
                digits = "".join(c for c in client_phone if c.isdigit())
                info_parts.append(f"[📞 {client_phone}](tel:{digits})")

            if client_email:
                info_parts.append(f"[✉️ {client_email}](mailto:{client_email})")

            if client_address:
                # Encode address for Google Maps / Apple Maps universal link
                import urllib.parse
                encoded_addr = urllib.parse.quote(client_address)
                maps_url = f"https://maps.google.com/?q={encoded_addr}"
                info_parts.append(f"[📍 {client_address}]({maps_url})")

            st.markdown("   |   ".join(info_parts))
            st.divider()

        # ── Project Summary ──────────────────────
        st.subheader("📋 Project Summary")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Square Footage", f"{project_total_sqft} sqft")
        col2.metric("Total Pane Count", f"{project_total_panes} panes")
        col3.metric("Sections / Rooms", f"{len(all_section_names)}")

        # ── Room Selector ────────────────────────
        st.divider()
        st.subheader("🏠 Room Selector")
        st.caption("Deselect rooms to see how removing them affects the total price. The original full-job price is always shown for comparison.")

        active_sections = {}
        cols = st.columns(min(len(all_section_names), 4))
        for i, name in enumerate(all_section_names):
            with cols[i % len(cols)]:
                active_sections[name] = st.checkbox(name, value=True, key=f"room_{name}")

        active_section_names = [n for n, active in active_sections.items() if active]

        if not active_section_names:
            st.warning("All rooms are deselected. Select at least one room to generate an estimate.")
            st.stop()

        st.divider()

        # ── Detect if any active section uses a caulking-required film ──
        active_films_all = []
        for sname in active_section_names:
            for w in section_groups.get(sname, []):
                active_films_all.append(w.get("film", ""))

        job_needs_caulking = any(needs_caulking(f) for f in active_films_all)

        # ── Caulking (safety films only) ─────────
        if job_needs_caulking:
            caulking_lf = st.number_input(
                "🛡️ Caulking (Linear Feet)",
                min_value=0.0,
                value=0.0,
                step=1.0,
                help="Required for safety/security films 8mil and above. Charged at $3.00/LF. "
                     "Measure the perimeter of each window getting safety film."
            )
            caulking_cost = calculate_caulking_cost(caulking_lf)
            if caulking_lf > 0:
                st.caption(f"Caulking: {caulking_lf:.0f} LF × $3.00 = ${caulking_cost:.2f}")
            else:
                st.caption("Safety film detected — enter caulking linear feet above.")
        else:
            caulking_lf = 0.0
            caulking_cost = 0.0

        # ── Rare Options (collapsed by default) ──
        with st.expander("⚙️ Rare Options — Equipment Rental / Exterior Install"):
            rare_col1, rare_col2 = st.columns(2)
            with rare_col1:
                equipment_rental = st.number_input(
                    "Equipment Rental ($)",
                    min_value=0.0,
                    value=0.0,
                    step=50.0,
                    help="Lift, scaffold, or other equipment rental cost. Added directly to total job cost."
                )
                if equipment_rental > 0:
                    st.caption(f"Equipment rental: ${equipment_rental:,.2f}")
            with rare_col2:
                exterior_premium_pct = st.number_input(
                    "Exterior Install Premium (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=0.0,
                    step=5.0,
                    help="Percentage markup for exterior installations. e.g., 25 adds 25% to the sell price."
                )
                if exterior_premium_pct > 0:
                    st.caption(f"Exterior premium: {exterior_premium_pct:.0f}% added to sell price")

        st.divider()

        # ─────────────────────────────────────────
        # Per-Section Analysis
        # ─────────────────────────────────────────
        order_lines = []

        full_job_material = 0.0
        full_job_labor = 0.0
        full_job_sell = 0.0

        active_job_material = 0.0
        active_job_labor = 0.0
        active_job_sell = 0.0

        section_results = {}

        # Job-level complexity flags for install days calculation
        job_has_removal = False
        job_has_ladder = False
        job_has_french_panes = False

        for section_name, section_windows in section_groups.items():
            section_panes = expand_windows(section_windows)
            film_names = sorted(list(set([w["film"] for w in section_windows])))
            film_display = ", ".join(film_names)
            primary_film = film_names[0] if film_names else "Unknown"

            section_sqft = section_meta.get(section_name, {}).get("room_total_sqft", 0) or 0
            section_panes_total = section_meta.get(section_name, {}).get("room_total_panes", len(section_panes))

            roll_options = [48, 60, 72]
            comparison = []

            for roll in roll_options:
                try:
                    optimization = optimize_for_roll_width(section_panes, roll)
                    cost_info = calculate_material_cost(
                        primary_film, roll, optimization["total_lf"], buffer_lf
                    )
                    comparison.append({
                        "roll": roll,
                        "required_lf": optimization["total_lf"],
                        "order_lf": cost_info["order_lf"],
                        "mat_cost": cost_info["recommended_cost"],
                        "btf_cost": cost_info["btf_cost"],
                        "full_roll_cost": cost_info["full_roll_cost"],
                        "full_roll_savings": cost_info["full_roll_savings"],
                        "order_method": cost_info["order_method"],
                        "full_roll_only": cost_info.get("full_roll_only", False),
                        "rates": cost_info["rates"],
                        "rows": optimization["rows"]
                    })
                except ValueError:
                    pass

            if not comparison:
                section_results[section_name] = {"error": True}
                continue

            best = min(comparison, key=lambda x: x["mat_cost"])

            is_active = active_sections.get(section_name, True)

            if is_active:
                st.subheader(f"📐 {section_name}")
                st.markdown(f"**Product:** {film_display}  |  **Panes:** {section_panes_total}  |  **Sqft:** {section_sqft}")

                if is_safety_film(primary_film):
                    caulk_note = " Caulking required (8mil+)." if needs_caulking(primary_film) else ""
                    st.info(f"🛡️ Safety & Security film — ordered in full rolls only. Labor rate: $3.50/sqft.{caulk_note}")

                st.markdown("**Complexity Factors** — check boxes for windows that have special conditions:")

            section_labor_total = 0.0
            complexity_summary = []

            for idx, window_row in enumerate(section_windows):
                w_desc = window_row.get("description", "Window")
                w_film = window_row.get("film", primary_film)
                w_sqft = window_row.get("sqft", 0) or 0
                w_qty = window_row.get("quantity", 1) or 1
                w_dims = window_row.get("dims", "")
                line_sqft = float(w_sqft)

                if line_sqft <= 0:
                    continue

                complexity_flags = {}

                french_panes_count = 0

                if is_active:
                    with st.expander(
                        f"{w_desc} — {w_qty} pane(s) @ {w_dims} = {line_sqft:.0f} sqft",
                        expanded=False
                    ):
                        flag_cols = st.columns(3)
                        flag_keys = list(COMPLEXITY_ADDERS.keys())
                        for fi, fkey in enumerate(flag_keys):
                            factor = COMPLEXITY_ADDERS[fkey]
                            with flag_cols[fi % 3]:
                                complexity_flags[fkey] = st.checkbox(
                                    f"{factor['label']} (+${factor['adder']:.2f}/sqft)",
                                    key=f"cx_{section_name}_{idx}_{fkey}",
                                    help=factor["help"]
                                )
                        # French panes: charged per pane at $8.00/pane (not per sqft)
                        st.markdown("**French Panes** — $8.00 per pane (enter count, not sqft):")
                        french_panes_count = st.number_input(
                            "Number of French Panes",
                            min_value=0,
                            max_value=500,
                            value=0,
                            step=1,
                            key=f"fp_{section_name}_{idx}",
                            help="Each divided pane counts as 1. Charged at $8.00/pane flat."
                        )
                else:
                    for fkey in COMPLEXITY_ADDERS.keys():
                        complexity_flags[fkey] = False

                labor_info = calculate_line_item_labor(
                    line_sqft, w_film, complexity_flags,
                    french_panes_count=int(french_panes_count)
                )
                section_labor_total += labor_info["labor_cost"]

                has_complexity = any(complexity_flags.values()) or french_panes_count > 0
                if has_complexity:
                    complexity_summary.append(
                        f"{w_desc}: {', '.join(labor_info['active_factors'])} → ${labor_info['labor_cost']:.2f} labor"
                    )

            # Selling price (includes labor)
            # NOTE: min_price=0.0 here — the minimum job price is enforced at the
            # job TOTAL level below, not per room. Passing min_job_price per section
            # would inflate every small room to $350 individually.
            pricing = calculate_selling_price(
                best["mat_cost"],
                section_labor_total,
                section_sqft,
                target_margin,
                daily_revenue_target,
                0.0,
                primary_film
            )

            # Apply exterior premium to this section's sell price
            section_sell = pricing["recommended"]
            if exterior_premium_pct > 0:
                section_sell = round(section_sell * (1 + exterior_premium_pct / 100), 2)

            # Go/No-Go for this section
            section_decision = go_nogo_decision(
                section_sell,
                pricing["total_cost"],
                GO_NOGO_MIN_MARGIN,
                GO_NOGO_WARN_MARGIN,
            )

            full_job_material += best["mat_cost"]
            full_job_labor += section_labor_total
            full_job_sell += section_sell

            if is_active:
                active_job_material += best["mat_cost"]
                active_job_labor += section_labor_total
                active_job_sell += section_sell

            # Accumulate job-level complexity flags
            for idx2, window_row2 in enumerate(section_windows):
                for fkey in COMPLEXITY_ADDERS.keys():
                    flag_val = st.session_state.get(f"cx_{section_name}_{idx2}_{fkey}", False)
                    if fkey == "removal" and flag_val:
                        job_has_removal = True
                    if fkey == "ladder" and flag_val:
                        job_has_ladder = True
                fp_val = st.session_state.get(f"fp_{section_name}_{idx2}", 0)
                if fp_val and int(fp_val) > 0:
                    job_has_french_panes = True

            section_results[section_name] = {
                "error": False,
                "is_active": is_active,
                "film": film_display,
                "primary_film": primary_film,
                "sqft": section_sqft,
                "panes": section_panes_total,
                "mat_cost": best["mat_cost"],
                "labor_cost": section_labor_total,
                "total_cost": pricing["total_cost"],
                "recommended_sell": section_sell,
                "decision": section_decision,
                "best": best,
                "pricing": pricing,
                "comparison": comparison,
                "complexity_summary": complexity_summary,
            }

            if is_active:
                info_col, price_col = st.columns([2, 1])

                with info_col:
                    rate = best["rates"]
                    if rate.get("btf_base"):
                        rate_display = f"${rate['btf_base']:.2f}/LF base + ${rate['btf_fee']:.2f}/LF fee"
                    else:
                        rate_display = "Full roll only"
                    st.markdown(f"**Dealer Rate ({best['roll']}\" roll):** {rate_display}")
                    st.markdown(f"**Best Roll Width:** {best['roll']}\"  |  **Order:** {best['order_lf']} LF")

                    order_method_label = {
                        "by_the_foot": "By the Foot",
                        "full_roll": "Full 100 LF Roll",
                        "50lf_roll": "50 LF Roll",
                        "estimate": "Estimated"
                    }.get(best["order_method"], best["order_method"])

                    st.markdown(f"**Order Method:** {order_method_label}")
                    st.markdown(f"**Material Cost:** ${best['mat_cost']:.2f}  |  **Labor Cost:** ${section_labor_total:.2f}")
                    st.markdown(f"**Total Job Cost:** ${pricing['total_cost']:.2f}")

                    if exterior_premium_pct > 0:
                        st.caption(f"Exterior premium ({exterior_premium_pct:.0f}%) applied to sell price.")

                    if best.get("full_roll_savings"):
                        st.success(f"💡 Full roll saves ${best['full_roll_savings']:.2f} vs. by-the-foot.")

                    if complexity_summary:
                        st.caption("Complexity factors applied: " + " | ".join(complexity_summary))

                with price_col:
                    decision = section_decision
                    if decision["color"] == "green":
                        st.success(f"✅ {decision['message']}")
                    elif decision["color"] == "yellow":
                        st.warning(f"⚠️ {decision['message']}")
                    else:
                        st.error(f"🚫 {decision['message']}")

                    st.metric(
                        label="Recommended Sell Price",
                        value=f"${section_sell:,.2f}",
                        delta=f"+${decision['gross_profit']:,.2f} gross profit",
                    )
                    st.caption(f"Material: ${pricing['material_cost']:,.2f}")
                    st.caption(f"Labor: ${pricing['labor_cost']:,.2f}")
                    st.caption(f"Margin-based: ${pricing['margin_price']:,.2f}")
                    st.caption(f"Floor ({pricing['floor_per_sqft']:.2f}/sqft): ${pricing['floor_price']:,.2f}")

                order_lines.append(
                    f"{film_display} — {best['roll']}\" × {best['order_lf']} LF ({order_method_label})"
                )

                with st.expander(f"Roll width comparison — {section_name}"):
                    for item in comparison:
                        marker = " ✅ best" if item["roll"] == best["roll"] else ""
                        method = {
                            "by_the_foot": "by-the-foot",
                            "full_roll": "full roll",
                            "50lf_roll": "50 LF roll",
                        }.get(item["order_method"], item["order_method"])
                        savings_note = f" | saves ${item['full_roll_savings']:.2f} vs BTF" if item.get("full_roll_savings") else ""
                        st.write(
                            f"{item['roll']}\" roll | Required: {item['required_lf']} LF | "
                            f"Order: {item['order_lf']} LF ({method}) | "
                            f"Cost: ${item['mat_cost']:.2f}{savings_note}{marker}"
                        )

                with st.expander(f"Pull rows — {section_name}"):
                    for ridx, row in enumerate(best["rows"], start=1):
                        pane_text = " + ".join([f"{p['width']}×{p['height']}" for p in row["panes"]])
                        st.write(
                            f"Row {ridx}: {pane_text} | "
                            f"Used Width: {row['used_width']}\" | "
                            f"Pull to: {row['pull_to']}\" | "
                            f"Lanes: {row['lanes']}"
                        )

                st.divider()

        # ─────────────────────────────────────────────
        # Order Summary
        # ─────────────────────────────────────────────
        if order_lines:
            st.subheader("🛒 Order This")
            for line in order_lines:
                st.markdown(f"- {line}")
            if caulking_lf > 0:
                st.markdown(f"- Caulking: {caulking_lf:.0f} LF")
            if equipment_rental > 0:
                st.markdown(f"- Equipment Rental: ${equipment_rental:,.2f}")

            # ── Free Shipping Check ──────────────────
            supplier_totals: dict = {}
            for sname, res in section_results.items():
                if res.get("error") or not res.get("is_active"):
                    continue
                supplier = get_supplier(res["primary_film"])
                supplier_totals[supplier] = supplier_totals.get(supplier, 0.0) + res["mat_cost"]

            st.markdown("**Shipping Status:**")
            for supplier, total in sorted(supplier_totals.items()):
                threshold = 1000.0
                if total >= threshold:
                    st.success(f"✅ {supplier}: ${total:,.2f} — **Free shipping** (over ${threshold:,.0f})")
                else:
                    shortfall = round(threshold - total, 2)
                    st.warning(f"⚠️ {supplier}: ${total:,.2f} — Add ${shortfall:,.2f} more to qualify for free shipping")

            st.divider()

        # ─────────────────────────────────────────
        # Job Totals Dashboard
        # ─────────────────────────────────────────
        st.subheader("💰 Job Totals")

        rooms_removed = len(all_section_names) - len(active_section_names)
        showing_adjusted = rooms_removed > 0

        if showing_adjusted:
            st.info(f"**{rooms_removed} room(s) removed.** Showing adjusted estimate vs. full job.")

        # Add caulking and equipment rental to cost totals
        active_job_labor += caulking_cost
        full_job_labor += caulking_cost
        active_job_material += equipment_rental
        full_job_material += equipment_rental

        active_total_cost = active_job_material + active_job_labor
        full_total_cost = full_job_material + full_job_labor

        # Apply minimum job price at the TOTAL job level (not per room)
        min_price_applied = active_job_sell < min_job_price
        active_job_sell = max(active_job_sell, min_job_price)
        full_job_sell = max(full_job_sell, min_job_price)

        active_decision = go_nogo_decision(active_job_sell, active_total_cost)
        full_decision = go_nogo_decision(full_job_sell, full_total_cost)

        if showing_adjusted:
            col_adj, col_full = st.columns(2)

            with col_adj:
                st.markdown("#### Adjusted Estimate (Selected Rooms)")
                st.metric("Material Cost", f"${active_job_material:,.2f}")
                st.metric("Labor Cost", f"${active_job_labor:,.2f}")
                st.metric("Total Cost", f"${active_total_cost:,.2f}")
                st.metric(
                    "Recommended Sell Price",
                    f"${active_job_sell:,.2f}",
                    delta=f"+${active_job_sell - active_total_cost:,.2f} gross"
                )
                if active_decision["color"] == "green":
                    st.success(f"✅ {active_decision['message']}")
                elif active_decision["color"] == "yellow":
                    st.warning(f"⚠️ {active_decision['message']}")
                else:
                    st.error(f"🚫 {active_decision['message']}")

            with col_full:
                st.markdown("#### Original Full Job")
                st.metric("Material Cost", f"${full_job_material:,.2f}")
                st.metric("Labor Cost", f"${full_job_labor:,.2f}")
                st.metric("Total Cost", f"${full_total_cost:,.2f}")
                st.metric(
                    "Recommended Sell Price",
                    f"${full_job_sell:,.2f}",
                    delta=f"+${full_job_sell - full_total_cost:,.2f} gross"
                )
                if full_decision["color"] == "green":
                    st.success(f"✅ {full_decision['message']}")
                elif full_decision["color"] == "yellow":
                    st.warning(f"⚠️ {full_decision['message']}")
                else:
                    st.error(f"🚫 {full_decision['message']}")

        else:
            col_mat, col_lab, col_cost, col_sell = st.columns(4)

            col_mat.metric("Material Cost", f"${active_job_material:,.2f}")
            col_lab.metric("Labor Cost", f"${active_job_labor:,.2f}")
            col_cost.metric("Total Job Cost", f"${active_total_cost:,.2f}")
            col_sell.metric(
                "Recommended Sell Price",
                f"${active_job_sell:,.2f}",
                delta=f"+${active_job_sell - active_total_cost:,.2f} gross"
            )

            if min_price_applied:
                st.caption(f"ℹ️ Minimum job price of ${min_job_price:,.2f} applied to total (rooms priced individually below this threshold).")

            st.divider()

            if active_decision["color"] == "green":
                st.success(f"✅ **{active_decision['message']}** — Gross Profit: ${active_decision['gross_profit']:,.2f}")
            elif active_decision["color"] == "yellow":
                st.warning(f"⚠️ **{active_decision['message']}** — Gross Profit: ${active_decision['gross_profit']:,.2f}")
            else:
                st.error(f"🚫 **{active_decision['message']}** — Consider raising the price or declining this job.")

        # ─────────────────────────────────────────
        # Daily Profit Protection Panel
        # ─────────────────────────────────────────
        st.divider()
        st.subheader("⏱️ Daily Profit Protection")

        # Crew type selector
        crew_type_choice = st.radio(
            "Crew Type",
            options=["solo", "crew"],
            format_func=lambda x: "Solo (Owner Install)" if x == "solo" else "Crew (Installer + Helper)",
            horizontal=True,
            key="crew_type_radio",
            help="Solo = 250 sqft/day ($700/day floor). Crew = 400 sqft/day ($500/day floor)."
        )

        active_sqft = sum(
            res["sqft"] for res in section_results.values()
            if not res.get("error") and res.get("is_active")
        )

        install_info = calculate_install_days(
            total_sqft=active_sqft,
            has_removal=job_has_removal,
            has_ladder=job_has_ladder,
            has_french_panes=job_has_french_panes,
            crew_type=crew_type_choice,
        )

        active_gross_profit = active_job_sell - active_total_cost
        install_days = install_info["install_days"]
        daily_profit_floor = install_info["daily_profit_floor"]
        daily_profit_actual = round(active_gross_profit / install_days, 2) if install_days > 0 else 0.0
        profit_gap = round(daily_profit_actual - daily_profit_floor, 2)

        dp_col1, dp_col2, dp_col3, dp_col4 = st.columns(4)
        dp_col1.metric(
            "Total Active SqFt",
            f"{active_sqft} sqft"
        )
        dp_col2.metric(
            "Production Rate",
            f"{install_info['adjusted_sqft_per_day']:,.0f} sqft/day",
            delta=f"{install_info['base_sqft_per_day']:,.0f} base" if install_info['penalties_applied'] else None,
            delta_color="off"
        )
        dp_col3.metric(
            "Estimated Install Days",
            f"{install_days:.2f} days"
        )
        dp_col4.metric(
            "Gross Profit / Day",
            f"${daily_profit_actual:,.2f}",
            delta=f"Floor: ${daily_profit_floor:,.0f}/day",
            delta_color="off"
        )

        if install_info["penalties_applied"]:
            st.caption("Production penalties applied: " + " | ".join(install_info["penalties_applied"]))

        # Daily profit verdict
        if daily_profit_actual >= daily_profit_floor:
            gap_msg = f"+${profit_gap:,.2f}/day above floor"
            st.success(f"✅ **DAILY PROFIT: GO** — ${daily_profit_actual:,.2f}/day vs. ${daily_profit_floor:,.0f}/day floor ({gap_msg})")
        elif daily_profit_actual >= daily_profit_floor * 0.90:
            gap_msg = f"${abs(profit_gap):,.2f}/day below floor"
            st.warning(f"⚠️ **DAILY PROFIT: CAUTION** — ${daily_profit_actual:,.2f}/day vs. ${daily_profit_floor:,.0f}/day floor ({gap_msg}). Raise price or reduce scope.")
        else:
            gap_msg = f"${abs(profit_gap):,.2f}/day below floor"
            st.error(f"🚫 **DAILY PROFIT: NO-GO** — ${daily_profit_actual:,.2f}/day vs. ${daily_profit_floor:,.0f}/day floor ({gap_msg}). This job does not meet your Profit Floor.")

        # ── Section Summary Table ────────────────
        st.divider()
        st.subheader("📊 Section Breakdown")

        summary_rows = []
        for sname, res in section_results.items():
            if res.get("error"):
                continue
            status_icon = {"green": "✅", "yellow": "⚠️", "red": "🚫"}.get(
                res["decision"]["color"], "—"
            )
            active_label = "✓" if res["is_active"] else "—"
            summary_rows.append({
                "Room": sname,
                "Active": active_label,
                "Film": res["film"],
                "SqFt": res["sqft"],
                "Material": f"${res['mat_cost']:,.2f}",
                "Labor": f"${res['labor_cost']:,.2f}",
                "Total Cost": f"${res['total_cost']:,.2f}",
                "Sell Price": f"${res['recommended_sell']:,.2f}",
                "Margin": f"{res['decision']['actual_margin_pct']}%",
                "Status": f"{status_icon} {res['decision']['actual_margin_pct']}%",
            })

        if summary_rows:
            st.dataframe(summary_rows, use_container_width=True)

        # ── Persist results to session state for Proposal tab ──
        st.session_state["section_results"] = section_results
        st.session_state["active_job_sell"] = active_job_sell
        st.session_state["caulking_lf"] = caulking_lf
        st.session_state["caulking_cost"] = caulking_cost
        st.session_state["equipment_rental"] = equipment_rental

    else:
        st.info("Upload a TintWiz worksheet PDF using the uploader above to get started.")


# ═════════════════════════════════════════════
# TAB 2: PROPOSAL GENERATOR
# ═════════════════════════════════════════════
with tab_proposal:

    st.subheader("📄 Proposal Generator")
    st.caption("Generate a professional, branded PDF proposal from the current estimate. Run the Estimator tab first.")

    if not st.session_state.get("pdf_text") or "section_results" not in st.session_state:
        st.info("Upload a TintWiz worksheet and run the Estimator first — then come back here to generate a proposal.")
    else:
        _client = st.session_state.get("client_info") or {}
        _section_results = st.session_state.get("section_results", {})
        _active_job_sell = st.session_state.get("active_job_sell", 0.0)
        _caulking_lf = st.session_state.get("caulking_lf", 0.0)
        _caulking_cost = st.session_state.get("caulking_cost", 0.0)
        _equipment_rental = st.session_state.get("equipment_rental", 0.0)

        st.markdown("#### Proposal Settings")
        prop_col1, prop_col2 = st.columns(2)

        with prop_col1:
            import datetime as _dt
            default_prop_num = f"ECWF-{_dt.date.today().strftime('%Y%m%d')}-001"
            proposal_number = st.text_input(
                "Proposal Number",
                value=default_prop_num,
                help="Unique identifier for this proposal."
            )
            valid_days = st.number_input(
                "Valid For (days)",
                min_value=7,
                max_value=90,
                value=30,
                step=1,
                help="Number of days this proposal remains valid."
            )

        with prop_col2:
            scope_notes = st.text_area(
                "Project Scope / Notes (optional)",
                placeholder="e.g., Install solar control film on all south-facing windows in the living room and master bedroom to reduce heat and glare.",
                height=100,
                help="A brief description of the project scope shown at the top of the proposal."
            )

        with st.expander("⚙️ Customize Terms & Conditions (optional)"):
            terms_notes = st.text_area(
                "Terms & Conditions",
                placeholder="Leave blank to use the default ECWF terms.",
                height=120,
                help="Override the default terms and conditions text."
            )

        st.divider()

        # Preview the line items
        st.markdown("#### Proposal Preview")
        preview_rows = []
        for sname, res in _section_results.items():
            if res.get("error") or not res.get("is_active"):
                continue
            preview_rows.append({
                "Room": sname,
                "Film": res.get("film", ""),
                "Sq Ft": res.get("sqft", 0),
                "Price": f"${res.get('recommended_sell', 0.0):,.2f}",
            })

        if _caulking_lf > 0:
            preview_rows.append({
                "Room": "Perimeter Caulking",
                "Film": "Safety Film Seal",
                "Sq Ft": "—",
                "Price": f"${_caulking_cost:,.2f}",
            })
        if _equipment_rental > 0:
            preview_rows.append({
                "Room": "Equipment Rental",
                "Film": "Lift / Scaffold",
                "Sq Ft": "—",
                "Price": f"${_equipment_rental:,.2f}",
            })

        total_proposal = _active_job_sell + _caulking_cost + _equipment_rental
        preview_rows.append({
            "Room": "TOTAL",
            "Film": "",
            "Sq Ft": "",
            "Price": f"${total_proposal:,.2f}",
        })

        st.dataframe(preview_rows, use_container_width=True)

        st.divider()

        if st.button("⬇️ Generate & Download PDF Proposal", type="primary", use_container_width=True):
            import os as _os
            logo_path = _os.path.join(_os.path.dirname(__file__), "ecwf_logo.png")
            with st.spinner("Building your proposal PDF..."):
                try:
                    pdf_bytes = generate_proposal_pdf(
                        client=_client,
                        section_results=_section_results,
                        active_job_sell=_active_job_sell,
                        caulking_lf=_caulking_lf,
                        caulking_cost=_caulking_cost,
                        equipment_rental=_equipment_rental,
                        proposal_number=proposal_number,
                        valid_days=int(valid_days),
                        scope_notes=scope_notes,
                        terms_notes=terms_notes if 'terms_notes' in dir() else "",
                        logo_path=logo_path,
                    )
                    client_name_safe = (_client.get("name") or "Proposal").replace(" ", "_")
                    filename = f"ECWF_Proposal_{client_name_safe}_{proposal_number}.pdf"
                    st.download_button(
                        label="📥 Download PDF",
                        data=pdf_bytes,
                        file_name=filename,
                        mime="application/pdf",
                        use_container_width=True,
                    )
                    st.success(f"✅ Proposal ready: {filename}")
                except Exception as e:
                    st.error(f"Error generating proposal: {e}")
                    st.exception(e)


# ═════════════════════════════════════════════
# TAB 3: FILM LOOKUP
# ═════════════════════════════════════════════
with tab_lookup:
    st.subheader("🔍 Film Price Lookup")

    import re as _re

    # ── Helper: build rate table rows for a list of film names (one row per width) ──
    def _build_rate_rows(film_list):
        rows = []
        for film_name in film_list:
            widths = FILM_RATES[film_name]
            safety_flag = "🛡️" if film_name in CAULKING_FILMS else ""
            for w, rates in sorted(widths.items()):
                price_sqft = rates.get("price_sqft")
                btf_base = rates.get("btf_base")
                btf_fee = rates.get("btf_fee", 0)
                roll_100 = rates.get("roll_100lf")
                roll_50 = rates.get("roll_50lf")

                if price_sqft is not None:
                    rate_per_lf = round(price_sqft * (w / 12.0), 3)
                    rate_display = f"${price_sqft:.2f}/sqft (${rate_per_lf:.3f}/LF)"
                elif btf_base is not None:
                    rate_display = f"${round(btf_base + btf_fee, 3):.3f}/LF"
                else:
                    rate_display = "Full roll only"

                roll_100_display = f"${roll_100:,.2f}" if roll_100 else "—"
                roll_50_display = f"${roll_50:,.2f}" if roll_50 else "—"

                rows.append({
                    "Film": film_name,
                    "Width": f'{w}"',
                    "Dealer Rate": rate_display,
                    "100 LF Roll": roll_100_display,
                    "50 LF Roll": roll_50_display,
                    "Safety": safety_flag,
                })
        return rows

    # ── Helper: build dimension-cost rows for a list of film names ───────────
    def _build_cost_rows(film_list, w_in, h_in):
        lf_needed = round(h_in / 12, 4)
        rows = []
        for film_name in film_list:
            widths_available = sorted(FILM_RATES[film_name].keys())
            fitting_widths = [rw for rw in widths_available if rw >= w_in] or widths_available
            for roll_w in fitting_widths:
                rates = FILM_RATES[film_name][roll_w]
                btf_base = rates.get("btf_base")
                btf_fee = rates.get("btf_fee", 0)
                roll_100 = rates.get("roll_100lf")
                price_sqft = rates.get("price_sqft")
                if price_sqft is not None:
                    rate_per_lf = round(price_sqft * (roll_w / 12.0), 4)
                    material_cost = round(rate_per_lf * lf_needed, 2)
                    cost_display = f"${material_cost:.2f}"
                    rate_display = f"${price_sqft:.2f}/sqft (${rate_per_lf:.3f}/LF)"
                elif btf_base is not None:
                    rate_per_lf = round(btf_base + btf_fee, 4)
                    material_cost = round(rate_per_lf * lf_needed, 2)
                    cost_display = f"${material_cost:.2f}"
                    rate_display = f"${rate_per_lf:.4f}/LF"
                else:
                    cost_display = "Full roll only"
                    rate_display = "Full roll only"
                roll_100_display = f"${roll_100:,.2f}" if roll_100 else "—"
                safety_flag = "🛡️" if film_name in CAULKING_FILMS else ""
                rows.append({
                    "Film": film_name,
                    "Roll Width": f'{roll_w}"',
                    "LF Needed": f"{lf_needed:.2f} LF",
                    "Rate": rate_display,
                    f"Cost ({w_in}x{h_in})": cost_display,
                    "100 LF Roll": roll_100_display,
                    "Safety": safety_flag,
                })
        return rows

    # ── Global Search (queries all manufacturers) ───────────────────────────
    st.caption(
        "Search across all manufacturers by film name or code. "
        "Optionally prefix with dimensions to get material cost: e.g. **60x25 UltraView 15**"
    )
    search_query = st.text_input(
        "🔎 Search all films (name, code, or WxH film)",
        placeholder="e.g., Daydream 25   or   60x48 ASWF Nature 20   or   Guardian 8mil",
        key="lookup_global_search",
        help="Searches across Edge, Huper Optik, and ASWF simultaneously."
    )

    all_film_names_global = sorted(FILM_RATES.keys())

    dim_match = _re.match(r"^\s*(\d+)\s*[xX×]\s*(\d+)\s+(.*)", search_query.strip())
    parsed_width = int(dim_match.group(1)) if dim_match else None
    parsed_height = int(dim_match.group(2)) if dim_match else None
    film_search_term = dim_match.group(3).strip() if dim_match else search_query.strip()

    if search_query.strip():
        global_matches = [f for f in all_film_names_global if film_search_term.lower() in f.lower()]
        if not global_matches:
            st.warning(f"No films found matching '{film_search_term}'.")
        else:
            st.caption(f"{len(global_matches)} match(es) across all manufacturers.")
            if parsed_width and parsed_height:
                cost_rows = _build_cost_rows(global_matches, parsed_width, parsed_height)
                if cost_rows:
                    st.markdown(f"**Material cost for a {parsed_width}\" × {parsed_height}\" piece:**")
                    st.dataframe(cost_rows, use_container_width=True)
                else:
                    st.warning("No matching films found for those dimensions.")
            else:
                st.dataframe(_build_rate_rows(global_matches), use_container_width=True)

    st.divider()

    # ── Manufacturer Sub-Tabs ────────────────────────────────────────────────
    st.markdown("**Browse by Manufacturer**")
    mfr_tab_edge, mfr_tab_huper, mfr_tab_aswf = st.tabs(
        ["🏷️ Edge", "🏷️ Huper Optik", "🏷️ ASWF"]
    )

    MANUFACTURER_TABS = {
        "Edge": mfr_tab_edge,
        "Huper Optik": mfr_tab_huper,
        "ASWF": mfr_tab_aswf,
    }

    for mfr_name, mfr_tab in MANUFACTURER_TABS.items():
        with mfr_tab:
            mfr_films = sorted([f for f in FILM_RATES.keys() if get_supplier(f) == mfr_name])
            if not mfr_films:
                st.info(f"No films loaded for {mfr_name}.")
                continue

            st.caption(f"{len(mfr_films)} films — click any row to see width details.")

            # Per-manufacturer search
            mfr_search = st.text_input(
                f"Filter {mfr_name} films",
                placeholder="e.g., Nature 20",
                key=f"mfr_search_{mfr_name}",
            )
            if mfr_search.strip():
                mfr_films = [f for f in mfr_films if mfr_search.strip().lower() in f.lower()]

            if not mfr_films:
                st.warning("No films match that filter.")
            else:
                st.dataframe(_build_rate_rows(mfr_films), use_container_width=True)



    # ── Quick Cost Calculator ──────────────────
    st.divider()
    st.subheader("⚡ Quick Cost Calculator")
    st.caption("Select a film and enter a quantity to get an instant cost estimate.")

    all_film_names_qc = sorted(FILM_RATES.keys())
    qc_col1, qc_col2, qc_col3 = st.columns(3)

    with qc_col1:
        selected_film = st.selectbox("Film", options=all_film_names_qc, key="qc_film")

    available_widths = sorted(FILM_RATES.get(selected_film, {}).keys())

    with qc_col2:
        selected_width = st.selectbox(
            "Roll Width",
            options=available_widths,
            format_func=lambda w: f'{w}"',
            key="qc_width"
        )

    with qc_col3:
        qty_lf = st.number_input("Linear Feet Needed", min_value=1, value=50, step=5, key="qc_lf")

    if selected_film and selected_width and qty_lf:
        result = calculate_material_cost(selected_film, selected_width, qty_lf, 0)

        st.markdown("---")
        res_col1, res_col2, res_col3 = st.columns(3)

        with res_col1:
            st.metric("Order Quantity", f"{result['order_lf']} LF")
            st.metric("Order Method", result["order_method"].replace("_", " ").title())

        with res_col2:
            if result.get("btf_cost"):
                st.metric("By-the-Foot Cost", f"${result['btf_cost']:,.2f}")
            if result.get("full_roll_cost"):
                st.metric("Full Roll Cost", f"${result['full_roll_cost']:,.2f}")

        with res_col3:
            st.metric("Recommended Cost", f"${result['recommended_cost']:,.2f}")
            if result.get("full_roll_savings"):
                st.success(f"💡 Buy the full roll and save ${result['full_roll_savings']:.2f}!")

        floor = get_price_floor(selected_film)
        sqft = (selected_width / 12) * qty_lf
        floor_sell = round(floor * sqft, 2)
        st.caption(
            f"Estimated sqft at {selected_width}\" × {qty_lf} LF = {sqft:.1f} sqft | "
            f"Min sell floor: ${floor_sell:,.2f}"
        )
        if selected_film in CAULKING_FILMS:
            st.info("🛡️ This is a safety/security film (8mil+). Caulking will be required at installation.")
