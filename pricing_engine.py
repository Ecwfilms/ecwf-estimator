# pricing_engine.py
# East Coast Window Films — Pricing Engine v2.3
# Changes from v2.2:
#   - Four crew types: Owner Solo, Owner+Helper, Helper Only, Sub-Contractor
#   - Real owner/helper labor costs ($640/day, $880/day, $240/day)
#   - Job-aware profit floor with auto-elevation from complexity flags
#   - 3% tariff surcharge on Edge and Huper Optik orders
#   - Smart order splitting: max 70 LF BTF, full roll when difference < $30
#   - Removal production penalty: 30% slower

import math
from typing import Any, Dict, List, Optional, Tuple

# =============================================================================
# FILM RATE DATABASE
# =============================================================================

FILM_RATES: Dict[str, Dict[int, Dict[str, float]]] = {

    # ── EDGE UltraView ────────────────────────────────────────────────────────
    "UltraView 5":  {48:{"btf_base":5.87,"btf_fee":0.505,"roll_100lf":386.73}, 60:{"btf_base":6.88,"btf_fee":0.505,"roll_100lf":550.11}, 72:{"btf_base":7.50,"btf_fee":0.505,"roll_100lf":550.11}},
    "UltraView 15": {48:{"btf_base":5.87,"btf_fee":0.505,"roll_100lf":386.73}, 60:{"btf_base":6.88,"btf_fee":0.505,"roll_100lf":550.11}, 72:{"btf_base":7.50,"btf_fee":0.505,"roll_100lf":550.11}},
    "UltraView 20": {48:{"btf_base":5.87,"btf_fee":0.505,"roll_100lf":386.73}, 60:{"btf_base":6.88,"btf_fee":0.505,"roll_100lf":550.11}, 72:{"btf_base":7.50,"btf_fee":0.505,"roll_100lf":550.11}},
    "UltraView 25": {48:{"btf_base":5.87,"btf_fee":0.505,"roll_100lf":386.73}, 60:{"btf_base":6.88,"btf_fee":0.505,"roll_100lf":550.11}, 72:{"btf_base":7.50,"btf_fee":0.505,"roll_100lf":550.11}},
    "UltraView 35": {48:{"btf_base":5.87,"btf_fee":0.505,"roll_100lf":386.73}, 60:{"btf_base":6.88,"btf_fee":0.505,"roll_100lf":550.11}, 72:{"btf_base":7.50,"btf_fee":0.505,"roll_100lf":550.11}},
    "Edge Reform":        {48:{"btf_base":10.82,"btf_fee":0.505,"roll_100lf":1082.46}, 60:{"btf_base":12.02,"btf_fee":0.505,"roll_100lf":None}},
    "Edge Coal Alloy":    {48:{"btf_base":5.60,"btf_fee":0.505,"roll_100lf":559.76},  60:{"btf_base":6.28,"btf_fee":0.505,"roll_100lf":627.95},  72:{"btf_base":7.53,"btf_fee":0.505,"roll_100lf":752.73}},
    "Edge Silver":        {48:{"btf_base":3.81,"btf_fee":0.505,"roll_100lf":380.86},  60:{"btf_base":4.33,"btf_fee":0.505,"roll_100lf":432.56}},
    "Edge Bronze":        {48:{"btf_base":5.63,"btf_fee":0.505,"roll_100lf":563.03},  60:{"btf_base":6.36,"btf_fee":0.505,"roll_100lf":635.91},  72:{"btf_base":7.63,"btf_fee":0.505,"roll_100lf":762.86}},
    "Edge Pristine Ceramic": {48:{"btf_base":9.36,"btf_fee":0.505,"roll_100lf":935.63}, 60:{"btf_base":11.70,"btf_fee":0.505,"roll_100lf":1169.55}, 72:{"btf_base":14.63,"btf_fee":0.505,"roll_100lf":1463.45}},
    "Guardian 4mil":   {48:{"btf_base":4.35,"btf_fee":0.505,"roll_100lf":434.91}, 60:{"btf_base":4.81,"btf_fee":0.505,"roll_100lf":481.17}, 72:{"btf_base":5.80,"btf_fee":0.505,"roll_100lf":579.90}},
    "Guardian 8mil":   {48:{"btf_base":5.79,"btf_fee":0.505,"roll_100lf":579.40}, 60:{"btf_base":10.82,"btf_fee":0.505,"roll_100lf":1082.46}, 72:{"btf_base":8.73,"btf_fee":0.505,"roll_100lf":873.30}},
    "Guardian 12mil":  {48:{"btf_base":10.96,"btf_fee":0.505,"roll_100lf":1096.33}, 72:{"btf_base":13.13,"btf_fee":0.505,"roll_100lf":1312.95}},
    "Frost":     {48:{"btf_base":3.81,"btf_fee":0.505,"roll_100lf":380.84}, 60:{"btf_base":4.40,"btf_fee":0.505,"roll_100lf":439.60}, 72:{"btf_base":5.28,"btf_fee":0.505,"roll_100lf":527.77}},
    "Blackout":  {48:{"btf_base":4.16,"btf_fee":0.505,"roll_100lf":416.10}, 60:{"btf_base":4.83,"btf_fee":0.505,"roll_100lf":483.12}},
    "Whiteout":  {48:{"btf_base":4.58,"btf_fee":0.505,"roll_100lf":458.42}, 60:{"btf_base":5.33,"btf_fee":0.505,"roll_100lf":533.11}},
    "Clear Defense 4mil": {48:{"btf_base":4.35,"btf_fee":0.505,"roll_100lf":434.91}, 60:{"btf_base":4.83,"btf_fee":0.505,"roll_100lf":483.12}, 72:{"btf_base":5.76,"btf_fee":0.505,"roll_100lf":576.08}},
    "Clear Defense 6mil": {48:{"btf_base":5.62,"btf_fee":0.505,"roll_100lf":561.86}, 60:{"btf_base":6.30,"btf_fee":0.505,"roll_100lf":630.03}, 72:{"btf_base":7.50,"btf_fee":0.505,"roll_100lf":750.03}},

    # ── HUPER OPTIK ───────────────────────────────────────────────────────────
    "Huper Select Drei":  {36:{"btf_base":22.47,"btf_fee":0.505,"roll_100lf":None}, 48:{"btf_base":31.71,"btf_fee":0.505,"roll_100lf":None}, 60:{"btf_base":36.11,"btf_fee":0.505,"roll_100lf":None}, 72:{"btf_base":42.93,"btf_fee":0.505,"roll_100lf":None}},
    "Huper Select Sech":  {36:{"btf_base":18.87,"btf_fee":0.505,"roll_100lf":None}, 48:{"btf_base":26.40,"btf_fee":0.505,"roll_100lf":None}, 60:{"btf_base":30.12,"btf_fee":0.505,"roll_100lf":None}, 72:{"btf_base":35.74,"btf_fee":0.505,"roll_100lf":None}},
    "Huper Ceramic 20":   {36:{"btf_base":7.23,"btf_fee":0.505,"roll_100lf":None},  48:{"btf_base":10.10,"btf_fee":0.505,"roll_100lf":None}, 60:{"btf_base":11.53,"btf_fee":0.505,"roll_100lf":None}, 72:{"btf_base":13.56,"btf_fee":0.505,"roll_100lf":None}},
    "Huper Ceramic 30":   {36:{"btf_base":7.23,"btf_fee":0.505,"roll_100lf":None},  48:{"btf_base":10.10,"btf_fee":0.505,"roll_100lf":None}, 60:{"btf_base":11.53,"btf_fee":0.505,"roll_100lf":None}, 72:{"btf_base":13.56,"btf_fee":0.505,"roll_100lf":None}},
    "Huper Ceramic 40":   {36:{"btf_base":7.23,"btf_fee":0.505,"roll_100lf":None},  48:{"btf_base":10.10,"btf_fee":0.505,"roll_100lf":None}, 60:{"btf_base":11.53,"btf_fee":0.505,"roll_100lf":None}, 72:{"btf_base":22.05,"btf_fee":0.505,"roll_100lf":None}},
    "Huper Ceramic 50":   {36:{"btf_base":7.23,"btf_fee":0.505,"roll_100lf":None},  48:{"btf_base":10.10,"btf_fee":0.505,"roll_100lf":None}, 60:{"btf_base":11.53,"btf_fee":0.505,"roll_100lf":None}, 72:{"btf_base":13.56,"btf_fee":0.505,"roll_100lf":None}},
    "Huper Ceramic 60":   {36:{"btf_base":7.23,"btf_fee":0.505,"roll_100lf":None},  48:{"btf_base":10.10,"btf_fee":0.505,"roll_100lf":None}, 60:{"btf_base":11.53,"btf_fee":0.505,"roll_100lf":None}, 72:{"btf_base":13.56,"btf_fee":0.505,"roll_100lf":None}},
    "Huper Ceramic 70":   {36:{"btf_base":7.23,"btf_fee":0.505,"roll_100lf":None},  48:{"btf_base":10.10,"btf_fee":0.505,"roll_100lf":None}, 60:{"btf_base":11.53,"btf_fee":0.505,"roll_100lf":None}, 72:{"btf_base":13.56,"btf_fee":0.505,"roll_100lf":None}},
    "Huper Fusion 10":    {36:{"btf_base":5.67,"btf_fee":0.505,"roll_100lf":None},  48:{"btf_base":7.28,"btf_fee":0.505,"roll_100lf":None},  60:{"btf_base":8.12,"btf_fee":0.505,"roll_100lf":None},  72:{"btf_base":9.34,"btf_fee":0.505,"roll_100lf":None}},
    "Huper Fusion 20":    {36:{"btf_base":5.67,"btf_fee":0.505,"roll_100lf":None},  48:{"btf_base":7.28,"btf_fee":0.505,"roll_100lf":None},  60:{"btf_base":8.12,"btf_fee":0.505,"roll_100lf":None},  72:{"btf_base":9.34,"btf_fee":0.505,"roll_100lf":None}},
    "Huper Fusion 28":    {36:{"btf_base":5.67,"btf_fee":0.505,"roll_100lf":None},  48:{"btf_base":7.28,"btf_fee":0.505,"roll_100lf":None},  60:{"btf_base":8.12,"btf_fee":0.505,"roll_100lf":None},  72:{"btf_base":9.34,"btf_fee":0.505,"roll_100lf":None}},
    "Huper Bronze 25":    {36:{"btf_base":6.65,"btf_fee":0.505,"roll_100lf":None},  48:{"btf_base":8.66,"btf_fee":0.505,"roll_100lf":None},  60:{"btf_base":9.74,"btf_fee":0.505,"roll_100lf":None},  72:{"btf_base":11.29,"btf_fee":0.505,"roll_100lf":None}},
    "Huper Bronze 40":    {36:{"btf_base":6.65,"btf_fee":0.505,"roll_100lf":None},  48:{"btf_base":8.66,"btf_fee":0.505,"roll_100lf":None},  60:{"btf_base":9.74,"btf_fee":0.505,"roll_100lf":None},  72:{"btf_base":11.29,"btf_fee":0.505,"roll_100lf":None}},
    "Huper Silver 18":    {36:{"btf_base":5.21,"btf_fee":0.505,"roll_100lf":None},  48:{"btf_base":6.75,"btf_fee":0.505,"roll_100lf":None},  60:{"btf_base":7.36,"btf_fee":0.505,"roll_100lf":None},  72:{"btf_base":8.43,"btf_fee":0.505,"roll_100lf":None}},
    "Huper Silver 30":    {36:{"btf_base":5.21,"btf_fee":0.505,"roll_100lf":None},  48:{"btf_base":6.75,"btf_fee":0.505,"roll_100lf":None},  60:{"btf_base":7.36,"btf_fee":0.505,"roll_100lf":None},  72:{"btf_base":8.43,"btf_fee":0.505,"roll_100lf":None}},
    "Huper ClearShield 4mil":       {60:{"btf_base":9.52,"btf_fee":0.505,"roll_100lf":None},  72:{"btf_base":10.82,"btf_fee":0.505,"roll_100lf":None}},
    "Huper ClearShield 8mil":       {60:{"btf_base":12.84,"btf_fee":0.505,"roll_100lf":None}, 72:{"btf_base":14.81,"btf_fee":0.505,"roll_100lf":None}},
    "Huper ClearShield 14mil":      {60:{"btf_base":17.37,"btf_fee":0.505,"roll_100lf":None}, 72:{"btf_base":20.24,"btf_fee":0.505,"roll_100lf":None}},
    "Huper Shield 35 Neutral 8mil": {60:{"btf_base":16.51,"btf_fee":0.505,"roll_100lf":None}, 72:{"btf_base":19.21,"btf_fee":0.505,"roll_100lf":None}},

    # ── ASWF (no tariff) ─────────────────────────────────────────────────────
    "Twilight 35": {48:{"btf_base":8.00,"btf_fee":0.00,"roll_100lf":None}, 60:{"btf_base":10.00,"btf_fee":0.00,"roll_100lf":None}},
    "Twilight 20": {48:{"btf_base":8.00,"btf_fee":0.00,"roll_100lf":None}, 60:{"btf_base":10.00,"btf_fee":0.00,"roll_100lf":None}},
    "Twilight 10": {48:{"btf_base":8.00,"btf_fee":0.00,"roll_100lf":None}, 60:{"btf_base":10.00,"btf_fee":0.00,"roll_100lf":None}},
}

