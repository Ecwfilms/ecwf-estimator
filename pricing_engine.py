# pricing_engine.py
# East Coast Window Films — Pricing Engine v4.4
# Handles roll optimization, material cost, labor complexity scoring, and Go/No-Go logic.
#
# PRICING MODEL (Edge Dealer Store):
#   - "By the foot" orders: base_rate_per_lf + processing_fee_per_lf
#   - Full 100 LF roll orders: full_roll_price (flat, no processing fee)
#   - Safety & Security films: full-roll-only (50 LF or 100 LF increments)
#
# LABOR MODEL:
#   - Base rates: Solar/Decorative $3.00/sqft, Safety $3.50/sqft
#   - Complexity adders applied per line item (not per whole job)
#   - Caulking is a separate line item at $3.00/LF
#
# GO/NO-GO ENGINE:
#   - Minimum acceptable gross margin: 40% (configurable)
#   - Green: margin >= target, Yellow: within 5% below target, Red: below threshold

from typing import Any, Dict, List, Optional, Tuple

# =============================================================================
# FILM RATE DATABASE
# =============================================================================

FILM_RATES: Dict[str, Dict[int, Dict[str, float]]] = {
    "UltraView 5": {
        48: {"btf_base": 3.37, "btf_fee": 0.505, "roll_100lf": 97.69},
        60: {"btf_base": 6.08, "btf_fee": 0.505, "roll_100lf": 458.42},
        72: {"btf_base": 6.80, "btf_fee": 0.505, "roll_100lf": 550.11},
    },
    "UltraView 15": {
        48: {"btf_base": 3.37, "btf_fee": 0.505, "roll_100lf": 97.69},
        60: {"btf_base": 6.08, "btf_fee": 0.505, "roll_100lf": 458.42},
        72: {"btf_base": 6.80, "btf_fee": 0.505, "roll_100lf": 550.11},
    },
    "UltraView 20": {
        48: {"btf_base": 3.37, "btf_fee": 0.505, "roll_100lf": 97.69},
        60: {"btf_base": 6.08, "btf_fee": 0.505, "roll_100lf": 458.42},
        72: {"btf_base": 6.80, "btf_fee": 0.505, "roll_100lf": 550.11},
    },
    "UltraView 25": {
        48: {"btf_base": 3.37, "btf_fee": 0.505, "roll_100lf": 97.69},
        60: {"btf_base": 6.08, "btf_fee": 0.505, "roll_100lf": 458.42},
        72: {"btf_base": 6.80, "btf_fee": 0.505, "roll_100lf": 550.11},
    },
    "UltraView 35": {
        48: {"btf_base": 3.37, "btf_fee": 0.505, "roll_100lf": 97.69},
        60: {"btf_base": 6.08, "btf_fee": 0.505, "roll_100lf": 458.42},
        72: {"btf_base": 6.80, "btf_fee": 0.505, "roll_100lf": 550.11},
    },
    "Nature 10": {
        48: {"btf_base": 6.90, "btf_fee": 0.505, "roll_100lf": 638.35},
        60: {"btf_base": 7.65, "btf_fee": 0.505, "roll_100lf": 718.35},
        72: {"btf_base": 8.65, "btf_fee": 0.505, "roll_100lf": 818.35},
    },
    "Nature 20": {
        48: {"btf_base": 6.90, "btf_fee": 0.505, "roll_100lf": 638.35},
        60: {"btf_base": 7.65, "btf_fee": 0.505, "roll_100lf": 718.35},
        72: {"btf_base": 8.65, "btf_fee": 0.505, "roll_100lf": 818.35},
    },
    "Nature 30": {
        48: {"btf_base": 6.90, "btf_fee": 0.505, "roll_100lf": 638.35},
        60: {"btf_base": 7.65, "btf_fee": 0.505, "roll_100lf": 718.35},
        72: {"btf_base": 8.65, "btf_fee": 0.505, "roll_100lf": 818.35},
    },
    "Cool Alloy 20": {
        48: {"btf_base": 5.07, "btf_fee": 0.505, "roll_100lf": 501.23},
        60: {"btf_base": 5.78, "btf_fee": 0.505, "roll_100lf": 559.76},
        72: {"btf_base": 7.09, "btf_fee": 0.505, "roll_100lf": 627.95},
    },
    "Cool Alloy 35": {
        48: {"btf_base": 5.07, "btf_fee": 0.505, "roll_100lf": 501.23},
        60: {"btf_base": 5.78, "btf_fee": 0.505, "roll_100lf": 559.76},
        72: {"btf_base": 7.09, "btf_fee": 0.505, "roll_100lf": 627.95},
    },
    "Cool Alloy 60": {
        48: {"btf_base": 5.07, "btf_fee": 0.505, "roll_100lf": 501.23},
        60: {"btf_base": 5.78, "btf_fee": 0.505, "roll_100lf": 559.76},
        72: {"btf_base": 7.09, "btf_fee": 0.505, "roll_100lf": 627.95},
    },
    "Edge Coal Alloy": {
        48: {"btf_base": 5.07, "btf_fee": 0.505, "roll_100lf": 501.23},
        60: {"btf_base": 5.78, "btf_fee": 0.505, "roll_100lf": 559.76},
        72: {"btf_base": 7.09, "btf_fee": 0.505, "roll_100lf": 627.95},
    },
    "Silver 20": {
        48: {"btf_base": 3.66, "btf_fee": 0.505, "roll_100lf": 380.86},
        60: {"btf_base": 4.91, "btf_fee": 0.505, "roll_100lf": 460.86},
        72: {"btf_base": 6.19, "btf_fee": 0.505, "roll_100lf": 540.86},
    },
    "Silver 30": {
        48: {"btf_base": 3.66, "btf_fee": 0.505, "roll_100lf": 380.86},
        60: {"btf_base": 4.91, "btf_fee": 0.505, "roll_100lf": 460.86},
        72: {"btf_base": 6.19, "btf_fee": 0.505, "roll_100lf": 540.86},
    },
    "Silver 40": {
        48: {"btf_base": 3.66, "btf_fee": 0.505, "roll_100lf": 380.86},
        60: {"btf_base": 4.91, "btf_fee": 0.505, "roll_100lf": 460.86},
        72: {"btf_base": 6.19, "btf_fee": 0.505, "roll_100lf": 540.86},
    },
    "Edge Silver": {
        48: {"btf_base": 3.66, "btf_fee": 0.505, "roll_100lf": 380.86},
        60: {"btf_base": 4.91, "btf_fee": 0.505, "roll_100lf": 460.86},
        72: {"btf_base": 6.19, "btf_fee": 0.505, "roll_100lf": 540.86},
    },
    "Bronze 20": {
        48: {"btf_base": 5.81, "btf_fee": 0.505, "roll_100lf": 563.03},
        60: {"btf_base": 7.62, "btf_fee": 0.505, "roll_100lf": 635.91},
        72: {"btf_base": 9.63, "btf_fee": 0.505, "roll_100lf": 762.86},
    },
    "Bronze 35": {
        48: {"btf_base": 5.81, "btf_fee": 0.505, "roll_100lf": 563.03},
        60: {"btf_base": 7.62, "btf_fee": 0.505, "roll_100lf": 635.91},
        72: {"btf_base": 9.63, "btf_fee": 0.505, "roll_100lf": 762.86},
    },
    "Edge Bronze": {
        48: {"btf_base": 5.81, "btf_fee": 0.505, "roll_100lf": 563.03},
        60: {"btf_base": 7.62, "btf_fee": 0.505, "roll_100lf": 635.91},
        72: {"btf_base": 9.63, "btf_fee": 0.505, "roll_100lf": 762.86},
    },
    "Edge Pristine 30": {
        48: {"btf_base": 12.18, "btf_fee": 0.505, "roll_100lf": 1169.55},
        60: {"btf_base": 14.71, "btf_fee": 0.505, "roll_100lf": 1403.46},
        72: {"btf_base": 16.03, "btf_fee": 0.505, "roll_100lf": 1637.37},
    },
    "Edge Pristine 40": {
        48: {"btf_base": 12.18, "btf_fee": 0.505, "roll_100lf": 1169.55},
        60: {"btf_base": 14.71, "btf_fee": 0.505, "roll_100lf": 1403.46},
        72: {"btf_base": 16.03, "btf_fee": 0.505, "roll_100lf": 1637.37},
    },
    "Edge Pristine 50": {
        48: {"btf_base": 12.18, "btf_fee": 0.505, "roll_100lf": 1169.55},
        60: {"btf_base": 14.71, "btf_fee": 0.505, "roll_100lf": 1403.46},
        72: {"btf_base": 16.03, "btf_fee": 0.505, "roll_100lf": 1637.37},
    },
    "Edge Pristine 70": {
        48: {"btf_base": 12.18, "btf_fee": 0.505, "roll_100lf": 1169.55},
        60: {"btf_base": 14.71, "btf_fee": 0.505, "roll_100lf": 1403.46},
        72: {"btf_base": 16.03, "btf_fee": 0.505, "roll_100lf": 1637.37},
    },
    "Edge Pristine 80": {
        48: {"btf_base": 12.18, "btf_fee": 0.505, "roll_100lf": 1169.55},
        60: {"btf_base": 14.71, "btf_fee": 0.505, "roll_100lf": 1403.46},
        72: {"btf_base": 16.03, "btf_fee": 0.505, "roll_100lf": 1637.37},
    },
    "Guardian 4mil": {
        48: {"btf_base": 0.59, "btf_fee": 0.505, "roll_100lf": 96.53},
        60: {"btf_base": 0.91, "btf_fee": 0.505, "roll_100lf": 120.86},
        72: {"btf_base": 1.25, "btf_fee": 0.505, "roll_100lf": 145.19},
    },
    "Guardian 8mil": {
        48: {"btf_base": 1.25, "btf_fee": 0.505, "roll_100lf": 145.36},
        60: {"btf_base": 1.69, "btf_fee": 0.505, "roll_100lf": 181.70},
        72: {"btf_base": 1.69, "btf_fee": 0.505, "roll_100lf": 218.04},
    },
    "Guardian 8mil Silver 20": {
        48: {"btf_base": 2.76, "btf_fee": 0.505, "roll_100lf": 272.44},
        60: {"btf_base": 3.57, "btf_fee": 0.505, "roll_100lf": 340.55},
        72: {"btf_base": 4.38, "btf_fee": 0.505, "roll_100lf": 408.66},
    },
    "Guardian 12mil": {
        48: {"btf_base": 1.69, "btf_fee": 0.505, "roll_100lf": 181.70},
        60: {"btf_base": 1.69, "btf_fee": 0.505, "roll_100lf": 218.04},
        72: {"btf_base": 1.69, "btf_fee": 0.505, "roll_100lf": 254.38},
    },
    "CS 4mil": {
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 651.98},
        72: {"btf_base": 9.52, "btf_fee": 0.0, "roll_100lf": 782.36},
    },
    "CS 8mil": {
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 983.79},
        72: {"btf_base": 12.84, "btf_fee": 0.0, "roll_100lf": 1180.54},
    },
    "CS 14mil": {
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 1416.67},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 1724.24},
    },
    "Shield 35 Neutral 8mil": {
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 1312.95},
        72: {"btf_base": 16.51, "btf_fee": 0.0, "roll_100lf": 1620.61},
    },
    "Frost": {
        48: {"btf_base": 4.64, "btf_fee": 0.505, "roll_100lf": 439.00},
        60: {"btf_base": 5.51, "btf_fee": 0.505, "roll_100lf": 550.11},
        72: {"btf_base": 6.38, "btf_fee": 0.505, "roll_100lf": 327.77},
    },
    "Blackout": {
        48: {"btf_base": 4.16, "btf_fee": 0.505, "roll_100lf": 451.12},
        60: {"btf_base": 5.51, "btf_fee": 0.505, "roll_100lf": 451.12},
        72: {"btf_base": 1.05, "btf_fee": 0.505, "roll_100lf": 451.12},
    },
    "Whiteout": {
        48: {"btf_base": 6.58, "btf_fee": 0.505, "roll_100lf": 458.40},
        60: {"btf_base": 7.03, "btf_fee": 0.505, "roll_100lf": 550.11},
    },
    "Clear Defense 4mil": {
        48: {"btf_base": 0.72, "btf_fee": 0.505, "roll_100lf": 101.21},
        60: {"btf_base": 1.03, "btf_fee": 0.505, "roll_100lf": 126.51},
        72: {"btf_base": 1.03, "btf_fee": 0.505, "roll_100lf": 151.81},
    },
    "Clear Defense 6mil": {
        48: {"btf_base": 0.83, "btf_fee": 0.505, "roll_100lf": 110.97},
        60: {"btf_base": 1.17, "btf_fee": 0.505, "roll_100lf": 138.71},
        72: {"btf_base": 1.17, "btf_fee": 0.505, "roll_100lf": 166.45},
    },
    "Huper Select Drei": {
        40: {"btf_base": 22.47, "btf_fee": 0.505, "roll_100lf": 2971.12},
        60: {"btf_base": 31.21, "btf_fee": 0.505, "roll_100lf": 3411.21},
        72: {"btf_base": 42.43, "btf_fee": 0.505, "roll_100lf": 4092.45},
    },
    "Huper Select Sech": {
        40: {"btf_base": 18.17, "btf_fee": 0.505, "roll_100lf": 2440.24},
        60: {"btf_base": 29.62, "btf_fee": 0.505, "roll_100lf": 2811.63},
        72: {"btf_base": 35.24, "btf_fee": 0.505, "roll_100lf": 1373.95},
    },
    "Huper Ceramic 20": {
        40: {"btf_base": 11.52, "btf_fee": 0.505, "roll_100lf": 1457.62},
        60: {"btf_base": 16.08, "btf_fee": 0.505, "roll_100lf": 1670.68},
        72: {"btf_base": 18.21, "btf_fee": 0.505, "roll_100lf": 2004.81},
    },
    "Huper Ceramic 30": {
        40: {"btf_base": 11.52, "btf_fee": 0.505, "roll_100lf": 1457.62},
        60: {"btf_base": 16.08, "btf_fee": 0.505, "roll_100lf": 1670.68},
        72: {"btf_base": 18.21, "btf_fee": 0.505, "roll_100lf": 2004.81},
    },
    "Huper Ceramic 40": {
        40: {"btf_base": 11.52, "btf_fee": 0.505, "roll_100lf": 1457.62},
        60: {"btf_base": 16.08, "btf_fee": 0.505, "roll_100lf": 1670.68},
        72: {"btf_base": 18.21, "btf_fee": 0.505, "roll_100lf": 2004.81},
    },
    "Huper Ceramic 50": {
        40: {"btf_base": 8.44, "btf_fee": 0.505, "roll_100lf": 1156.10},
        60: {"btf_base": 13.06, "btf_fee": 0.505, "roll_100lf": 1156.10},
        72: {"btf_base": 13.06, "btf_fee": 0.505, "roll_100lf": 1388.94},
    },
    "Huper Ceramic 60": {
        40: {"btf_base": 8.44, "btf_fee": 0.505, "roll_100lf": 1156.10},
        60: {"btf_base": 13.06, "btf_fee": 0.505, "roll_100lf": 1156.10},
        72: {"btf_base": 13.06, "btf_fee": 0.505, "roll_100lf": 1388.94},
    },
    "Huper Ceramic 70": {
        40: {"btf_base": 23.05, "btf_fee": 0.505, "roll_100lf": 2631.17},
        60: {"btf_base": 28.81, "btf_fee": 0.505, "roll_100lf": 2811.63},
        72: {"btf_base": 29.62, "btf_fee": 0.505, "roll_100lf": None},
    },
    "Huper Ceramic 35": {
        40: {"btf_base": 6.73, "btf_fee": 0.505, "roll_100lf": 869.09},
        60: {"btf_base": 10.19, "btf_fee": 0.505, "roll_100lf": 870.25},
        72: {"btf_base": 10.23, "btf_fee": 0.505, "roll_100lf": 1044.31},
    },
    "Huper Ceramic 45": {
        40: {"btf_base": 6.73, "btf_fee": 0.505, "roll_100lf": 869.09},
        60: {"btf_base": 10.19, "btf_fee": 0.505, "roll_100lf": 870.25},
        72: {"btf_base": 10.23, "btf_fee": 0.505, "roll_100lf": 1044.31},
    },
    "Huper KLAR 85": {
        40: {"btf_base": 16.20, "btf_fee": 0.505, "roll_100lf": 1723.06},
        60: {"btf_base": 18.73, "btf_fee": 0.505, "roll_100lf": 1915.17},
    },
    "Huper Fusion 10": {
        40: {"btf_base": 5.17, "btf_fee": 0.505, "roll_100lf": 611.93},
        60: {"btf_base": 6.78, "btf_fee": 0.505, "roll_100lf": 611.93},
        72: {"btf_base": 7.62, "btf_fee": 0.505, "roll_100lf": 734.31},
    },
    "Huper Fusion 20": {
        40: {"btf_base": 5.17, "btf_fee": 0.505, "roll_100lf": 611.93},
        60: {"btf_base": 6.78, "btf_fee": 0.505, "roll_100lf": 611.93},
        72: {"btf_base": 7.62, "btf_fee": 0.505, "roll_100lf": 734.31},
    },
    "Huper Fusion 28": {
        40: {"btf_base": 5.17, "btf_fee": 0.505, "roll_100lf": 611.93},
        60: {"btf_base": 6.78, "btf_fee": 0.505, "roll_100lf": 611.93},
        72: {"btf_base": 7.62, "btf_fee": 0.505, "roll_100lf": 734.31},
    },
    "Huper Bronze 25": {
        40: {"btf_base": 6.13, "btf_fee": 0.505, "roll_100lf": 665.94},
        60: {"btf_base": 8.16, "btf_fee": 0.505, "roll_100lf": 774.22},
        72: {"btf_base": 9.24, "btf_fee": 0.505, "roll_100lf": 929.06},
    },
    "Huper Bronze 35": {
        40: {"btf_base": 6.13, "btf_fee": 0.505, "roll_100lf": 665.94},
        60: {"btf_base": 8.16, "btf_fee": 0.505, "roll_100lf": 774.22},
        72: {"btf_base": 9.24, "btf_fee": 0.505, "roll_100lf": 929.06},
    },
    "Huper Silver 18": {
        40: {"btf_base": 4.71, "btf_fee": 0.505, "roll_100lf": 475.01},
        60: {"btf_base": 6.25, "btf_fee": 0.505, "roll_100lf": 535.55},
        72: {"btf_base": 8.13, "btf_fee": 0.505, "roll_100lf": 642.66},
    },
    "Huper Silver 30": {
        40: {"btf_base": 4.71, "btf_fee": 0.505, "roll_100lf": 475.01},
        60: {"btf_base": 6.25, "btf_fee": 0.505, "roll_100lf": 535.55},
        72: {"btf_base": 8.13, "btf_fee": 0.505, "roll_100lf": 642.66},
    },
    "Huper ClearShield 4mil": {
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 651.98},
        72: {"btf_base": 9.52, "btf_fee": 0.0, "roll_100lf": 782.36},
    },
    "Huper ClearShield 8mil": {
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 983.79},
        72: {"btf_base": 12.84, "btf_fee": 0.0, "roll_100lf": 1180.54},
    },
    "Huper ClearShield 14mil": {
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 1416.67},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 1724.24},
    },
    "Huper Shield 35 Neutral 8mil": {
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 1312.95},
        72: {"btf_base": 16.51, "btf_fee": 0.0, "roll_100lf": 1620.61},
    },
    "Huper Decorative Frost": {
        40: {"btf_base": 1.18, "btf_fee": 0.505, "roll_100lf": 367.90},
        60: {"btf_base": 5.90, "btf_fee": 0.505, "roll_100lf": 459.88},
        72: {"btf_base": 7.04, "btf_fee": 0.505, "roll_100lf": 551.84},
    },
    "Huper Matte Blackout": {
        40: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 442.41},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 553.02},
        72: {"btf_base": 7.03, "btf_fee": 0.505, "roll_100lf": None},
    },
    "Huper Whiteout": {
        40: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 442.41},
        60: {"btf_base": 5.92, "btf_fee": 0.505, "roll_100lf": 553.02},
        72: {"btf_base": 7.03, "btf_fee": 0.505, "roll_100lf": None},
    },
    "Huper Dusted Crystal": {
        40: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 936.04},
        60: {"btf_base": 10.86, "btf_fee": 0.505, "roll_100lf": 1170.06},
        72: {"btf_base": 13.20, "btf_fee": 0.505, "roll_100lf": None},
    },
    "Huper Xtreme Pro": {
        40: {"btf_base": 0.31, "btf_fee": 0.505, "roll_100lf": 269.00},
        60: {"btf_base": 4.19, "btf_fee": 0.505, "roll_100lf": None},
    },
    "Huper Xtreme Ceramic": {
        40: {"btf_base": 1.27, "btf_fee": 0.505, "roll_100lf": 589.00},
        60: {"btf_base": 7.39, "btf_fee": 0.505, "roll_100lf": None},
    },
    "Twilight 35": {
        48: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 800.00, "roll_50lf": 440.00},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 1000.00, "roll_50lf": 550.00},
    },
    "Twilight 20": {
        48: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 800.00, "roll_50lf": 440.00},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 1000.00, "roll_50lf": 550.00},
    },
    "Twilight 10": {
        48: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 800.00, "roll_50lf": 440.00},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 1000.00, "roll_50lf": 550.00},
    },
    # ── ASWF — EXCLUSIVE SERIES ───────────────────────────────────────────────
    # ASWF pricing: price_sqft * (width_in / 12) = $/LF; rolls in 25ft increments
    "ASWF Aurora 40": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 897.00, "price_sqft": 3.00},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 1495.00, "price_sqft": 3.00},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 1794.00, "price_sqft": 3.00},
    },
    "ASWF Aurora 70": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 897.00, "price_sqft": 3.00},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 1495.00, "price_sqft": 3.00},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 1794.00, "price_sqft": 3.00},
    },
    "ASWF Twilight 10": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 600.00, "roll_50lf": 330.00, "price_sqft": 2.00},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 1000.00, "roll_50lf": 550.00, "price_sqft": 2.00},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 1200.00, "roll_50lf": 660.00, "price_sqft": 2.00},
    },
    "ASWF Twilight 20": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 600.00, "roll_50lf": 330.00, "price_sqft": 2.00},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 1000.00, "roll_50lf": 550.00, "price_sqft": 2.00},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 1200.00, "roll_50lf": 660.00, "price_sqft": 2.00},
    },
    "ASWF Twilight 35": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 600.00, "roll_50lf": 330.00, "price_sqft": 2.00},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 1000.00, "roll_50lf": 550.00, "price_sqft": 2.00},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 1200.00, "roll_50lf": 660.00, "price_sqft": 2.00},
    },
    # ── ASWF — DUAL REFLECTIVE SOLAR SERIES ──────────────────────────────────
    "ASWF Illusion": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 369.00, "price_sqft": 1.19},
        48: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 504.00, "price_sqft": 1.19},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 594.00, "price_sqft": 1.19},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 734.00, "price_sqft": 1.19},
    },
    "ASWF Daydream 5": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 369.00, "price_sqft": 1.19},
        48: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 504.00, "price_sqft": 1.19},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 594.00, "price_sqft": 1.19},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 734.00, "price_sqft": 1.19},
    },
    "ASWF Daydream 15": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 369.00, "price_sqft": 1.19},
        48: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 504.00, "price_sqft": 1.19},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 594.00, "price_sqft": 1.19},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 734.00, "price_sqft": 1.19},
    },
    "ASWF Daydream 25": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 369.00, "price_sqft": 1.19},
        48: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 504.00, "price_sqft": 1.19},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 594.00, "price_sqft": 1.19},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 734.00, "price_sqft": 1.19},
    },
    "ASWF Daydream 35": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 369.00, "price_sqft": 1.19},
        48: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 504.00, "price_sqft": 1.19},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 594.00, "price_sqft": 1.19},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 734.00, "price_sqft": 1.19},
    },
    "ASWF Sky 10": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 369.00, "price_sqft": 1.19},
        48: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 504.00, "price_sqft": 1.19},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 594.00, "price_sqft": 1.19},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 734.00, "price_sqft": 1.19},
    },
    "ASWF Sky 20": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 369.00, "price_sqft": 1.19},
        48: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 504.00, "price_sqft": 1.19},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 594.00, "price_sqft": 1.19},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 734.00, "price_sqft": 1.19},
    },
    "ASWF Sky 30": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 369.00, "price_sqft": 1.19},
        48: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 504.00, "price_sqft": 1.19},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 594.00, "price_sqft": 1.19},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 734.00, "price_sqft": 1.19},
    },
    "ASWF Sky 40": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 369.00, "price_sqft": 1.19},
        48: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 504.00, "price_sqft": 1.19},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 594.00, "price_sqft": 1.19},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 734.00, "price_sqft": 1.19},
    },
    # ── ASWF — SOLAR SERIES ───────────────────────────────────────────────────
    "ASWF Legacy 40": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 485.00, "price_sqft": 1.58},
        48: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 672.00, "price_sqft": 1.58},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 788.00, "price_sqft": 1.58},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 945.00, "price_sqft": 1.58},
    },
    "ASWF Legacy 50": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 485.00, "price_sqft": 1.58},
        48: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 672.00, "price_sqft": 1.58},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 788.00, "price_sqft": 1.58},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 945.00, "price_sqft": 1.58},
    },
    "ASWF Legacy 70": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 485.00, "price_sqft": 1.58},
        48: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 672.00, "price_sqft": 1.58},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 788.00, "price_sqft": 1.58},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 945.00, "price_sqft": 1.58},
    },
    "ASWF Nature 10": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 357.00, "price_sqft": 1.10},
        48: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 473.00, "price_sqft": 1.10},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 552.00, "price_sqft": 1.10},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 714.00, "price_sqft": 1.10},
    },
    "ASWF Nature 20": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 357.00, "price_sqft": 1.10},
        48: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 473.00, "price_sqft": 1.10},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 552.00, "price_sqft": 1.10},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 714.00, "price_sqft": 1.10},
    },
    "ASWF Nature 30": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 357.00, "price_sqft": 1.10},
        48: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 473.00, "price_sqft": 1.10},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 552.00, "price_sqft": 1.10},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 714.00, "price_sqft": 1.10},
    },
    "ASWF Nature 40": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 357.00, "price_sqft": 1.10},
        48: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 473.00, "price_sqft": 1.10},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 552.00, "price_sqft": 1.10},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 714.00, "price_sqft": 1.10},
    },
    "ASWF Nature 50": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 357.00, "price_sqft": 1.10},
        48: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 473.00, "price_sqft": 1.10},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 552.00, "price_sqft": 1.10},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 714.00, "price_sqft": 1.10},
    },
    "ASWF Horizon 20": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 357.00, "price_sqft": 1.10},
        48: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 473.00, "price_sqft": 1.10},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 552.00, "price_sqft": 1.10},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 714.00, "price_sqft": 1.10},
    },
    "ASWF Horizon 35": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 357.00, "price_sqft": 1.10},
        48: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 473.00, "price_sqft": 1.10},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 552.00, "price_sqft": 1.10},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 714.00, "price_sqft": 1.10},
    },
    "ASWF Moonlight 05": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 372.00, "price_sqft": 1.24},
        48: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 506.00, "price_sqft": 1.24},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 619.00, "price_sqft": 1.24},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 743.00, "price_sqft": 1.24},
    },
    "ASWF Moonlight 10": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 372.00, "price_sqft": 1.24},
        48: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 506.00, "price_sqft": 1.24},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 619.00, "price_sqft": 1.24},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 743.00, "price_sqft": 1.24},
    },
    "ASWF Moonlight 25": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 372.00, "price_sqft": 1.24},
        48: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 506.00, "price_sqft": 1.24},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 619.00, "price_sqft": 1.24},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 743.00, "price_sqft": 1.24},
    },
    "ASWF Reflection 20": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 275.00, "price_sqft": 0.86},
        48: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 374.00, "price_sqft": 0.86},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 431.00, "price_sqft": 0.86},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 550.00, "price_sqft": 0.86},
    },
    "ASWF Reflection 35": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 275.00, "price_sqft": 0.86},
        48: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 374.00, "price_sqft": 0.86},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 431.00, "price_sqft": 0.86},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 550.00, "price_sqft": 0.86},
    },
    "ASWF Reflection 50": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 275.00, "price_sqft": 0.86},
        48: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 374.00, "price_sqft": 0.86},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 431.00, "price_sqft": 0.86},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 550.00, "price_sqft": 0.86},
    },
    "ASWF Firewall 70": {
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 788.00, "price_sqft": 1.58},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 945.00, "price_sqft": 1.58},
    },
    # ── ASWF — DESIGN SERIES ──────────────────────────────────────────────────
    "ASWF UV Clear": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 335.00, "price_sqft": 1.11},
        48: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 475.00, "price_sqft": 1.11},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 555.00, "price_sqft": 1.11},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 665.00, "price_sqft": 1.11},
    },
    "ASWF White Frost": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 275.00, "price_sqft": 0.86},
        48: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 370.00, "price_sqft": 0.86},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 430.00, "price_sqft": 0.86},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 545.00, "price_sqft": 0.86},
    },
    "ASWF Black Out": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 275.00, "price_sqft": 0.86},
        48: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 370.00, "price_sqft": 0.86},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 430.00, "price_sqft": 0.86},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 545.00, "price_sqft": 0.86},
    },
    "ASWF White Out": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 275.00, "price_sqft": 0.86},
        48: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 370.00, "price_sqft": 0.86},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 430.00, "price_sqft": 0.86},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 545.00, "price_sqft": 0.86},
    },
    "ASWF Removable White Frost": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 275.00, "price_sqft": 0.86},
        48: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 370.00, "price_sqft": 0.86},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 430.00, "price_sqft": 0.86},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 545.00, "price_sqft": 0.86},
    },
    "ASWF Removable Blackout": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 275.00, "price_sqft": 0.86},
        48: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 370.00, "price_sqft": 0.86},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 430.00, "price_sqft": 0.86},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 545.00, "price_sqft": 0.86},
    },
    # ── ASWF — PROTECTION & SECURITY ─────────────────────────────────────────
    "ASWF Safety Clear 4mil": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 258.00, "price_sqft": 0.86},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 430.00, "price_sqft": 0.86},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 516.00, "price_sqft": 0.86},
    },
    "ASWF Safety Clear 7mil": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 330.00, "price_sqft": 1.10},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 550.00, "price_sqft": 1.10},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 660.00, "price_sqft": 1.10},
    },
    "ASWF Safety Clear 8mil": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 435.00, "price_sqft": 1.45},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 725.00, "price_sqft": 1.45},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 870.00, "price_sqft": 1.45},
    },
    "ASWF Safety Clear 12mil": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 795.00, "price_sqft": 2.65},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 1325.00, "price_sqft": 2.65},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 1590.00, "price_sqft": 2.65},
    },
    "ASWF Safety Clear 16mil": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 825.00, "price_sqft": 2.75},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 1375.00, "price_sqft": 2.75},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 1650.00, "price_sqft": 2.75},
    },
    "ASWF AG Clear 4mil": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 270.00, "price_sqft": 0.90},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 450.00, "price_sqft": 0.90},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 540.00, "price_sqft": 0.90},
    },
    "ASWF AG Clear 6mil": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 390.00, "price_sqft": 1.30},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 650.00, "price_sqft": 1.30},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 780.00, "price_sqft": 1.30},
    },
    "ASWF AG Clear 7mil": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 405.00, "price_sqft": 1.35},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 675.00, "price_sqft": 1.35},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 810.00, "price_sqft": 1.35},
    },
    "ASWF Solar Safety 4mil Reflection 20": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 360.00, "price_sqft": 1.20},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 600.00, "price_sqft": 1.20},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 720.00, "price_sqft": 1.20},
    },
    "ASWF Solar Safety 8mil Reflection 20": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 492.00, "price_sqft": 1.64},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 820.00, "price_sqft": 1.64},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 984.00, "price_sqft": 1.64},
    },
    "ASWF Solar Safety 4mil Nature 20/40": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 420.00, "price_sqft": 1.40},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 700.00, "price_sqft": 1.40},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 840.00, "price_sqft": 1.40},
    },
    "ASWF Solar Safety 8mil Nature 20/40": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 540.00, "price_sqft": 1.80},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 900.00, "price_sqft": 1.80},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 1080.00, "price_sqft": 1.80},
    },
    "ASWF Solar Safety 9mil Daydream 25": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 675.00, "price_sqft": 2.25},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 1125.00, "price_sqft": 2.25},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 1350.00, "price_sqft": 2.25},
    },
    "ASWF Solar Safety 10mil Legacy 50": {
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 1125.00, "price_sqft": 2.25},
    },
    # ── ASWF — EXTERIOR FILMS ─────────────────────────────────────────────────
    "ASWF Exterior Legacy 40": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 499.00},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 832.00},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 999.00},
    },
    "ASWF Exterior Legacy 70": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 499.00},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 832.00},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 999.00},
    },
    "ASWF Exterior Nature 20": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 360.00},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 600.00},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 720.00},
    },
    "ASWF Exterior Nature 30": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 360.00},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 600.00},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 720.00},
    },
    "ASWF Exterior Reflection 20": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 360.00},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 600.00},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 720.00},
    },
    "ASWF Exterior Reflection 35": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 360.00},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 600.00},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 720.00},
    },
    "ASWF Exterior 7mil Safety": {
        36: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 465.00},
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 889.00},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 930.00},
    },
}

