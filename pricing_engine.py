# pricing_engine.py
# East Coast Window Films — Pricing Engine v4.3
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
    "SXF-5050": {
        60: {"btf_base": 9.36, "btf_fee": 0.0, "roll_100lf": 936.00},
    },
    "SXF-5060": {
        60: {"btf_base": 9.36, "btf_fee": 0.0, "roll_100lf": 936.00},
    },
    "SXF-5070": {
        60: {"btf_base": 9.36, "btf_fee": 0.0, "roll_100lf": 936.00},
    },
    "SXF-5080": {
        60: {"btf_base": 9.36, "btf_fee": 0.0, "roll_100lf": 936.00},
    },
    "SXB-001": {
        48: {"btf_base": 12.11, "btf_fee": 0.0, "roll_100lf": 1211.25},
    },
    "SXB-002": {
        48: {"btf_base": 12.11, "btf_fee": 0.0, "roll_100lf": 1211.25},
    },
    "SXO Colored Frosted": {
        48: {"btf_base": 7.81, "btf_fee": 0.0, "roll_100lf": None, "roll_150lf": 1171.80},
    },
    "SXP Colored Frosted": {
        60: {"btf_base": 10.26, "btf_fee": 0.0, "roll_100lf": 1025.85},
    },
    "SXG Geometric": {
        60: {"btf_base": 10.26, "btf_fee": 0.0, "roll_100lf": 1025.85},
    },
    "SXN Organic": {
        60: {"btf_base": 10.26, "btf_fee": 0.0, "roll_100lf": 1025.85},
    },
    "UltraSafe 2mil": {
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 318.15, "roll_50lf": None},
    },
    "UltraSafe 4mil": {
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 431.55, "roll_50lf": None},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 517.65, "roll_50lf": None},
    },
    "UltraSafe 8mil": {
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 572.25, "roll_50lf": None},
    },
    "UltraSafe White Matte": {
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 813.75, "roll_50lf": None},
    },
    "UltraCool Silver 15": {
        60: {"btf_base": 4.01, "btf_fee": 0.0, "roll_100lf": 401.10},
    },
    "UltraCool Silver 35": {
        60: {"btf_base": 4.01, "btf_fee": 0.0, "roll_100lf": 401.10},
    },
    "UltraCool Silver 60": {
        60: {"btf_base": 4.01, "btf_fee": 0.0, "roll_100lf": 401.10},
    },
    "UltraCool Blue Silver": {
        60: {"btf_base": 4.67, "btf_fee": 0.0, "roll_100lf": 467.25},
    },
    "UltraCool IR83": {
        60: {"btf_base": 7.05, "btf_fee": 0.0, "roll_100lf": 704.55},
    },
    "UltraCool Solar Bronze": {
        60: {"btf_base": 10.27, "btf_fee": 0.0, "roll_100lf": 1026.90},
    },
    "BSF Solar Bird Safety": {
        60: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 2084.25, "roll_50lf": None},
        72: {"btf_base": None, "btf_fee": 0.0, "roll_100lf": 2501.10, "roll_50lf": None},
    },
    "SX-STPF Sea Turtle": {
        60: {"btf_base": 7.72, "btf_fee": 0.0, "roll_100lf": 756.32},
    },
    "SGC Simulated Glass": {
        59: {"btf_base": 22.84, "btf_fee": 0.0, "roll_100lf": 2283.75},
    },
    "SXI Gradient": {
        60: {"btf_base": 13.18, "btf_fee": 0.0, "roll_100lf": 1317.75},
        71: {"btf_base": 29.60, "btf_fee": 0.0, "roll_100lf": 2900.75},
    },
    "SX-7876 Chalkboard": {
        36: {"btf_base": 5.75, "btf_fee": 0.0, "roll_100lf": None},
        48: {"btf_base": 9.61, "btf_fee": 0.0, "roll_100lf": None},
        72: {"btf_base": 11.66, "btf_fee": 0.0, "roll_100lf": None},
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
    "ultrasafe", "bsf solar",
]

# Minimum selling price floors per sqft by product family
PRICE_FLOORS_PER_SQFT: Dict[str, float] = {
    "ultraview":      7.50,
    "twilight":      10.00,
    "aurora":        12.00,
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
    "solyx":          8.00,
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
    "Solyx":          1000.00,
}

