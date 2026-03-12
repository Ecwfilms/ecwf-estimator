# ECWF Estimator

**East Coast Window Films — Internal Cost Estimator & Business Decision Tool**

A Streamlit-based estimator for window tinting jobs that calculates material costs, labor, margins, and recommended selling prices.

## Features

- **PDF Parsing**: Upload TintWiz CRM worksheets to auto-populate job details
- **Multi-Supplier Pricing**: Edge, Huper Optik, and Solyx/Decorative Films
- **Roll Optimization**: First-Fit Decreasing bin-packing for minimal film waste
- **Go/No-Go Engine**: 40% minimum margin threshold with green/yellow/red indicators
- **Job Complexity Scoring**: 7 factors including film removal, ladder work, exterior install
- **Room Selector**: Adjust pricing by removing specific rooms/areas
- **Film Lookup**: Quick price checks for any film product

## Usage

1. Select a film supplier and product
2. Upload a TintWiz PDF worksheet (optional) or enter pane dimensions manually
3. Review material costs, labor estimates, and recommended sell price
4. Use the Go/No-Go indicator to make informed bidding decisions

## Deployment

This app is deployed on [Streamlit Community Cloud](https://streamlit.io/cloud).

---

*Internal tool for East Coast Window Films. Not for public distribution.*