DEFAULT_FILM_RATES = {
    48: {"btf_base": 5.87, "btf_fee": 0.505, "roll_100lf": None},
    60: {"btf_base": 6.88, "btf_fee": 0.505, "roll_100lf": None},
    72: {"btf_base": 7.50, "btf_fee": 0.505, "roll_100lf": None},
}

# Films that must be ordered in full rolls only (no by-the-foot)
FULL_ROLL_ONLY_KEYWORDS = [
    "guardian", "cs 4mil", "cs 8mil", "cs 14mil", "shield 35",
    "twilight", "clearshield", "safety", "security",
    "ultrasafe", "bsf solar", "aswf",
]

# Minimum selling price floors per sqft by product family
PRICE_FLOORS_PER_SQFT: Dict[str, float] = {
    "ultraview":      7.50,
    "twilight":      10.00,
    "aurora":        12.00,
    "aswf aurora":   12.00,
    "aswf twilight": 10.00,
    "aswf":           7.00,
    "huper":         12.00,
    "edge pristine": 12.00,
    "pristine":      12.00,
    "safety":         8.00,
    "guardian":       8.00,
    "decorative":     6.00,
    "frost":          6.00,
    "blackout":       6.00,
    "whiteout":       6.00,
    "sxf":            8.00,
    "ultrasafe":      8.00,
    "ultracool":      7.50,
    "sxo":            8.00,
    "sxp":            8.00,
    "sxg":            9.00,
    "sxn":            9.00,
    "sxi":           12.00,
    "sgc":           15.00,
    "default":        7.50,
}