# Films that carry the 3% tariff surcharge
TARIFF_BRANDS = {"edge", "ultraview", "guardian", "huper", "clear defense"}
TARIFF_RATE   = 0.03

DEFAULT_FILM_RATES = {
    48: {"btf_base": 5.87, "btf_fee": 0.505, "roll_100lf": None},
    60: {"btf_base": 6.88, "btf_fee": 0.505, "roll_100lf": None},
    72: {"btf_base": 7.50, "btf_fee": 0.505, "roll_100lf": None},
}

# =============================================================================
# CREW CONFIGURATION
# =============================================================================

CREW_CONFIG = {
    "owner_solo": {
        "label":          "Owner Solo",
        "hourly_rate":    80.00,
        "daily_cost":     640.00,   # $80/hr × 8 hrs
        "sqft_per_day":   250,
        "base_floor":     550.00,
        "helper_daily":   0.00,
    },
    "owner_helper": {
        "label":          "Owner + Helper",
        "hourly_rate":    110.00,
        "daily_cost":     880.00,   # $110/hr × 8 hrs
        "sqft_per_day":   400,
        "base_floor":     700.00,
        "helper_daily":   240.00,   # helper guaranteed full day
    },
    "helper_only": {
        "label":          "Helper Only",
        "hourly_rate":    30.00,
        "daily_cost":     240.00,   # $30/hr × 8 hrs
        "sqft_per_day":   200,
        "base_floor":     550.00,
        "helper_daily":   0.00,
    },
    "sub": {
        "label":          "Sub-Contractor",
        "hourly_rate":    0.00,     # rate table based
        "daily_cost":     0.00,     # calculated from sqft × sub rate
        "sqft_per_day":   400,
        "base_floor":     500.00,
        "helper_daily":   0.00,
    },
}