# Supplier keyword mapping — used to identify which supplier a film belongs to
SUPPLIER_KEYWORDS: Dict[str, List[str]] = {
    "Edge": [
        "ultraview", "reform", "cool alloy", "coal alloy", "silver", "bronze",
        "nature", "pristine", "x series", "guardian", "cs 4mil", "cs 8mil",
        "cs 14mil", "shield 35", "frost", "blackout", "whiteout",
        "clear defense",
    ],
    "Huper Optik": [
        "klar", "huper ceramic", "multi-layer", "single layer", "dark ceramic",
        "select sech", "select drei", "huper fusion", "huper bronze", "huper silver",
        "huper whiteout", "huper blackout", "dusted crystal", "clearshield",
        "xtreme pro", "xtreme ceramic", "huper",
    ],
    "Solyx": [
        "sxf", "sxo", "sxp", "sxb", "sxg", "sxn", "sxi", "sgc", "sx-stpf",
        "sx-7876", "chalkboard", "sea turtle", "twilight", "aurora",
        "ultrasafe", "bsf solar", "solyx",
    ],
}


def get_supplier(film_name: str) -> str:
    """Identify which supplier a film belongs to."""
    film_lower = film_name.lower()
    for supplier, keywords in SUPPLIER_KEYWORDS.items():
        if any(kw in film_lower for kw in keywords):
            return supplier
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

# Complexity adders per sqft — applied per line item, not per whole job
COMPLEXITY_ADDERS: Dict[str, Dict[str, Any]] = {
    "removal": {
        "label": "Film Removal",
        "adder": 1.00,
        "help": "Existing film must be removed before installation. Adds $1.00/sqft.",
    },
    "frames": {
        "label": "Dirty/Painted Frames",
        "adder": 0.50,
        "help": "Delicate or dirty wood/painted frames requiring extra care. Adds $0.50/sqft.",
    },
    "french_panes": {
        "label": "French Panes",
        "adder": 1.50,
        "help": "Multiple small divided panes requiring individual cuts. Adds $1.50/sqft.",
    },
    "small_windows": {
        "label": "Many Small Windows",
        "adder": 1.25,
        "help": "High pane count with small individual windows. Adds $1.25/sqft.",
    },
    "ladder": {
        "label": "Ladder/Scaffold/Lift",
        "adder": 0.75,
        "help": "Windows not accessible from ground level. Adds $0.75/sqft.",
    },
    "dust_debris": {
        "label": "Construction Dust/Debris",
        "adder": 0.50,
        "help": "New construction site with excessive dust or debris. Adds $0.50/sqft.",
    },
    "specialty_decorative": {
        "label": "Specialty Decorative Install",
        "adder": 1.50,
        "help": "Complex decorative film requiring precision cutting or alignment. Adds $1.50/sqft.",
    },
}

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
    safety_keywords = ["guardian", "cs 4mil", "cs 8mil", "cs 14mil", "shield", "clearshield", "safety", "security"]
    return any(kw in film_lower for kw in safety_keywords)


def get_labor_base_rate(film_name: str) -> float:
    """Return the base labor rate per sqft for the given film."""
    film_lower = film_name.lower()
    if is_safety_film(film_name):
        return LABOR_BASE_RATES["safety"]
    if any(kw in film_lower for kw in ["frost", "blackout", "whiteout", "decorative"]):
        return LABOR_BASE_RATES["decorative"]
    return LABOR_BASE_RATES["solar"]


def calculate_line_item_labor(
    sqft: float,
    film_name: str,
    complexity_flags: Dict[str, bool],
) -> Dict[str, float]:
    """
    Calculate labor cost for a single line item (window group).

    Args:
        sqft: Square footage of this line item.
        film_name: Name of the film being installed.
        complexity_flags: Dict of complexity keys -> True/False.
            Keys: removal, frames, french_panes, small_windows, ladder, dust_debris, specialty_decorative

    Returns:
        Dict with base_rate, complexity_adder, total_rate, labor_cost, breakdown.
    """
    base_rate = get_labor_base_rate(film_name)
    complexity_adder = sum(
        COMPLEXITY_ADDERS[key]["adder"]
        for key, active in complexity_flags.items()
        if active and key in COMPLEXITY_ADDERS
    )
    total_rate = base_rate + complexity_adder
    labor_cost = round(total_rate * sqft, 2)

    active_factors = [
        COMPLEXITY_ADDERS[key]["label"]
        for key, active in complexity_flags.items()
        if active and key in COMPLEXITY_ADDERS
    ]

    return {
        "base_rate": base_rate,
        "complexity_adder": complexity_adder,
        "total_rate": total_rate,
        "labor_cost": labor_cost,
        "active_factors": active_factors,
        "sqft": sqft,
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