# Production baseline: solo installer residential (sqft/day)
SOLO_INSTALLER_SQFT_PER_DAY = 300

# =============================================================================
# SUPPLIER METADATA
# =============================================================================

# Free shipping thresholds by supplier (order subtotal in $)
SUPPLIER_FREE_SHIPPING: Dict[str, float] = {
    "Edge":           1000.00,
    "Huper Optik":    1000.00,
    "ASWF":           1000.00,
}

# Supplier keyword mapping — used to identify which supplier a film belongs to
SUPPLIER_KEYWORDS: Dict[str, List[str]] = {
    "Edge": [
        "ultraview", "reform", "cool alloy", "coal alloy", "silver", "bronze",
        "nature", "pristine", "x series", "guardian", "cs 4mil", "cs 8mil",
        "cs 14mil", "shield 35", "frost", "blackout", "whiteout",
        "clear defense", "twilight",
    ],
    "Huper Optik": [
        "klar", "huper ceramic", "multi-layer", "single layer", "dark ceramic",
        "select sech", "select drei", "huper fusion", "huper bronze", "huper silver",
        "huper whiteout", "huper blackout", "dusted crystal", "clearshield",
        "xtreme pro", "xtreme ceramic", "huper",
    ],
    "ASWF": [
        "aswf",
    ],
}