# Floor auto-elevation triggers (stacked, capped at $800)
FLOOR_BUMPS = {
    "high_work":  150.00,
    "removal":    100.00,
    "exterior":   100.00,
}
FLOOR_CAP = 800.00

# =============================================================================
# SUB-CONTRACTOR RATE TABLE
# =============================================================================

SUB_RATES = {
    "solar":      {"standard": 3.00, "high_work": 3.25},
    "exterior":   {"standard": 3.00, "high_work": 3.25},
    "decorative": {"standard": 3.00, "high_work": 3.00},
    "security": {
        "standard": {4: 3.00, 8: 3.00, 11: 3.25, 15: 3.50, 23: 4.00},
        "high_work": {4: 3.25, 8: 3.25, 11: 3.50, 15: 3.75, 23: 4.25},
    },
}

FILM_SUB_CATEGORY = {
    "ultraview": "solar", "twilight": "solar", "coal alloy": "solar",
    "silver": "solar", "bronze": "solar", "pristine": "solar",
    "reform": "solar", "huper": "solar",
    "frost": "decorative", "blackout": "decorative", "whiteout": "decorative",
    "guardian": "security", "clearshield": "security", "clear defense": "security",
}

SECURITY_MIL = {
    "guardian 4mil": 4,  "guardian 8mil": 8,  "guardian 12mil": 12,
    "clearshield 4mil": 4, "clearshield 8mil": 8, "clearshield 14mil": 14,
    "clear defense 4mil": 4, "clear defense 6mil": 6,
}

