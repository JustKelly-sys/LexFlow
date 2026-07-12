"""
South African Tax Calculation Engine (SARS 2024/25)

Pure functions -- no side effects, no external dependencies.
Add new jurisdictions by adding new calculate_paye_<jurisdiction>() functions.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class TaxResult:
    paye_annual: float
    paye_monthly: float
    effective_rate_pct: float
    marginal_rate_pct: float
    rebate_applied: float
    uif_monthly: float
    sdl_monthly: float
    net_annual: float
    net_monthly: float


# SARS 2024/25 Tax Tables
_ZA_BRACKETS = [
    # (lower_bound, upper_bound, base_tax, marginal_rate)
    (0,          237_100,    0,        0.18),
    (237_101,    370_500,    42_678,   0.26),
    (370_501,    512_800,    77_362,   0.31),
    (512_801,    673_000,    121_475,  0.36),
    (673_001,    857_900,    179_147,  0.39),
    (857_901,  1_817_000,    251_258,  0.41),
    (1_817_001, float("inf"), 644_489, 0.45),
]

_ZA_PRIMARY_REBATE = 17_235.0     # 2024/25
_ZA_SECONDARY_REBATE = 9_444.0    # age 65+
_ZA_TERTIARY_REBATE = 3_145.0     # age 75+

_ZA_UIF_RATE = 0.01               # 1% employee contribution
_ZA_UIF_MONTHLY_CEILING = 177.12  # 2024/25 cap

_ZA_SDL_RATE = 0.01               # 1% of payroll (employer-paid, shown for reference)


def _za_gross_tax(annual_gross: float) -> tuple[float, float]:
    """Return (gross_tax_before_rebates, marginal_rate_pct)."""
    for lower, upper, base, rate in _ZA_BRACKETS:
        if annual_gross <= upper:
            return base + (annual_gross - lower) * rate, rate * 100
    last = _ZA_BRACKETS[-1]
    return last[2] + (annual_gross - last[0]) * last[3], last[3] * 100


def calculate_paye_za(
    annual_gross: float,
    age: int = 30,
    include_uif: bool = True,
) -> TaxResult:
    """Calculate employee PAYE, UIF, SDL for a ZA employee (2024/25 tax year).

    Raises:
        ValueError: If annual_gross is negative or age is outside 0-120.
    """
    if annual_gross < 0:
        raise ValueError(f"annual_gross must be >= 0, got {annual_gross}")
    if not (0 < age <= 120):
        raise ValueError(f"age must be between 1 and 120, got {age}")

    gross_tax, marginal_rate = _za_gross_tax(annual_gross)

    rebate = _ZA_PRIMARY_REBATE
    if age >= 65:
        rebate += _ZA_SECONDARY_REBATE
    if age >= 75:
        rebate += _ZA_TERTIARY_REBATE

    paye_annual = max(0.0, gross_tax - rebate)
    paye_monthly = paye_annual / 12
    effective_rate = (paye_annual / annual_gross * 100) if annual_gross > 0 else 0.0

    monthly_gross = annual_gross / 12
    uif_monthly = min(_ZA_UIF_MONTHLY_CEILING, monthly_gross * _ZA_UIF_RATE)
    sdl_monthly = monthly_gross * _ZA_SDL_RATE

    net_monthly = monthly_gross - paye_monthly - uif_monthly
    net_annual = net_monthly * 12

    return TaxResult(
        paye_annual=round(paye_annual, 2),
        paye_monthly=round(paye_monthly, 2),
        effective_rate_pct=round(effective_rate, 2),
        marginal_rate_pct=round(marginal_rate, 2),
        rebate_applied=round(rebate, 2),
        uif_monthly=round(uif_monthly, 2),
        sdl_monthly=round(sdl_monthly, 2),
        net_annual=round(net_annual, 2),
        net_monthly=round(net_monthly, 2),
    )


def calculate_uif_za(monthly_gross: float) -> float:
    """Return employee UIF contribution for the month.

    Raises:
        ValueError: If monthly_gross is negative.
    """
    if monthly_gross < 0:
        raise ValueError(f"monthly_gross must be >= 0, got {monthly_gross}")
    return round(min(_ZA_UIF_MONTHLY_CEILING, monthly_gross * _ZA_UIF_RATE), 2)


ZA_BRACKETS_SUMMARY = [
    {"bracket": "R0 - R237,100",         "rate": "18%"},
    {"bracket": "R237,101 - R370,500",   "rate": "26%"},
    {"bracket": "R370,501 - R512,800",   "rate": "31%"},
    {"bracket": "R512,801 - R673,000",   "rate": "36%"},
    {"bracket": "R673,001 - R857,900",   "rate": "39%"},
    {"bracket": "R857,901 - R1,817,000", "rate": "41%"},
    {"bracket": "R1,817,001+",           "rate": "45%"},
]

