"""Unit tests for Dedukto tax calculation engine (ZA jurisdiction)."""
import pytest
from dedukto_mcp.tax_engine import calculate_paye_za, calculate_uif_za, TaxResult


def test_paye_zero_for_below_threshold():
    """Very low income where gross tax < rebate = zero PAYE.
    At R80,000/yr: gross_tax = 80,000 * 0.18 = 14,400; rebate = 17,235 -> PAYE = 0."""
    result = calculate_paye_za(annual_gross=80_000)
    assert result.paye_annual == 0.0
    assert result.paye_monthly == 0.0


def test_paye_first_bracket():
    """R300,000 gross -- rebate (R17,235) exceeds gross tax so PAYE is still zero."""
    result = calculate_paye_za(annual_gross=300_000)
    assert result.paye_annual >= 0
    assert result.paye_monthly == pytest.approx(result.paye_annual / 12, abs=1)


def test_paye_second_bracket():
    """R600,000 annual gross falls in the 31% bracket and has positive PAYE."""
    result = calculate_paye_za(annual_gross=600_000)
    assert result.paye_annual > 0
    assert result.effective_rate_pct > 0


def test_paye_high_earner():
    """R2,000,000 annual gross hits 45% marginal rate."""
    result = calculate_paye_za(annual_gross=2_000_000)
    assert result.marginal_rate_pct == 45.0
    assert result.paye_annual > 0


def test_uif_capped_at_ceiling():
    """UIF is 1% of gross, capped at R177.12/month (2024/25)."""
    result = calculate_uif_za(monthly_gross=50_000)
    assert result == pytest.approx(177.12, abs=0.5)


def test_uif_below_ceiling():
    """For monthly gross < R17,712, UIF = 1% of gross."""
    result = calculate_uif_za(monthly_gross=10_000)
    assert result == pytest.approx(100.0, abs=0.5)


def test_tax_result_has_all_fields():
    result = calculate_paye_za(annual_gross=500_000)
    assert hasattr(result, "paye_annual")
    assert hasattr(result, "paye_monthly")
    assert hasattr(result, "effective_rate_pct")
    assert hasattr(result, "marginal_rate_pct")
    assert hasattr(result, "rebate_applied")
    assert hasattr(result, "uif_monthly")
    assert hasattr(result, "net_monthly")
    assert hasattr(result, "net_annual")


def test_paye_net_monthly_equals_gross_minus_deductions():
    """net_monthly must equal gross_monthly - paye_monthly - uif_monthly."""
    result = calculate_paye_za(annual_gross=600_000)
    expected_net = (600_000 / 12) - result.paye_monthly - result.uif_monthly
    assert result.net_monthly == pytest.approx(expected_net, abs=0.05)


def test_age_65_gets_secondary_rebate():
    """A 65-year-old should pay less PAYE due to secondary rebate."""
    young = calculate_paye_za(annual_gross=400_000, age=40)
    senior = calculate_paye_za(annual_gross=400_000, age=65)
    assert senior.paye_annual < young.paye_annual



# -- SEC-4 + SEC-5: Input validation guards ----------------------------------

def test_paye_rejects_negative_income():
    """calculate_paye_za must raise ValueError for negative gross income."""
    with pytest.raises(ValueError, match="annual_gross"):
        calculate_paye_za(annual_gross=-1)


def test_paye_rejects_zero_age():
    """calculate_paye_za must raise ValueError for age <= 0."""
    with pytest.raises(ValueError, match="age"):
        calculate_paye_za(annual_gross=300_000, age=0)


def test_paye_rejects_unrealistic_age():
    """calculate_paye_za must raise ValueError for age > 120."""
    with pytest.raises(ValueError, match="age"):
        calculate_paye_za(annual_gross=300_000, age=150)


def test_uif_rejects_negative_gross():
    """calculate_uif_za must raise ValueError for negative monthly gross."""
    with pytest.raises(ValueError, match="monthly_gross"):
        calculate_uif_za(monthly_gross=-500)