REMOVAL_RATE_PER_SQFT  = 1.50
REMOVAL_PRODUCTION_PENALTY = 0.30   # 30% slower
MAX_BTF_LF             = 70         # max linear feet orderable by-the-foot
FULL_ROLL_SWITCH_DELTA = 30.00      # if full roll costs < $30 more than 70 BTF, take the roll

# kept for backward compat
SOLO_INSTALLER_SQFT_PER_DAY = 250


# =============================================================================
# FILM UTILITIES
# =============================================================================

def film_has_tariff(film_name: str) -> bool:
    lower = film_name.lower()
    return any(brand in lower for brand in TARIFF_BRANDS)


def get_film_rates(film_name: str, roll_width: int) -> Dict[str, float]:
    rates = FILM_RATES.get(film_name, {})
    if roll_width in rates:
        return rates[roll_width]
    film_lower = film_name.lower()
    for key, widths in FILM_RATES.items():
        if key.lower() in film_lower or film_lower in key.lower():
            if roll_width in widths:
                return widths[roll_width]
    return DEFAULT_FILM_RATES.get(roll_width, DEFAULT_FILM_RATES[48])


def get_price_floor_per_sqft(film_name: str) -> float:
    FLOORS = {
        "UltraView": 7.50, "Twilight": 10.00, "Aurora": 12.00,
        "Huper": 12.00, "Edge Pristine": 12.00,
        "Safety": 8.00, "Guardian": 8.00, "Decorative": 6.00, "default": 7.50,
    }
    for family, floor in FLOORS.items():
        if family.lower() in film_name.lower():
            return floor
    return FLOORS["default"]


# =============================================================================
# MATERIAL COST — SMART ORDER SPLITTING
# =============================================================================