def get_supplier(film_name: str) -> str:
    """
    Identify which supplier a film belongs to.
    ASWF is checked first (prefix match) to prevent keyword collisions
    with Edge/Huper films that share words like 'nature', 'frost', 'silver'.
    """
    film_lower = film_name.lower()

    # ASWF: always starts with 'aswf ' — check first to avoid collisions
    if film_lower.startswith("aswf"):
        return "ASWF"

    # Huper Optik: check before Edge to prevent 'silver'/'bronze' collision
    if any(kw in film_lower for kw in SUPPLIER_KEYWORDS["Huper Optik"]):
        return "Huper Optik"

    # Edge (catch-all for remaining known Edge products)
    if any(kw in film_lower for kw in SUPPLIER_KEYWORDS["Edge"]):
        return "Edge"

    return "Unknown"


def check_free_shipping(film_name: str, order_cost: float) -> Dict[str, Any]:
    """
    Check whether an order qualifies for free shipping.

    Returns:
        supplier: name of the supplier
        qualifies: True if order meets free shipping threshold
        threshold: the free shipping minimum
        shortfall: amount needed to reach free shipping (0 if already qualifies)
    """
    supplier = get_supplier(film_name)
    threshold = SUPPLIER_FREE_SHIPPING.get(supplier, 0.0)
    qualifies = order_cost >= threshold
    shortfall = max(0.0, round(threshold - order_cost, 2))
    return {
        "supplier": supplier,
        "qualifies": qualifies,
        "threshold": threshold,
        "shortfall": shortfall,
    }

