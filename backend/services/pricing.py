"""
Pricing engine for Cleannest.

All rates are in USD. Adjust the constants below to change pricing
without touching any other file.
"""
from __future__ import annotations
from models.service_info import ServiceInfo, SERVICE_TYPE_LABELS, FREQUENCY_LABELS
from models.quote import Quote, LineItem


# ── Base rates by service type ────────────────────────────────────────────────

BASE_RATES: dict[str, float] = {
    "standard": 120.00,
    "deep": 200.00,
    "move-in-out": 250.00,
    "airbnb": 150.00,
}

# ── Per-bedroom and per-bathroom surcharges ───────────────────────────────────

BED_RATE: float = 20.00    # per bedroom above 1
BATH_RATE: float = 15.00   # per bathroom above 1

# ── sqft-based pricing (used ONLY when beds/baths are not provided) ───────────
# Tiered: (max_sqft, price_per_sqft)

SQFT_TIERS: list[tuple[int, float]] = [
    (1000, 0.14),
    (1500, 0.13),
    (2500, 0.12),
    (4000, 0.11),
    (999_999, 0.10),
]

# ── Frequency discounts ───────────────────────────────────────────────────────

FREQUENCY_DISCOUNTS: dict[str, float] = {
    "one-time": 0.00,
    "monthly": 0.10,
    "biweekly": 0.15,
    "weekly": 0.20,
}

# ── Add-on flat fees ──────────────────────────────────────────────────────────

ADDON_RATES: dict[str, tuple[str, float]] = {
    "inside_fridge":      ("Inside fridge clean", 45.00),
    "inside_oven":        ("Inside oven clean", 35.00),
    "interior_windows":   ("Interior windows", 50.00),
    "laundry":            ("Laundry (wash + fold)", 40.00),
    "cabinets":           ("Interior cabinets", 60.00),
}

def _sqft_price(sqft: int) -> float:
    for max_sqft, rate in SQFT_TIERS:
        if sqft <= max_sqft:
            return sqft * rate
    return sqft * SQFT_TIERS[-1][1]


def calculate_quote(service: ServiceInfo) -> Quote:
    """
    Compute quote from a ServiceInfo object.
    Returns a Quote with total and itemised line items.
    """
    line_items: list[LineItem] = []

    # 1. Base rate
    base = BASE_RATES[service.serviceType]
    service_label = SERVICE_TYPE_LABELS[service.serviceType]
    line_items.append(LineItem(description=f"{service_label} (base)", amount=base))

    subtotal = base

    # 2. Bedroom / bathroom surcharges (preferred over sqft)
    if service.beds is not None or service.baths is not None:
        beds = service.beds or 1
        baths = service.baths or 1.0

        if beds > 1:
            bed_charge = (beds - 1) * BED_RATE
            line_items.append(
                LineItem(description=f"Additional bedrooms ({beds - 1} × ${BED_RATE:.0f})", amount=bed_charge)
            )
            subtotal += bed_charge

        if baths > 1:
            bath_charge = (baths - 1) * BATH_RATE
            line_items.append(
                LineItem(description=f"Additional bathrooms ({baths - 1} × ${BATH_RATE:.0f})", amount=bath_charge)
            )
            subtotal += bath_charge

    elif service.sqft is not None:
        sqft_price = _sqft_price(service.sqft)
        line_items.append(
            LineItem(description=f"Size-based pricing ({service.sqft:,} sqft)", amount=sqft_price)
        )
        subtotal += sqft_price

    # 3. Add-ons
    for addon_key in (service.addons or []):
        if addon_key in ADDON_RATES:
            label, fee = ADDON_RATES[addon_key]
            line_items.append(LineItem(description=label, amount=fee))
            subtotal += fee

    # 4. Frequency discount
    discount_pct = FREQUENCY_DISCOUNTS.get(service.frequency, 0.0)
    if discount_pct > 0:
        discount_amount = round(subtotal * discount_pct, 2)
        freq_label = FREQUENCY_LABELS[service.frequency]
        line_items.append(
            LineItem(
                description=f"{freq_label} discount (−{int(discount_pct * 100)}%)",
                amount=-discount_amount,
            )
        )
        subtotal -= discount_amount

    total = round(subtotal, 2)

    return Quote(currency="USD", total=total, lineItems=line_items)