def calculate_material_cost(
    film_name: str,
    roll_width: int,
    required_lf: float,
    buffer_lf: float,
) -> Dict[str, Any]:
    """
    Calculate material cost with smart order splitting:
    - Max BTF order: 70 LF
    - If needed LF > 70: use full 100 LF roll + BTF remainder
    - If full roll vs 70 BTF difference < $30: recommend full roll
    - Tariff: 3% on Edge and Huper Optik
    """
    rates     = get_film_rates(film_name, roll_width)
    btf_rate  = rates["btf_base"] + rates["btf_fee"]
    needed_lf = math.ceil(required_lf + buffer_lf)

    order_lines   = []   # list of dicts describing each order line
    total_mat     = 0.0
    order_method  = "by_the_foot"
    order_lf_total = needed_lf

    roll_price = rates.get("roll_100lf")

    if needed_lf <= MAX_BTF_LF:
        # Simple BTF order
        btf_cost = round(needed_lf * btf_rate, 2)

        # Check if full roll is available and worth it
        if roll_price and roll_price < btf_cost + FULL_ROLL_SWITCH_DELTA:
            # Full roll is cheaper or within $30 — recommend it
            order_lines.append({
                "type": "full_roll", "lf": 100, "cost": roll_price,
                "note": f"Full 100 LF roll (saves ${round(btf_cost - roll_price, 2):.2f} vs BTF)" if roll_price < btf_cost else f"Full 100 LF roll (only ${round(roll_price - btf_cost, 2):.2f} more — get 30+ extra feet)"
            })
            total_mat    = roll_price
            order_method = "full_roll"
            order_lf_total = 100
        else:
            order_lines.append({
                "type": "btf", "lf": needed_lf, "cost": btf_cost,
                "note": f"{needed_lf} LF by the foot"
            })
            total_mat    = btf_cost
            order_method = "by_the_foot"

    else:
        # Need more than 70 LF — must split
        if roll_price:
            # Full roll covers first 100 LF
            order_lines.append({
                "type": "full_roll", "lf": 100, "cost": roll_price,
                "note": "Full 100 LF roll"
            })
            remainder_lf = needed_lf - 100

            if remainder_lf > 0:
                # Clamp remainder to MAX_BTF_LF
                remainder_lf = min(remainder_lf, MAX_BTF_LF)
                remainder_cost = round(remainder_lf * btf_rate, 2)
                order_lines.append({
                    "type": "btf", "lf": remainder_lf, "cost": remainder_cost,
                    "note": f"{remainder_lf} LF by the foot (remainder)"
                })
                total_mat = roll_price + remainder_cost
            else:
                total_mat = roll_price

            order_method   = "split"
            order_lf_total = sum(line["lf"] for line in order_lines)
        else:
            # No full roll available — cap at MAX_BTF_LF and warn
            capped_lf   = min(needed_lf, MAX_BTF_LF)
            btf_cost    = round(capped_lf * btf_rate, 2)
            order_lines.append({
                "type": "btf", "lf": capped_lf, "cost": btf_cost,
                "note": f"{capped_lf} LF by the foot (capped — no full roll available)"
            })
            total_mat      = btf_cost
            order_method   = "by_the_foot_capped"
            order_lf_total = capped_lf

    # Tariff
    tariff = round(total_mat * TARIFF_RATE, 2) if film_has_tariff(film_name) else 0.0

    return {
        "order_lf":       order_lf_total,
        "order_lines":    order_lines,
        "mat_subtotal":   round(total_mat, 2),
        "tariff":         tariff,
        "recommended_cost": round(total_mat + tariff, 2),
        "order_method":   order_method,
        "rates":          rates,
        # Legacy keys for compatibility
        "btf_cost":       round(needed_lf * btf_rate, 2),
        "full_roll_cost": roll_price,
        "full_roll_savings": round(needed_lf * btf_rate - roll_price, 2) if roll_price else None,
    }


# =============================================================================
# PROFIT FLOOR ENGINE
# =============================================================================

def calculate_profit_floor(
    crew_type:    str,
    is_high_work: bool = False,
    has_removal:  bool = False,
    is_exterior:  bool = False,
) -> Dict[str, Any]:
    """
    Returns the auto-calculated profit floor and a human-readable reason label.
    Floor = base + bumps, capped at FLOOR_CAP.
    """
    base   = CREW_CONFIG[crew_type]["base_floor"]
    bumps  = 0.0
    reasons = []

    if is_high_work:
        bumps += FLOOR_BUMPS["high_work"]
        reasons.append(f"High Work +${FLOOR_BUMPS['high_work']:.0f}")
    if has_removal:
        bumps += FLOOR_BUMPS["removal"]
        reasons.append(f"Removal +${FLOOR_BUMPS['removal']:.0f}")
    if is_exterior:
        bumps += FLOOR_BUMPS["exterior"]
        reasons.append(f"Exterior +${FLOOR_BUMPS['exterior']:.0f}")

    calculated = min(base + bumps, FLOOR_CAP)
    label = f"${base:.0f} base"
    if reasons:
        label += " + " + ", ".join(reasons)
    if base + bumps > FLOOR_CAP:
        label += f" (capped at ${FLOOR_CAP:.0f})"

    return {
        "calculated": calculated,
        "base":       base,
        "bumps":      bumps,
        "label":      label,
    }