# =============================================================================
# LABOR MODEL
# =============================================================================

# Base labor rates per sqft
LABOR_BASE_RATES: Dict[str, float] = {
    "solar":       3.00,   # Solar control film (all standard products)
    "decorative":  3.00,   # Standard decorative (Frost, Blackout, Whiteout)
    "safety":      3.50,   # Safety & Security films
    "specialty":   4.50,   # Specialty decorative (complex patterns, cut graphics)
    "caulking":    3.00,   # Per LINEAR FOOT of caulking (separate line item)
}

# Complexity adders — v4.4 CORRECTED VALUES
# NOTE: french_panes is charged at $8/pane (flat), NOT per sqft.
#       It is handled separately via french_panes_count in calculate_line_item_labor.
COMPLEXITY_ADDERS: Dict[str, Dict[str, Any]] = {
    "removal": {
        "label": "Film Removal",
        "adder": 2.00,
        "per": "sqft",
        "help": "Existing film must be removed before installation. Adds $2.00/sqft.",
    },
    "new_construction": {
        "label": "New Construction",
        "adder": 1.00,
        "per": "sqft",
        "help": "New construction site — dust, debris, and extra prep. Adds $1.00/sqft.",
    },
    "ladder": {
        "label": "Ladder / High Work",
        "adder": 1.00,
        "per": "sqft",
        "help": "Windows not accessible from ground level. Adds $1.00/sqft.",
    },
    "frames": {
        "label": "Dirty / Painted Frames",
        "adder": 0.50,
        "per": "sqft",
        "help": "Delicate or dirty wood/painted frames requiring extra care. Adds $0.50/sqft.",
    },
    "specialty_decorative": {
        "label": "Specialty Decorative Install",
        "adder": 1.50,
        "per": "sqft",
        "help": "Complex decorative film requiring precision cutting or alignment. Adds $1.50/sqft.",
    },
}

