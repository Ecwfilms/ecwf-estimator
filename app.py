
# East Coast Window Films — Internal Estimator v4
# Streamlit UI with per-window complexity scoring, room selector, Go/No-Go engine,
# Film Lookup tab, equipment rental, and exterior install premium.

import streamlit as st
from worksheet_parser import extract_text_from_pdf, extract_window_data
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
    GO_NOGO_MIN_MARGIN,
    GO_NOGO_WARN_MARGIN,
)
from pane_expander import expand_windows

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
    st.caption("Film costs loaded from Edge, Huper Optik, and Solyx/Decorative Films. Verified Mar 2026.")

# ─────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────
tab_estimator, tab_lookup = st.tabs(["📋 Estimator", "🔍 Film Lookup"])

# ═════════════════════════════════════════════
# TAB 1: ESTIMATOR
# ═════════════════════════════════════════════
with tab_estimator:

    uploaded_file = st.file_uploader(
        "Upload TintWiz Worksheet",
        type=["pdf"],
        accept_multiple_files=False,
        help="Export the worksheet from TintWiz as a PDF and upload it here."
    )

    if uploaded_file:
        text = extract_text_from_pdf(uploaded_file)
        parsed = extract_window_data(text)

        windows = parsed["windows"]
        section_meta = parsed["section_meta"]
        project_total_sqft = parsed["project_total_sqft"]
        project_total_panes = parsed["project_total_panes"]

        if not windows:
            st.error("No window data could be parsed from this PDF. Please check the file format.")
            st.stop()

        section_groups = group_windows_by_section(windows)
        all_section_names = list(section_groups.keys())

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

        # ── Additional Line Items ────────────────
        st.subheader("🔧 Additional Line Items")

        add_col1, add_col2, add_col3 = st.columns(3)

        with add_col1:
            caulking_lf = st.number_input(
                "Caulking (Linear Feet)",
                min_value=0.0,
                value=0.0,
                step=1.0,
                help="Enter total linear feet of caulking required. Charged at $3.00/LF."
            )
            caulking_cost = calculate_caulking_cost(caulking_lf)
            if caulking_lf > 0:
                st.caption(f"Caulking: {caulking_lf:.0f} LF × $3.00 = **${caulking_cost:.2f}**")

        with add_col2:
            equipment_rental = st.number_input(
                "Equipment Rental ($)",
                min_value=0.0,
                value=0.0,
                step=50.0,
                help="Lift, scaffold, or other equipment rental cost for this job. Added directly to total job cost."
            )
            if equipment_rental > 0:
                st.caption(f"Equipment rental: **${equipment_rental:,.2f}**")

        with add_col3:
            exterior_premium_pct = st.number_input(
                "Exterior Install Premium (%)",
                min_value=0.0,
                max_value=100.0,
                value=0.0,
                step=5.0,
                help="Percentage markup added to the recommended sell price for exterior installations. e.g., 25 adds 25% to the sell price."
            )
            if exterior_premium_pct > 0:
                st.caption(f"Exterior premium: **{exterior_premium_pct:.0f}%** added to sell price")

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
                    st.info("🛡️ Safety & Security film — ordered in full rolls only. Labor rate: $3.50/sqft.")

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
                else:
                    for fkey in COMPLEXITY_ADDERS.keys():
                        complexity_flags[fkey] = False

                labor_info = calculate_line_item_labor(line_sqft, w_film, complexity_flags)
                section_labor_total += labor_info["labor_cost"]

                if any(complexity_flags.values()):
                    complexity_summary.append(
                        f"{w_desc}: {', '.join(labor_info['active_factors'])} → ${labor_info['labor_cost']:.2f} labor"
                    )

            # Selling price (includes labor)
            pricing = calculate_selling_price(
                best["mat_cost"],
                section_labor_total,
                section_sqft,
                target_margin,
                daily_revenue_target,
                min_job_price,
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
            # Group material costs by supplier to check thresholds
            supplier_totals: dict = {}
            for sname, res in section_results.items():
                if res.get("error") or not res.get("is_active"):
                    continue
                supplier = get_supplier(res["primary_film"])
                supplier_totals[supplier] = supplier_totals.get(supplier, 0.0) + res["mat_cost"]

            st.markdown("**Shipping Status:**")
            for supplier, total in sorted(supplier_totals.items()):
                shipping = check_free_shipping(list(FILM_RATES.keys())[0], total)
                # Use the supplier directly
                threshold = 1000.0
                if total >= threshold:
                    st.success(f"✅ {supplier}: ${total:,.2f} — **Free shipping** (over ${threshold:,.0f})")
                else:
                    shortfall = round(threshold - total, 2)
                    st.warning(f"⚠️ {supplier}: ${total:,.2f} — Add ${shortfall:,.2f} more to qualify for free shipping")

            st.divider()     # ─────────────────────────────────────────
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

            st.divider()

            if active_decision["color"] == "green":
                st.success(f"✅ **{active_decision['message']}** — Gross Profit: ${active_decision['gross_profit']:,.2f}")
            elif active_decision["color"] == "yellow":
                st.warning(f"⚠️ **{active_decision['message']}** — Gross Profit: ${active_decision['gross_profit']:,.2f}")
            else:
                st.error(f"🚫 **{active_decision['message']}** — Consider raising the price or declining this job.")

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

    else:
        st.info("Upload a TintWiz worksheet PDF using the uploader above to get started.")


# ═════════════════════════════════════════════
# TAB 2: FILM LOOKUP
# ═════════════════════════════════════════════
with tab_lookup:
    st.subheader("🔍 Film Price Lookup")
    st.caption("Search any film in the database to see wholesale cost, full roll price, and cost per sqft on the fly.")

    # Build a flat list of all films for the search
    all_film_names = sorted(FILM_RATES.keys())

    search_query = st.text_input(
        "Search film by name or code",
        placeholder="e.g., UltraView, SXF-5050, Ceramic 40, Guardian...",
        help="Type any part of the film name or product code."
    )

    if search_query:
        matches = [f for f in all_film_names if search_query.lower() in f.lower()]
    else:
        matches = all_film_names

    if not matches:
        st.warning(f"No films found matching '{search_query}'. Try a different search term.")
    else:
        st.caption(f"Showing {len(matches)} film(s).")

        lookup_rows = []
        for film_name in matches:
            widths = FILM_RATES[film_name]
            for width, rates in sorted(widths.items()):
                btf_base = rates.get("btf_base")
                btf_fee = rates.get("btf_fee", 0)
                roll_100 = rates.get("roll_100lf")
                roll_50 = rates.get("roll_50lf")

                if btf_base is not None:
                    btf_total = btf_base + btf_fee
                    btf_per_sqft = round(btf_total / (width / 12), 3)
                    btf_display = f"${btf_total:.3f}/LF (${btf_per_sqft:.3f}/sqft)"
                else:
                    btf_display = "Full roll only"
                    btf_per_sqft = None

                if roll_100:
                    roll_100_per_sqft = round(roll_100 / (width / 12) / 100, 3)
                    roll_100_display = f"${roll_100:,.2f} (${roll_100_per_sqft:.3f}/sqft)"
                else:
                    roll_100_display = "—"

                roll_50_display = f"${roll_50:,.2f}" if roll_50 else "—"

                floor = get_price_floor(film_name)

                lookup_rows.append({
                    "Film": film_name,
                    "Width": f"{width}\"",
                    "By the Foot": btf_display,
                    "100 LF Roll": roll_100_display,
                    "50 LF Roll": roll_50_display,
                    "Min Sell Floor": f"${floor:.2f}/sqft",
                })

        if lookup_rows:
            st.dataframe(lookup_rows, use_container_width=True)

        # Quick calculator
        st.divider()
        st.subheader("⚡ Quick Cost Calculator")
        st.caption("Select a film and enter a quantity to get an instant cost estimate.")

        qc_col1, qc_col2, qc_col3 = st.columns(3)

        with qc_col1:
            selected_film = st.selectbox("Film", options=all_film_names, key="qc_film")

        available_widths = sorted(FILM_RATES.get(selected_film, {}).keys())

        with qc_col2:
            selected_width = st.selectbox(
                "Roll Width",
                options=available_widths,
                format_func=lambda w: f"{w}\"",
                key="qc_width"
            )

        with qc_col3:
            qty_lf = st.number_input("Linear Feet Needed", min_value=1, value=50, step=5, key="qc_lf")

        if selected_film and selected_width and qty_lf:
            result = calculate_material_cost(selected_film, selected_width, qty_lf, 0)
            rates = result["rates"]

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
            st.caption(f"Estimated sqft at {selected_width}\" × {qty_lf} LF = {sqft:.1f} sqft | Min sell floor: ${floor_sell:,.2f}")
