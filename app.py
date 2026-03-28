# app.py
# East Coast Window Films — Internal Estimator v2.3

import math
import streamlit as st
from worksheet_parser import extract_text_from_pdf, extract_window_data
from pricing_engine import (
    optimize_for_roll_width, group_windows_by_section,
    calculate_material_cost, calculate_labor_cost,
    calculate_sub_labor, calculate_profit_floor,
    build_quote, check_override, detect_high_work,
    run_crew_optimizer,
    CREW_CONFIG, REMOVAL_RATE_PER_SQFT,
)
from pane_expander import expand_windows

st.set_page_config(page_title="ECWF Estimator", page_icon="🪟", layout="wide")

st.markdown("""
<style>
  .ribbon { background:linear-gradient(135deg,#0d1f35 0%,#091628 100%);
    border:1px solid #2e4870; border-radius:8px; padding:16px 20px; margin-bottom:20px; }
  .ribbon-green  { border-color:#00e5a0 !important; }
  .ribbon-amber  { border-color:#ffb300 !important; }
  .ribbon-red    { border-color:#ff4455 !important; }
  .walk-box  { background:rgba(255,179,0,0.08);  border:1px solid rgba(255,179,0,0.4);
    border-radius:6px; padding:10px 14px; margin:6px 0; }
  .target-box{ background:rgba(0,229,160,0.08);  border:1px solid rgba(0,229,160,0.4);
    border-radius:6px; padding:10px 14px; margin:6px 0; }
  .loss-box  { background:rgba(255,68,85,0.12);  border:2px solid #ff4455;
    border-radius:6px; padding:10px 14px; margin:6px 0; }
  .rule-win  { background:rgba(0,229,160,0.10);  border:1px solid rgba(0,229,160,0.3);
    border-radius:4px; padding:6px 10px; margin:3px 0; }
  .rule-norm { padding:6px 10px; margin:3px 0; color:#8899aa; }
  .hw-badge  { background:rgba(255,179,0,0.15);  color:#ffb300; border-radius:3px;
    padding:2px 8px; font-size:11px; font-weight:700; }
  .rem-badge { background:rgba(167,139,250,0.15); color:#a78bfa; border-radius:3px;
    padding:2px 8px; font-size:11px; font-weight:700; }
</style>
""", unsafe_allow_html=True)

st.markdown("## 🪟 East Coast Window Films — Estimator")
st.caption("Internal use only. Upload a TintWiz worksheet PDF to begin.")

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Job Settings")

    crew_type = st.selectbox(
        "Crew Type",
        options=list(CREW_CONFIG.keys()),
        format_func=lambda k: CREW_CONFIG[k]["label"],
        help="Sets production rate, labor cost, and base profit floor."
    )

    buffer_lf = st.number_input(
        "Installer Buffer (LF)", min_value=0.0, value=10.0, step=5.0,
        help="Extra linear feet added to material order."
    )

    cfg = CREW_CONFIG[crew_type]
    st.divider()
    st.caption(
        f"**{cfg['label']}**\n\n"
        f"Labor cost: **${cfg['daily_cost']:.2f}/day**\n\n"
        f"Production: **{cfg['sqft_per_day']} sqft/day**\n\n"
        f"Base floor: **${cfg['base_floor']:.2f}/day**"
    )

    # Profit Floor Settings — shown after a file is loaded
    st.divider()
    st.subheader("📊 Profit Floor Settings")

    # Placeholder — will be updated after job loads
    floor_placeholder = st.empty()

    st.divider()
    st.subheader("💬 Negotiation Override")
    override_input = st.number_input(
        "Client Offer / Your Override ($)",
        min_value=0.0, value=0.0, step=50.0,
    )

    st.divider()
    st.caption("Film costs: Edge, Huper Optik, ASWF. Verified Mar 2026.\n\n3% tariff applied to Edge & Huper Optik orders.")

# ─────────────────────────────────────────────────────────────────────────────
# FILE UPLOAD
# ─────────────────────────────────────────────────────────────────────────────
uploaded_file = st.file_uploader("Upload TintWiz Worksheet", type=["pdf"])

if not uploaded_file:
    st.info("Upload a TintWiz worksheet PDF to begin.")
    st.stop()