# =============================================================================
# LABOR COST ENGINE
# =============================================================================

def calculate_labor_cost(
    sqft:         float,
    crew_type:    str,
    has_removal:  bool = False,
    removal_sqft: float = 0.0,
) -> Dict[str, Any]:
    """
    Calculates real internal labor cost.
    - Applies 30% production penalty to removal work
    - Owner/helper: daily rate × days
    - Sub: calculated separately via calculate_sub_labor()
    """
    cfg = CREW_CONFIG[crew_type]

    if crew_type == "sub":
        # Sub labor is calculated per-section with rate table
        return {"cost": 0.0, "days": 0, "hours": 0, "rate_used": 0, "note": "Sub — see section rates"}

    base_rate = cfg["sqft_per_day"]

    # If removal is involved, calculate those sqft at reduced production
    install_days  = 0.0
    removal_days  = 0.0

    if has_removal and removal_sqft > 0:
        removal_rate  = base_rate * (1 - REMOVAL_PRODUCTION_PENALTY)
        removal_days  = removal_sqft / removal_rate
        install_sqft  = sqft - removal_sqft
        install_days  = install_sqft / base_rate if install_sqft > 0 else 0
    else:
        install_days = sqft / base_rate

    total_days  = math.ceil(install_days + removal_days)
    total_hours = total_days * 8
    daily_cost  = cfg["daily_cost"]
    total_cost  = round(total_days * daily_cost, 2)

    note = f"{total_days} day(s) × ${daily_cost:.2f}/day ({cfg['label']})"
    if has_removal:
        note += f" — removal at 70% production"

    return {
        "cost":      total_cost,
        "days":      total_days,
        "hours":     total_hours,
        "daily_cost": daily_cost,
        "rate_used": cfg["hourly_rate"],
        "note":      note,
    }


def get_sub_labor_rate(film_name: str, is_high_work: bool, is_exterior: bool = False) -> float:
    cat = "exterior" if is_exterior else next(
        (v for k, v in FILM_SUB_CATEGORY.items() if k in film_name.lower()), "solar"
    )
    if cat == "security":
        film_lower = film_name.lower()
        mil = next((m for k, m in SECURITY_MIL.items() if k in film_lower), 4)
        tier = SUB_RATES["security"]["high_work" if is_high_work else "standard"]
        return next(tier[t] for t in sorted(tier.keys(), reverse=True) if mil >= t)
    rates = SUB_RATES.get(cat, SUB_RATES["solar"])
    return rates["high_work"] if is_high_work else rates["standard"]


def calculate_sub_labor(
    sqft: float, film_name: str, is_high_work: bool, is_exterior: bool = False
) -> Dict[str, float]:
    rate = get_sub_labor_rate(film_name, is_high_work, is_exterior)
    return {"cost": round(sqft * rate, 2), "rate": rate}


# =============================================================================
# QUOTE BUILDER
# =============================================================================

def build_quote(
    material_cost:  float,
    tariff:         float,
    labor_cost:     float,
    removal_cost:   float,
    total_sqft:     float,
    crew_type:      str,
    active_floor:   float,
    days:           int,
) -> Dict[str, Any]:
    """
    Walk-Away = all costs + (days × active PM floor)
    Recommended = highest of Rule A (×1.30), Rule B ($1,200), Rule C ($7.50/sqft)
    """
    total_cost = round(material_cost + tariff + labor_cost + removal_cost, 2)
    walk_away  = round(total_cost + (days * active_floor), 2)

    rule_a = round(walk_away * 1.30, 2)
    rule_b = 0.0 if total_sqft < 150 else 1200.0
    rule_c = round(total_sqft * 7.50, 2)

    recommended = max(rule_a, rule_b, rule_c)

    if recommended == rule_c:      winning_rule, winning_label = "sqft_floor",    "$7.50/sqft Floor"
    elif recommended == rule_b:    winning_rule, winning_label = "min_ticket",    "$1,200 Minimum Ticket"
    else:                          winning_rule, winning_label = "margin_buffer", "30% Negotiation Buffer"

    gross_profit  = round(recommended - total_cost, 2)
    profit_per_day = round(gross_profit / days, 2) if days > 0 else 0.0
    margin_pct    = round((gross_profit / recommended) * 100, 1) if recommended > 0 else 0.0
    daily_revenue_needed = round(total_cost / days + active_floor, 2) if days > 0 else 0.0

    return {
        "walk_away":            walk_away,
        "recommended":          recommended,
        "winning_rule":         winning_rule,
        "winning_label":        winning_label,
        "rule_a":               rule_a,
        "rule_b":               rule_b,
        "rule_c":               rule_c,
        "gross_profit":         gross_profit,
        "profit_per_day":       profit_per_day,
        "margin_pct":           margin_pct,
        "active_floor":         active_floor,
        "daily_revenue_needed": daily_revenue_needed,
        "total_cost":           total_cost,
        "material_cost":        material_cost,
        "tariff":               tariff,
        "labor_cost":           labor_cost,
        "removal_cost":         removal_cost,
        "days":                 days,
    }