# French pane charge: $8.00 per pane (separate from sqft adders)
FRENCH_PANE_RATE = 8.00

# Go/No-Go margin thresholds
GO_NOGO_MIN_MARGIN = 40.0      # Red below this
GO_NOGO_WARN_MARGIN = 45.0     # Yellow between min and warn


def is_full_roll_only(film_name: str) -> bool:
    """Return True if this film must be ordered in full rolls only."""
    film_lower = film_name.lower()
    return any(kw in film_lower for kw in FULL_ROLL_ONLY_KEYWORDS)


def is_safety_film(film_name: str) -> bool:
    """Return True if this film is a Safety & Security product."""
    film_lower = film_name.lower()
    safety_keywords = ["guardian", "cs 4mil", "cs 8mil", "cs 14mil", "shield", "clearshield", "safety", "security", "aswf safety", "aswf ag", "aswf solar safety"]
    return any(kw in film_lower for kw in safety_keywords)


def get_labor_base_rate(film_name: str) -> float:
    """Return the base labor rate per sqft for the given film."""
    film_lower = film_name.lower()
    if is_safety_film(film_name):
        return LABOR_BASE_RATES["safety"]
    if any(kw in film_lower for kw in ["frost", "blackout", "whiteout", "decorative", "aswf white", "aswf black"]):
        return LABOR_BASE_RATES["decorative"]
    return LABOR_BASE_RATES["solar"]