text   = extract_text_from_pdf(uploaded_file)
parsed = extract_window_data(text)

windows             = parsed["windows"]
section_meta        = parsed["section_meta"]
project_total_sqft  = parsed.get("project_total_sqft") or 0
project_total_panes = parsed.get("project_total_panes") or 0
client_info         = parsed.get("client_info", {})

if not windows:
    st.error("No window data found. Check the PDF format.")
    st.stop()

section_groups = group_windows_by_section(windows)

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE — room toggles and flags
# ─────────────────────────────────────────────────────────────────────────────
for sec_name in section_groups:
    meta = section_meta.get(sec_name, {})
    for key, default in [
        (f"active_{sec_name}", True),
        (f"hw_{sec_name}",     meta.get("high_work", False)),
        (f"rem_{sec_name}",    meta.get("has_removal", False)),
        (f"ext_{sec_name}",    meta.get("is_exterior", False)),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

# ─────────────────────────────────────────────────────────────────────────────
# JOB-LEVEL FLAG AGGREGATION (for profit floor auto-calc)
# ─────────────────────────────────────────────────────────────────────────────
any_high_work = any(st.session_state.get(f"hw_{s}", False)  for s in section_groups)
any_removal   = any(st.session_state.get(f"rem_{s}", False) for s in section_groups)
any_exterior  = any(st.session_state.get(f"ext_{s}", False) for s in section_groups)

floor_info = calculate_profit_floor(crew_type, any_high_work, any_removal, any_exterior)

# Profit floor override widget (now we know floor_info)
with floor_placeholder.container():
    st.caption(f"**Auto Floor:** ${floor_info['calculated']:.2f}/day\n\n_{floor_info['label']}_")
    floor_override = st.number_input(
        "Override Floor ($/day)",
        min_value=0.0,
        value=float(floor_info["calculated"]),
        step=50.0,
        key="floor_override_input",
        help="Override the auto-calculated profit floor for this job."
    )
    active_floor = floor_override if floor_override != floor_info["calculated"] else floor_info["calculated"]
    if floor_override != floor_info["calculated"]:
        st.caption(f"⚡ **Override active:** ${floor_override:.2f}/day (auto was ${floor_info['calculated']:.2f})")
    else:
        st.caption(f"✅ Using auto floor: **${active_floor:.2f}/day**")

# ─────────────────────────────────────────────────────────────────────────────
# PER-SECTION CALCULATIONS
# ─────────────────────────────────────────────────────────────────────────────
section_results       = {}
total_mat_cost        = 0.0
total_tariff          = 0.0
total_labor_cost      = 0.0
total_removal_cost    = 0.0
total_active_sqft     = 0.0
total_days            = 0

for section_name, section_windows in section_groups.items():
    if not st.session_state.get(f"active_{section_name}", True):
        continue

    section_panes = expand_windows(section_windows)
    film_names    = sorted(set(w["film"] for w in section_windows))
    primary_film  = film_names[0] if film_names else "UltraView 15"
    section_sqft  = section_meta.get(section_name, {}).get("room_total_sqft", 0) or 0

    is_high_work = st.session_state.get(f"hw_{section_name}", False)
    has_removal  = st.session_state.get(f"rem_{section_name}", False)
    is_exterior  = st.session_state.get(f"ext_{section_name}", False)

    # Roll optimization
    comparison = []
    for roll in [48, 60, 72]:
        try:
            opt  = optimize_for_roll_width(section_panes, roll)
            cost = calculate_material_cost(primary_film, roll, opt["total_lf"], buffer_lf)
            comparison.append({
                "roll": roll, "required_lf": opt["total_lf"],
                "order_lf": cost["order_lf"],
                "mat_cost": cost["recommended_cost"],
                "mat_subtotal": cost["mat_subtotal"],
                "tariff": cost["tariff"],
                "order_lines": cost["order_lines"],
                "order_method": cost["order_method"],
                "rates": cost["rates"],
                "rows": opt["rows"],
                "full_roll_savings": cost.get("full_roll_savings"),
            })
        except ValueError:
            pass

    if not comparison:
        continue

    best = min(comparison, key=lambda x: x["mat_cost"])

    # Labor — sub is per-section (sqft × rate), owner is accumulated then recalculated at job level
    if crew_type == "sub":
        sub_result    = calculate_sub_labor(section_sqft, primary_film, is_high_work, is_exterior)
        section_labor = sub_result["cost"]
        sub_rate      = sub_result["rate"]
        labor_note    = f"{section_sqft} sqft × ${sub_rate:.2f}/sqft"
    else:
        section_labor = 0.0  # owner labor calculated at job level below
        sub_rate      = 0.0
        labor_note    = ""

    # Removal adder
    removal_cost = round(section_sqft * REMOVAL_RATE_PER_SQFT, 2) if has_removal else 0.0

    # Days for this section
    if crew_type == "sub":
        # Sub days calculated at job level (single pass), not per section
        sec_days = 0  # will be set at job level below
    else:
        labor_result2 = calculate_labor_cost(section_sqft, crew_type, has_removal,
                                              removal_sqft=section_sqft if has_removal else 0.0)
        sec_days = labor_result2["days"]

    total_mat_cost     += best["mat_subtotal"]
    total_tariff       += best["tariff"]
    total_labor_cost   += section_labor
    total_removal_cost += removal_cost
    total_active_sqft  += section_sqft
    total_days         = max(total_days, sec_days)  # parallel work assumption

    section_results[section_name] = {
        "best": best, "comparison": comparison,
        "film_names": film_names, "primary_film": primary_film,
        "section_sqft": section_sqft,
        "section_labor": section_labor, "sub_rate": sub_rate, "labor_note": labor_note,
        "removal_cost": removal_cost,
        "is_high_work": is_high_work, "has_removal": has_removal, "is_exterior": is_exterior,
        "notes": section_meta.get(section_name, {}).get("notes", ""),
        "sec_days": sec_days,
    }

# Total days — single pass for all crew types (one crew, one visit, full job)
import math as _math
_rate = CREW_CONFIG[crew_type]["sqft_per_day"]
total_days = _math.ceil(total_active_sqft / _rate) if total_active_sqft > 0 else 1

# Owner labor calculated at job level using single-pass days
if crew_type != "sub":
    total_labor_cost = round(total_days * CREW_CONFIG[crew_type]["daily_cost"], 2)

# ─────────────────────────────────────────────────────────────────────────────
# JOB-LEVEL QUOTE
# ─────────────────────────────────────────────────────────────────────────────
quote = build_quote(
    material_cost = total_mat_cost,
    tariff        = total_tariff,
    labor_cost    = total_labor_cost,
    removal_cost  = total_removal_cost,
    total_sqft    = total_active_sqft,
    crew_type     = crew_type,
    active_floor  = active_floor,
    days          = total_days,
)

ovr = check_override(override_input, quote) if override_input > 0 else None

# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY RIBBON
# ─────────────────────────────────────────────────────────────────────────────
client_name  = client_info.get("client_name", uploaded_file.name.replace(".pdf",""))
project_type = client_info.get("project_type", "")
display_name = client_name + (f" — {project_type}" if project_type else "")

display_price = ovr["price"] if ovr else quote["recommended"]
price_label   = "OVERRIDE PRICE" if ovr else "RECOMMENDED SELL PRICE"

# Ribbon state
if ovr and ovr["is_loss"]:
    ribbon_state, ribbon_border, price_color = "red",   "#ff4455", "#ff4455"
elif ovr and ovr["is_caution"]:
    ribbon_state, ribbon_border, price_color = "amber", "#ffb300", "#ffb300"
else:
    ribbon_state, ribbon_border, price_color = "green", "#00e5a0", "#00e5a0"

labor_label = f"{'Sub' if crew_type == 'sub' else CREW_CONFIG[crew_type]['label']} Labor"

st.markdown(f"""
<div class="ribbon ribbon-{ribbon_state}" style="border-color:{ribbon_border}">
  <div style="font-size:10px;color:#00e5a0;letter-spacing:.2em;text-transform:uppercase;margin-bottom:2px">PROJECT</div>
  <div style="font-size:20px;font-weight:700;color:#e8f0fe;margin-bottom:14px">{display_name}</div>
  <div style="display:grid;grid-template-columns:repeat(6,1fr);gap:10px">
    <div style="background:rgba(0,0,0,.25);border-radius:4px;padding:8px 10px">
      <div style="font-size:9px;color:#8899aa;text-transform:uppercase;letter-spacing:.08em">Total SqFt</div>
      <div style="font-size:16px;font-weight:700;color:#e8f0fe">{total_active_sqft:.0f} sqft</div>
    </div>
    <div style="background:rgba(0,0,0,.25);border-radius:4px;padding:8px 10px">
      <div style="font-size:9px;color:#8899aa;text-transform:uppercase;letter-spacing:.08em">Material</div>
      <div style="font-size:16px;font-weight:700;color:#e8f0fe">${total_mat_cost:,.2f}</div>
      <div style="font-size:9px;color:#8899aa">+${total_tariff:.2f} tariff</div>
    </div>
    <div style="background:rgba(0,0,0,.25);border-radius:4px;padding:8px 10px">
      <div style="font-size:9px;color:#8899aa;text-transform:uppercase;letter-spacing:.08em">{labor_label}</div>
      <div style="font-size:16px;font-weight:700;color:#e8f0fe">${total_labor_cost:,.2f}</div>
    </div>
    <div style="background:rgba(0,0,0,.25);border-radius:4px;padding:8px 10px">
      <div style="font-size:9px;color:#8899aa;text-transform:uppercase;letter-spacing:.08em">Days on Site</div>
      <div style="font-size:16px;font-weight:700;color:#e8f0fe">{total_days} day(s)</div>
      <div style="font-size:9px;color:#8899aa">floor: ${active_floor:.0f}/day</div>
    </div>
    <div style="background:rgba(255,179,0,.08);border:1px solid rgba(255,179,0,.3);border-radius:4px;padding:8px 10px">
      <div style="font-size:9px;color:#ffb300;text-transform:uppercase;letter-spacing:.08em">Walk-Away</div>
      <div style="font-size:16px;font-weight:700;color:#ffb300">${quote['walk_away']:,.2f}</div>
    </div>
    <div style="background:rgba(0,0,0,.25);border:1px solid {ribbon_border};border-radius:4px;padding:8px 10px">
      <div style="font-size:9px;color:{price_color};text-transform:uppercase;letter-spacing:.08em">{price_label}</div>
      <div style="font-size:20px;font-weight:700;color:{price_color}">${display_price:,.2f}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# Override warnings
if ovr:
    if ovr["is_loss"]:
        st.error(f"⛔ **BELOW WALK-AWAY — THIS IS A LOSS.** Override ${override_input:,.2f} vs walk-away ${quote['walk_away']:,.2f}. Gross profit would be **${ovr['gp']:,.2f}** (${ovr['ppd']:,.2f}/day vs ${active_floor:.0f}/day floor).")
    elif ovr["is_caution"]:
        st.warning(f"⚠️ **Caution — below recommended target.** You're above walk-away but leaving **${quote['recommended'] - override_input:,.2f}** on the table. Margin: {ovr['marg']}% · ${ovr['ppd']:,.2f}/day.")

# ─────────────────────────────────────────────────────────────────────────────
# QUOTE BUILDER PANEL
# ─────────────────────────────────────────────────────────────────────────────
with st.expander("💰 Quote Builder — Price Logic", expanded=True):
    col_rules, col_numbers = st.columns([1.2, 1])

    with col_rules:
        st.markdown("**How the Recommended Price was set:**")
        for label, val, key in [
            ("A) Walk-Away × 1.30",   quote["rule_a"], "margin_buffer"),
            ("B) $1,200 Min Ticket",   quote["rule_b"], "min_ticket"),
            ("C) $7.50/sqft Floor",    quote["rule_c"], "sqft_floor"),
        ]:
            is_win = quote["winning_rule"] == key
            css = "rule-win" if is_win else "rule-norm"
            arrow = " ← **WINNER**" if is_win else ""
            st.markdown(
                f'<div class="{css}">{"✅ " if is_win else ""}{label}: **${val:,.2f}**{arrow}</div>',
                unsafe_allow_html=True
            )
        st.markdown("---")
        st.markdown(
            f'<div class="walk-box">**Walk-Away: ${quote["walk_away"]:,.2f}**<br>'
            f'<small>Costs ${quote["total_cost"]:,.2f} + {total_days} day(s) × ${active_floor:.0f} floor</small></div>',
            unsafe_allow_html=True
        )
        st.markdown(
            f'<div class="target-box">**Recommended: ${quote["recommended"]:,.2f}** — {quote["winning_label"]}</div>',
            unsafe_allow_html=True
        )
        st.caption(
            f"Daily revenue needed: **${quote['daily_revenue_needed']:,.2f}/day** "
            f"(costs ${round(quote['total_cost']/total_days,2):,.2f}/day + ${active_floor:.0f} floor)"
        )

    with col_numbers:
        st.metric("Gross Profit",  f"${quote['gross_profit']:,.2f}")
        st.metric("Margin %",      f"{quote['margin_pct']}%")
        st.metric("Profit / Day",  f"${quote['profit_per_day']:,.2f}",
                  delta=f"floor: ${active_floor:.0f}/day", delta_color="normal")
        st.metric("Days on Site",  f"{total_days}")
        st.caption(
            f"**Cost audit:** Material ${total_mat_cost:,.2f} · "
            f"Tariff ${total_tariff:,.2f} · "
            f"Labor ${total_labor_cost:,.2f} · "
            f"Removal ${total_removal_cost:,.2f} · "
            f"**Total ${quote['total_cost']:,.2f}**"
        )

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# CREW OPTIMIZER
# ─────────────────────────────────────────────────────────────────────────────
with st.expander("🔍 Analyze Crews — Find the Best Option for This Job", expanded=False):

    st.caption(
        "Runs all four crew types against this job's actual costs and flags. "
        "Scores each option based on job size, complexity, and profit efficiency."
    )

    # Get primary film for sub rate mapping
    all_films = []
    for res in section_results.values():
        all_films.extend(res["film_names"])
    primary_film_global = all_films[0] if all_films else "UltraView 15"

    optimizer_results = run_crew_optimizer(
        total_sqft     = total_active_sqft,
        total_mat_cost = total_mat_cost,
        total_tariff   = total_tariff,
        removal_cost   = total_removal_cost,
        primary_film   = primary_film_global,
        any_high_work  = any_high_work,
        any_removal    = any_removal,
        any_exterior   = any_exterior,
        floor_override = active_floor,
        active_crew    = crew_type,
        active_days    = total_days,
        active_labor   = total_labor_cost,
        active_quote   = quote,
    )

    # ── Recommended banner ────────────────────────────────────────────────
    winner = optimizer_results[0]
    st.markdown(
        f"""<div style="background:rgba(0,229,160,0.08);border:2px solid #00e5a0;
        border-radius:8px;padding:14px 18px;margin-bottom:16px">
        <div style="font-size:10px;color:#00e5a0;letter-spacing:.15em;
        text-transform:uppercase;margin-bottom:4px">✅ RECOMMENDED CREW</div>
        <div style="font-size:20px;font-weight:700;color:#e8f0fe;margin-bottom:6px">
        {winner['label']}</div>
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:8px">
          <div><div style="font-size:9px;color:#8899aa">Days on Site</div>
               <div style="font-size:16px;font-weight:700;color:#e8f0fe">{winner['days']}</div></div>
          <div><div style="font-size:9px;color:#8899aa">Labor Cost</div>
               <div style="font-size:16px;font-weight:700;color:#e8f0fe">${winner['labor_cost']:,.2f}</div></div>
          <div><div style="font-size:9px;color:#ffb300">Walk-Away</div>
               <div style="font-size:16px;font-weight:700;color:#ffb300">${winner['walk_away']:,.2f}</div></div>
          <div><div style="font-size:9px;color:#00e5a0">Recommended Price</div>
               <div style="font-size:18px;font-weight:700;color:#00e5a0">${winner['recommended']:,.2f}</div></div>
        </div>
        <div style="font-size:11px;color:#8899aa">
          Profit/day: <b style="color:#00e5a0">${winner['profit_per_day']:,.2f}</b> ·
          Gross profit: <b style="color:#e8f0fe">${winner['gross_profit']:,.2f}</b> ·
          Margin: <b style="color:#e8f0fe">{winner['margin_pct']}%</b>
        </div>
        {"".join([f'<span style="background:rgba(0,229,160,0.15);color:#00e5a0;border-radius:3px;padding:2px 8px;font-size:10px;margin-right:4px;margin-top:6px;display:inline-block">{n}</span>' for n in winner['fit_notes']])}
        </div>""",
        unsafe_allow_html=True
    )

    # ── Full comparison table ──────────────────────────────────────────────
    st.markdown("**All crew options compared:**")

    # Table header
    cols = st.columns([1.4, 0.7, 1, 1, 1, 1, 1.6])
    for col, hdr in zip(cols, ["Crew", "Days", "Labor Cost", "Walk-Away",
                                "Recommended", "Profit/Day", "Notes"]):
        col.markdown(f"<div style='font-size:10px;color:#8899aa;text-transform:uppercase;"
                     f"letter-spacing:.08em'>{hdr}</div>", unsafe_allow_html=True)

    st.markdown("<hr style='border-color:#1e3050;margin:4px 0 8px'>", unsafe_allow_html=True)

    for r in optimizer_results:
        is_win     = r["is_recommended"]
        row_color  = "#00e5a0" if is_win else "#e8f0fe"
        row_dim    = "1" if is_win else "0.7"
        cols = st.columns([1.4, 0.7, 1, 1, 1, 1, 1.6])

        cols[0].markdown(
            f"<div style='font-weight:{'700' if is_win else '400'};color:{row_color};opacity:{row_dim}'>"
            f"{'✅ ' if is_win else ''}{r['label']}</div>",
            unsafe_allow_html=True
        )
        cols[1].markdown(f"<div style='opacity:{row_dim}'>{r['days']} day(s)</div>",
                         unsafe_allow_html=True)
        cols[2].markdown(f"<div style='opacity:{row_dim}'>${r['labor_cost']:,.2f}</div>",
                         unsafe_allow_html=True)
        cols[3].markdown(f"<div style='color:#ffb300;opacity:{row_dim}'>${r['walk_away']:,.2f}</div>",
                         unsafe_allow_html=True)
        cols[4].markdown(f"<div style='font-weight:{'700' if is_win else '400'};color:{row_color};opacity:{row_dim}'>"
                         f"${r['recommended']:,.2f}</div>", unsafe_allow_html=True)
        cols[5].markdown(f"<div style='color:{'#00e5a0' if r['profit_per_day'] >= 800 else '#e8f0fe'};opacity:{row_dim}'>"
                         f"${r['profit_per_day']:,.2f}/day</div>", unsafe_allow_html=True)

        # Notes column — fit notes green, risk notes amber
        notes_html = ""
        for n in r["fit_notes"]:
            notes_html += f"<span style='background:rgba(0,229,160,0.12);color:#00e5a0;border-radius:3px;padding:1px 6px;font-size:9px;margin-right:3px'>{n}</span>"
        for n in r["risk_notes"]:
            notes_html += f"<span style='background:rgba(255,179,0,0.12);color:#ffb300;border-radius:3px;padding:1px 6px;font-size:9px;margin-right:3px'>{n}</span>"
        cols[6].markdown(notes_html or "<span style='color:#4a6080;font-size:10px'>—</span>",
                         unsafe_allow_html=True)

        st.markdown("<hr style='border-color:#1e3050;margin:3px 0'>", unsafe_allow_html=True)

    st.caption(
        "💡 To use a recommended crew, select it in the **Crew Type** dropdown in the sidebar. "
        "All numbers update instantly."
    )

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# CLIENT INFO
# ─────────────────────────────────────────────────────────────────────────────
if client_info:
    with st.expander("👤 Client Info", expanded=False):
        cols = st.columns(3)
        if "phone"   in client_info: cols[0].markdown(f"📞 {client_info['phone']}")
        if "email"   in client_info: cols[1].markdown(f"✉️ {client_info['email']}")
        if "address" in client_info: cols[2].markdown(f"📍 {client_info['address']}")

# ─────────────────────────────────────────────────────────────────────────────
# PROJECT SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("📋 Project Summary")
c1, c2, c3 = st.columns(3)
c1.metric("Active SqFt",      f"{total_active_sqft:.0f} sqft")
c2.metric("Total Panes",      f"{project_total_panes}")
c3.metric("Active Sections",  f"{len(section_results)} of {len(section_groups)}")
st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# ROOM BREAKDOWN
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("🏠 Room Breakdown")
st.caption("Toggle rooms on/off — Tetris re-runs automatically on active rooms.")

order_lines = []

for section_name, section_windows in section_groups.items():
    meta = section_meta.get(section_name, {})

    # ── Room header checkbox ───────────────────────────────────────────────
    hdr_cols = st.columns([0.05, 0.95])
    with hdr_cols[0]:
        active = st.checkbox("", value=st.session_state.get(f"active_{section_name}", True),
                             key=f"cb_active_{section_name}", label_visibility="collapsed")
        st.session_state[f"active_{section_name}"] = active

    with hdr_cols[1]:
        sqft_disp  = meta.get("room_total_sqft", 0) or 0
        panes_disp = meta.get("section_panes_header", 0)
        status     = "" if active else " *(excluded)*"
        badges = ""
        if st.session_state.get(f"hw_{section_name}"):
            badges += ' <span class="hw-badge">⚠ HIGH WORK</span>'
        if st.session_state.get(f"rem_{section_name}"):
            badges += ' <span class="rem-badge">🔧 REMOVAL</span>'
        st.markdown(
            f"**{section_name}**{status} — {panes_disp} panes · {sqft_disp} sqft{badges}",
            unsafe_allow_html=True
        )

    if not active:
        st.divider(); continue

    res = section_results.get(section_name)
    if not res:
        st.warning(f"No valid roll width for '{section_name}'. Check pane dimensions.")
        st.divider(); continue

    best = res["best"]

    # Notes
    if res["notes"]:
        st.info(f"📋 **Notes:** {res['notes']}")

    # ── Complexity flags ───────────────────────────────────────────────────
    flag_cols = st.columns(3)
    with flag_cols[0]:
        hw = st.checkbox("⚠ High Work / Lift (12–25 ft AFF)",
                         value=st.session_state.get(f"hw_{section_name}", False),
                         key=f"cb_hw_{section_name}",
                         help="Bumps sub rate $3.00→$3.25/sqft · Floor +$150/day")
        st.session_state[f"hw_{section_name}"] = hw
    with flag_cols[1]:
        ext = st.checkbox("🌤 Exterior Install",
                          value=st.session_state.get(f"ext_{section_name}", False),
                          key=f"cb_ext_{section_name}",
                          help="Floor +$100/day")
        st.session_state[f"ext_{section_name}"] = ext
    with flag_cols[2]:
        rem = st.checkbox("🔧 Film Removal",
                          value=st.session_state.get(f"rem_{section_name}", False),
                          key=f"cb_rem_{section_name}",
                          help=f"Adds ${REMOVAL_RATE_PER_SQFT:.2f}/sqft removal cost · 30% slower production · Floor +$100/day")
        st.session_state[f"rem_{section_name}"] = rem

    # ── Section numbers ────────────────────────────────────────────────────
    info_col, cost_col = st.columns([2, 1])

    with info_col:
        film_display = ", ".join(res["film_names"])
        rate         = best["rates"]
        rate_display = f"${rate['btf_base']:.2f}/LF base + ${rate['btf_fee']:.2f}/LF fee"

        st.markdown(f"**Film:** {film_display}")
        st.markdown(f"**Best Roll:** {best['roll']}\" | **Dealer Rate:** {rate_display}")
        st.markdown(f"**Required:** {best['required_lf']} LF + {buffer_lf:.0f} LF buffer")

        # Order lines
        for line in best["order_lines"]:
            icon = "📦" if line["type"] == "full_roll" else "📏"
            st.markdown(f"{icon} **{line['note']}** — ${line['cost']:.2f}")
        if best["tariff"] > 0:
            st.markdown(f"🌐 **Tariff (3%):** ${best['tariff']:.2f}")
        st.markdown(f"**Material Total:** ${best['mat_cost']:.2f}")

        # Labor line
        if crew_type == "sub":
            rate_lbl = f"${res['sub_rate']:.2f}/sqft"
            if res["is_high_work"]: rate_lbl += " (HIGH WORK)"
            if res["is_exterior"]:  rate_lbl += " (EXTERIOR)"
            st.markdown(f"**Sub Labor:** {res['section_sqft']} sqft × {rate_lbl} = **${res['section_labor']:.2f}**")
        else:
            st.markdown(f"**Labor ({CREW_CONFIG[crew_type]['label']}):** {res['labor_note']} = **${res['section_labor']:.2f}**")

        if res["removal_cost"] > 0:
            st.markdown(f"**Removal:** {res['section_sqft']} sqft × ${REMOVAL_RATE_PER_SQFT:.2f}/sqft = **${res['removal_cost']:.2f}**")

    with cost_col:
        # Section-level quote
        sec_quote = build_quote(
            material_cost = best["mat_subtotal"],
            tariff        = best["tariff"],
            labor_cost    = res["section_labor"],
            removal_cost  = res["removal_cost"],
            total_sqft    = res["section_sqft"],
            crew_type     = crew_type,
            active_floor  = active_floor,
            days          = res["sec_days"],
        )
        st.metric("Section Walk-Away",   f"${sec_quote['walk_away']:,.2f}")
        st.metric("Section Recommended", f"${sec_quote['recommended']:,.2f}",
                  help=f"Rule: {sec_quote['winning_label']}")
        st.caption(f"Mat ${best['mat_cost']:.2f} · Labor ${res['section_labor']:.2f} · {res['sec_days']} day(s)")

    # ── Roll comparison ────────────────────────────────────────────────────
    with st.expander(f"Roll width comparison — {section_name}"):
        for item in res["comparison"]:
            marker = " ✅ best" if item["roll"] == best["roll"] else ""
            method = item["order_method"].replace("_", " ")
            st.write(
                f"{item['roll']}\" roll | Required: {item['required_lf']} LF | "
                f"Order: {item['order_lf']} LF ({method}) | "
                f"Material: ${item['mat_cost']:.2f}{marker}"
            )

    # ── Cut sheet — deduplicated ───────────────────────────────────────────
    with st.expander(f"Cut sheet — {section_name}"):
        rows = best["rows"]
        # Group identical rows
        grouped = []
        for row in rows:
            sig = f"{row['used_width']}w-{row['pull_to']}h-{row['lanes']}l"
            pane_text = " + ".join([f"{p['width']}×{p['height']}" for p in row["panes"]])
            if grouped and grouped[-1]["sig"] == sig:
                grouped[-1]["count"] += 1
            else:
                grouped.append({"sig": sig, "count": 1, "pane_text": pane_text,
                                 "used_width": row["used_width"], "pull_to": row["pull_to"],
                                 "lanes": row["lanes"]})
        for g in grouped:
            count_label = f"{g['count']}× " if g["count"] > 1 else ""
            st.write(
                f"{count_label}**{g['pane_text']}** | "
                f"Width used: {g['used_width']}\" | "
                f"Pull to: {g['pull_to']}\" | "
                f"Lanes: {g['lanes']}"
            )

    order_method_label = best["order_method"].replace("_", " ").title()
    order_lines.append(
        f"{', '.join(res['film_names'])} — {best['roll']}\" × {best['order_lf']} LF ({order_method_label})"
    )
    st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# MATERIAL ORDER SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
if order_lines:
    st.subheader("🛒 Material Order Summary")
    for sec_name, res in section_results.items():
        best = res["best"]
        st.markdown(f"**{sec_name}** — {best['roll']}\" roll")
        for line in best["order_lines"]:
            st.markdown(f"  - {line['note']} · ${line['cost']:.2f}")
        if best["tariff"] > 0:
            st.markdown(f"  - Tariff (3%) · ${best['tariff']:.2f}")
        st.markdown(f"  **Section material total: ${best['mat_cost']:.2f}**")
    st.markdown(f"---")
    st.markdown(f"**Total material: ${total_mat_cost:,.2f} + ${total_tariff:,.2f} tariff = ${total_mat_cost+total_tariff:,.2f}**")