def check_override(override_price: float, quote: Dict[str, Any]) -> Dict[str, Any]:
    total_cost = quote["total_cost"]
    days       = quote["days"]
    gp   = round(override_price - total_cost, 2)
    ppd  = round(gp / days, 2) if days > 0 else 0.0
    marg = round((gp / override_price) * 100, 1) if override_price > 0 else 0.0
    is_loss   = override_price < quote["walk_away"]
    is_caution = not is_loss and override_price < quote["recommended"]
    return {"price": override_price, "gp": gp, "ppd": ppd, "marg": marg,
            "is_loss": is_loss, "is_caution": is_caution}


# =============================================================================
# OPTIMIZATION ENGINE (unchanged)
# =============================================================================

def _orientation_options(pane, roll_width):
    w, h = int(pane["width"]), int(pane["height"])
    opts = []
    if w <= roll_width: opts.append({"width": w, "height": h})
    if h <= roll_width and h != w: opts.append({"width": h, "height": w})
    return opts

def _pane_sort_key(pane, roll_width):
    w, h = int(pane["width"]), int(pane["height"])
    return (max(w,h), min(w,h), w*h)

def _best_fit_existing(pane, row, roll_width):
    rem = roll_width - row["used_width"]
    best, best_score = None, None
    for opt in _orientation_options(pane, roll_width):
        if opt["width"] > rem: continue
        added = max(row["pull_to"], opt["height"]) - row["pull_to"]
        score = (added, -(row["used_width"] + opt["width"]))
        if best_score is None or score < best_score:
            best_score, best = score, opt
    return best

def _best_fit_new(pane, roll_width):
    best, best_score = None, None
    for opt in _orientation_options(pane, roll_width):
        score = (opt["height"], -opt["width"])
        if best_score is None or score < best_score:
            best_score, best = score, opt
    return best

def optimize_for_roll_width(panes: List[Dict], roll_width: int) -> Dict[str, Any]:
    if roll_width <= 0: raise ValueError("roll_width must be positive")
    if not panes: return {"total_lf": 0.0, "rows": []}

    sorted_panes = sorted(
        [{"width": int(p["width"]), "height": int(p["height"])} for p in panes],
        key=lambda p: _pane_sort_key(p, roll_width), reverse=True,
    )
    rows = []
    for pane in sorted_panes:
        placed = False
        for row in rows:
            opt = _best_fit_existing(pane, row, roll_width)
            if opt:
                row["panes"].append(opt)
                row["used_width"] += opt["width"]
                row["pull_to"] = max(row["pull_to"], opt["height"])
                row["lanes"] = len(row["panes"])
                placed = True; break
        if not placed:
            opt = _best_fit_new(pane, roll_width)
            if opt is None:
                raise ValueError(f"Pane {pane} cannot fit on roll width {roll_width}")
            rows.append({"panes":[opt], "used_width":opt["width"], "pull_to":opt["height"], "lanes":1})

    total_inches = sum(r["pull_to"] for r in rows)
    return {"total_lf": round(total_inches/12.0, 2), "rows": rows}


def group_windows_by_section(windows: List[Dict]) -> Dict[str, List[Dict]]:
    groups: Dict[str, List[Dict]] = {}
    for w in windows:
        sec = w.get("section", "Unassigned")
        if sec not in groups: groups[sec] = []
        groups[sec].append(w)
    return groups


# High-work keyword detection
HIGH_WORK_KEYWORDS = [
    "lift","ladder","scaffold","aff","above finished","high work",
    "exterior","12 ft","12ft","elevated","boom","scissor","manlift"
]

def detect_high_work(notes: str) -> bool:
    if not notes: return False
    lower = notes.lower()
    return any(kw in lower for kw in HIGH_WORK_KEYWORDS)