def calculate_line_item_labor(
    sqft: float,
    film_name: str,
    complexity_flags: Dict[str, bool],
    french_panes_count: int = 0,
) -> Dict[str, Any]:
    """
    Calculate labor cost for a single line item (window group).

    Args:
        sqft: Square footage of this line item.
        film_name: Name of the film being installed.
        complexity_flags: Dict of complexity keys -> True/False.
            Keys: removal, new_construction, ladder, frames, specialty_decorative
        french_panes_count: Number of french panes charged at $8.00/pane (flat, not per sqft).

    Returns:
        Dict with base_rate, sqft_adder, total_rate, sqft_labor, french_pane_cost, labor_cost, breakdown.
    """
    base_rate = get_labor_base_rate(film_name)

    # Sqft-based adders
    sqft_adder = sum(
        COMPLEXITY_ADDERS[key]["adder"]
        for key, active in complexity_flags.items()
        if active and key in COMPLEXITY_ADDERS
    )
    total_rate = base_rate + sqft_adder
    sqft_labor = round(total_rate * sqft, 2)

    # French pane adder: $8/pane (flat)
    french_pane_cost = round(french_panes_count * FRENCH_PANE_RATE, 2)
    labor_cost = round(sqft_labor + french_pane_cost, 2)

    active_factors = [
        COMPLEXITY_ADDERS[key]["label"]
        for key, active in complexity_flags.items()
        if active and key in COMPLEXITY_ADDERS
    ]
    if french_panes_count > 0:
        active_factors.append(f"French Panes ({french_panes_count} panes × $8.00 = ${french_pane_cost:.2f})")

    return {
        "base_rate": base_rate,
        "sqft_adder": sqft_adder,
        "total_rate": total_rate,
        "sqft_labor": sqft_labor,
        "french_pane_cost": french_pane_cost,
        "labor_cost": labor_cost,
        "active_factors": active_factors,
        "sqft": sqft,
        "french_panes_count": french_panes_count,
    }


def calculate_caulking_cost(linear_feet: float) -> float:
    """Calculate caulking labor cost at $3.00/LF."""
    return round(linear_feet * LABOR_BASE_RATES["caulking"], 2)


def go_nogo_decision(
    selling_price: float,
    total_cost: float,
    min_margin_pct: float = GO_NOGO_MIN_MARGIN,
    warn_margin_pct: float = GO_NOGO_WARN_MARGIN,
) -> Dict[str, Any]:
    """
    Evaluate whether a job meets the minimum margin threshold.

    Returns:
        status: "go" | "warn" | "nogo"
        color: "green" | "yellow" | "red"
        actual_margin_pct: calculated gross margin
        gross_profit: selling_price - total_cost
        message: human-readable recommendation
    """
    if selling_price <= 0:
        return {"status": "nogo", "color": "red", "actual_margin_pct": 0.0,
                "gross_profit": 0.0, "message": "No selling price set."}

    gross_profit = selling_price - total_cost
    actual_margin = round((gross_profit / selling_price) * 100, 1)

    if actual_margin >= warn_margin_pct:
        return {
            "status": "go",
            "color": "green",
            "actual_margin_pct": actual_margin,
            "gross_profit": gross_profit,
            "message": f"GO — {actual_margin}% margin. Meets target.",
        }
    elif actual_margin >= min_margin_pct:
        return {
            "status": "warn",
            "color": "yellow",
            "actual_margin_pct": actual_margin,
            "gross_profit": gross_profit,
            "message": f"CAUTION — {actual_margin}% margin. Below target but acceptable.",
        }
    else:
        return {
            "status": "nogo",
            "color": "red",
            "actual_margin_pct": actual_margin,
            "gross_profit": gross_profit,
            "message": f"NO-GO — {actual_margin}% margin. Below {min_margin_pct}% minimum.",
        }


# =============================================================================
# MATERIAL COST FUNCTIONS
# =============================================================================

def get_film_rates(film_name: str, roll_width: int) -> Dict[str, float]:
    """Return the rate dictionary for a given film and roll width."""
    rates = FILM_RATES.get(film_name, {})
    if roll_width in rates:
        return rates[roll_width]

    film_lower = film_name.lower()
    for key, widths in FILM_RATES.items():
        if key.lower() in film_lower or film_lower in key.lower():
            if roll_width in widths:
                return widths[roll_width]

    return DEFAULT_FILM_RATES.get(roll_width, DEFAULT_FILM_RATES[48])