# =============================================================================
# CREW OPTIMIZER
# Runs all four crew types against the same job and scores each option.
# =============================================================================

def run_crew_optimizer(
    total_sqft:     float,
    total_mat_cost: float,
    total_tariff:   float,
    removal_cost:   float,
    primary_film:   str,
    any_high_work:  bool,
    any_removal:    bool,
    any_exterior:   bool,
    floor_override: float = None,
    active_crew:    str   = None,
    active_days:    int   = None,
    active_labor:   float = None,
    active_quote:   Dict  = None,
) -> List[Dict[str, Any]]:
    """
    Runs Walk-Away + Recommended Price for all four crew types.
    For the currently active crew, uses the pre-calculated numbers from the
    main Quote Builder so both panels always show identical numbers.
    For other crews, calculates independently.
    """
    results = []

    for crew_key, cfg in CREW_CONFIG.items():

        floor_info = calculate_profit_floor(crew_key, any_high_work, any_removal, any_exterior)
        floor      = floor_override if floor_override is not None else floor_info["calculated"]

        # If this is the currently selected crew, use the already-calculated
        # numbers exactly — no independent recalculation
        if crew_key == active_crew and active_quote is not None:
            days       = active_days
            labor_cost = active_labor
            q          = active_quote
        else:
            # Labor cost — all crew types use single-pass days (total sqft ÷ rate)
            # This matches real scheduling: one crew, one visit, full job
            days = math.ceil(total_sqft / cfg["sqft_per_day"]) if total_sqft > 0 else 1

            if crew_key == "sub":
                sub_rate   = 3.25 if any_high_work else 3.00
                labor_cost = round(total_sqft * sub_rate, 2)
            else:
                # Daily cost × days (single pass)
                labor_cost = round(days * cfg["daily_cost"], 2)

            # Quote
            q = build_quote(
                material_cost = total_mat_cost,
                tariff        = total_tariff,
                labor_cost    = labor_cost,
                removal_cost  = removal_cost,
                total_sqft    = total_sqft,
                crew_type     = crew_key,
                active_floor  = floor,
                days          = days,
            )

        # Scoring logic
        score        = 0
        fit_notes    = []
        risk_notes   = []

        # Job size fit
        if total_sqft <= 250:
            if crew_key == "owner_solo":
                score += 3
                fit_notes.append("ideal size for solo")
            elif crew_key in ["owner_helper", "sub"]:
                score += 1
                fit_notes.append("crew is optional at this size")
        elif total_sqft <= 500:
            if crew_key == "owner_helper":
                score += 3
                fit_notes.append("efficient 1-day crew job")
            elif crew_key == "sub":
                score += 2
                fit_notes.append("sub frees your schedule")
            elif crew_key == "owner_solo":
                score += 1
                fit_notes.append("doable solo but takes 2 days")
        else:
            if crew_key in ["owner_helper", "sub"]:
                score += 3
                fit_notes.append("large job — crew efficiency needed")
            elif crew_key == "owner_solo":
                score += 0
                risk_notes.append("large job solo takes 3+ days")
            elif crew_key == "helper_only":
                score += 0
                risk_notes.append("helper-only slow on large jobs")

        # High work risk
        if any_high_work:
            if crew_key == "owner_solo":
                score -= 1
                risk_notes.append("lift work solo is a safety risk")
            elif crew_key == "helper_only":
                score -= 2
                risk_notes.append("helper alone should not do lift work")
            elif crew_key in ["owner_helper", "sub"]:
                score += 1
                fit_notes.append("two-person crew safer on lifts")

        # Profit per day bonus
        ppd = q["profit_per_day"]
        if ppd >= 1200:   score += 2
        elif ppd >= 800:  score += 1

        # Sub frees your time — bonus for large or complex jobs
        if crew_key == "sub" and (total_sqft > 400 or any_high_work):
            score += 1
            fit_notes.append("sub lets you manage instead of install")

        results.append({
            "crew_key":    crew_key,
            "label":       cfg["label"],
            "days":        days,
            "labor_cost":  labor_cost,
            "walk_away":   q["walk_away"],
            "recommended": q["recommended"],
            "profit_per_day": ppd,
            "gross_profit":   q["gross_profit"],
            "margin_pct":     q["margin_pct"],
            "floor":          floor,
            "score":          score,
            "fit_notes":      fit_notes,
            "risk_notes":     risk_notes,
            "total_cost":     q["total_cost"],
        })

    # Sort: highest score first, then highest profit/day as tiebreaker
    results.sort(key=lambda x: (x["score"], x["profit_per_day"]), reverse=True)

    # Tag winner
    results[0]["is_recommended"] = True
    for r in results[1:]:
        r["is_recommended"] = False

    return results