def calculate_material_cost(
    film_name: str,
    roll_width: int,
    required_lf: float,
    buffer_lf: float,
) -> Dict[str, Any]:
    """
    Calculate material cost for a given film order.
    Handles full-roll-only films (Safety, Twilight) automatically.
    """
    rates = get_film_rates(film_name, roll_width)
    order_lf = round(required_lf + buffer_lf, 2)
    order_lf_ceil = int(order_lf) + (1 if order_lf % 1 > 0 else 0)

    # ASWF films: price_sqft * (width_in / 12) = $/LF
    if rates.get("price_sqft") is not None and rates.get("btf_base") is None:
        price_sqft = rates["price_sqft"]
        rate_per_lf = round(price_sqft * (roll_width / 12.0), 4)
        btf_cost = round(rate_per_lf * order_lf_ceil, 2)
        roll_100lf_price = rates.get("roll_100lf")
        roll_50lf_price = rates.get("roll_50lf")
        full_roll_savings = None
        recommended_cost = btf_cost
        order_method = "by_the_foot"
        if roll_100lf_price and order_lf_ceil <= 100 and roll_100lf_price < btf_cost:
            full_roll_savings = round(btf_cost - roll_100lf_price, 2)
            recommended_cost = roll_100lf_price
            order_method = "full_roll"
            order_lf_ceil = 100
        elif roll_50lf_price and order_lf_ceil <= 50 and roll_50lf_price < btf_cost:
            full_roll_savings = round(btf_cost - roll_50lf_price, 2)
            recommended_cost = roll_50lf_price
            order_method = "50lf_roll"
            order_lf_ceil = 50
        if order_method == "by_the_foot":
            # ASWF rolls come in 25ft increments
            order_lf_ceil = max(25, ((order_lf_ceil + 24) // 25) * 25)
            recommended_cost = round(rate_per_lf * order_lf_ceil, 2)
        return {
            "order_lf": order_lf_ceil,
            "btf_cost": btf_cost,
            "full_roll_cost": roll_100lf_price,
            "full_roll_savings": full_roll_savings,
            "recommended_cost": recommended_cost,
            "order_method": order_method,
            "full_roll_only": False,
            "rates": rates,
            "rate_per_lf": rate_per_lf,
        }

    full_roll_only = is_full_roll_only(film_name) or rates.get("btf_base") is None

    if full_roll_only:
        # Must order in 50 LF or 100 LF increments
        roll_50lf_price = rates.get("roll_50lf")
        roll_100lf_price = rates.get("roll_100lf")

        if roll_50lf_price and order_lf_ceil <= 50:
            recommended_cost = roll_50lf_price
            order_lf_ceil = 50
            order_method = "50lf_roll"
            full_roll_savings = None
        elif roll_100lf_price:
            recommended_cost = roll_100lf_price
            order_lf_ceil = 100
            order_method = "full_roll"
            full_roll_savings = None
        else:
            # Fallback: estimate from default rates
            recommended_cost = round(order_lf_ceil * 8.0, 2)
            order_method = "estimate"
            full_roll_savings = None

        return {
            "order_lf": order_lf_ceil,
            "btf_cost": None,
            "full_roll_cost": roll_100lf_price,
            "full_roll_savings": full_roll_savings,
            "recommended_cost": recommended_cost,
            "order_method": order_method,
            "full_roll_only": True,
            "rates": rates,
        }

    # Standard by-the-foot film
    btf_cost = round(order_lf_ceil * (rates["btf_base"] + rates["btf_fee"]), 2)

    full_roll_cost = None
    full_roll_savings = None
    order_method = "by_the_foot"
    recommended_cost = btf_cost

    if rates.get("roll_100lf") and order_lf_ceil <= 100:
        full_roll_cost = rates["roll_100lf"]
        if full_roll_cost < btf_cost:
            full_roll_savings = round(btf_cost - full_roll_cost, 2)
            recommended_cost = full_roll_cost
            order_method = "full_roll"
            order_lf_ceil = 100

    return {
        "order_lf": order_lf_ceil,
        "btf_cost": btf_cost,
        "full_roll_cost": full_roll_cost,
        "full_roll_savings": full_roll_savings,
        "recommended_cost": recommended_cost,
        "order_method": order_method,
        "full_roll_only": False,
        "rates": rates,
    }


def get_price_floor(film_name: str) -> float:
    """Return the minimum selling price per sqft for the given film family."""
    film_lower = film_name.lower()
    for family, floor in PRICE_FLOORS_PER_SQFT.items():
        if family in film_lower:
            return floor
    return PRICE_FLOORS_PER_SQFT["default"]


def calculate_selling_price(
    material_cost: float,
    labor_cost: float,
    section_sqft: int,
    margin_pct: float,
    daily_revenue: float,
    min_price: float,
    film_name: str,
) -> Dict[str, float]:
    """
    Recommended selling price = max of:
      1. (Material + Labor) marked up to target margin
      2. Price floor for the film family (per sqft × total sqft)
      3. Daily production revenue target (prorated by sqft)
      4. Minimum job price
    """
    total_cost = material_cost + labor_cost
    margin_fraction = margin_pct / 100.0
    margin_price = round(total_cost / (1 - margin_fraction), 2) if margin_fraction < 1 else total_cost * 2

    floor_per_sqft = get_price_floor(film_name)
    floor_price = round(floor_per_sqft * section_sqft, 2)

    days_needed = section_sqft / SOLO_INSTALLER_SQFT_PER_DAY
    production_price = round(days_needed * daily_revenue, 2)

    recommended = max(margin_price, floor_price, production_price, min_price)

    return {
        "recommended": recommended,
        "margin_price": margin_price,
        "floor_price": floor_price,
        "production_price": production_price,
        "min_job_price": min_price,
        "floor_per_sqft": floor_per_sqft,
        "total_cost": total_cost,
        "material_cost": material_cost,
        "labor_cost": labor_cost,
    }


def group_windows_by_section(windows: List[Dict]) -> Dict[str, List[Dict]]:
    """Group window records by their section name."""
    groups: Dict[str, List[Dict]] = {}
    for w in windows:
        section = w.get("section", "Unassigned")
        if section not in groups:
            groups[section] = []
        groups[section].append(w)
    return groups


# =============================================================================
# OPTIMIZATION ENGINE
# =============================================================================

def _orientation_options(pane: Dict[str, Any], roll_width: int) -> List[Dict[str, Any]]:
    width = int(pane["width"])
    height = int(pane["height"])
    options: List[Dict[str, Any]] = []
    if width <= roll_width:
        options.append({"width": width, "height": height})
    if height <= roll_width and height != width:
        options.append({"width": height, "height": width})
    return options


def _pane_sort_key(pane: Dict[str, Any], roll_width: int) -> Tuple[int, int, int]:
    width = int(pane["width"])
    height = int(pane["height"])
    return (max(width, height), min(width, height), width * height)


def _best_fit_for_existing_row(
    pane: Dict[str, Any],
    row: Dict[str, Any],
    roll_width: int,
) -> Optional[Dict[str, Any]]:
    remaining_width = roll_width - row["used_width"]
    current_pull_to = row["pull_to"]
    best_option: Optional[Dict[str, Any]] = None
    best_score: Optional[Tuple[int, int]] = None

    for option in _orientation_options(pane, roll_width):
        if option["width"] > remaining_width:
            continue
        added_pull = max(current_pull_to, option["height"]) - current_pull_to
        score = (added_pull, -(row["used_width"] + option["width"]))
        if best_score is None or score < best_score:
            best_score = score
            best_option = option

    return best_option


def _best_fit_for_new_row(
    pane: Dict[str, Any],
    roll_width: int,
) -> Optional[Dict[str, Any]]:
    best_option: Optional[Dict[str, Any]] = None
    best_score: Optional[Tuple[int, int]] = None

    for option in _orientation_options(pane, roll_width):
        score = (option["height"], -option["width"])
        if best_score is None or score < best_score:
            best_score = score
            best_option = option

    return best_option


def optimize_for_roll_width(panes: List[Dict[str, Any]], roll_width: int) -> Dict[str, Any]:
    """
    Arrange panes across a single roll width using First-Fit Decreasing heuristic.
    """
    if roll_width <= 0:
        raise ValueError("roll_width must be a positive integer")
    if not panes:
        return {"total_lf": 0.0, "rows": []}

    sorted_panes = sorted(
        [{"width": int(p["width"]), "height": int(p["height"])} for p in panes],
        key=lambda p: _pane_sort_key(p, roll_width),
        reverse=True,
    )

    rows: List[Dict[str, Any]] = []

    for pane in sorted_panes:
        placed = False
        for row in rows:
            option = _best_fit_for_existing_row(pane, row, roll_width)
            if option is None:
                continue
            row["panes"].append(option)
            row["used_width"] += option["width"]
            row["pull_to"] = max(row["pull_to"], option["height"])
            row["lanes"] = len(row["panes"])
            placed = True
            break

        if not placed:
            option = _best_fit_for_new_row(pane, roll_width)
            if option is None:
                raise ValueError(f"Pane {pane} cannot fit on roll width {roll_width} in any orientation.")
            rows.append({
                "panes": [option],
                "used_width": option["width"],
                "pull_to": option["height"],
                "lanes": 1,
            })

    total_inches = sum(row["pull_to"] for row in rows)
    total_lf = round(total_inches / 12.0, 2)

    return {"total_lf": total_lf, "rows": rows}
