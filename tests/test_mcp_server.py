"""Tests for Dedukto MCP server tools."""
import importlib
import pytest


def test_server_module_importable():
    """The MCP server module must import without error."""
    mod = importlib.import_module("dedukto_mcp.server")
    assert hasattr(mod, "mcp")


def test_server_has_calculate_paye_tool():
    """MCP server must expose calculate_paye as a callable."""
    mod = importlib.import_module("dedukto_mcp.server")
    assert callable(getattr(mod, "calculate_paye", None))


def test_server_has_calculate_net_pay_tool():
    """MCP server must expose calculate_net_pay as a callable."""
    mod = importlib.import_module("dedukto_mcp.server")
    assert callable(getattr(mod, "calculate_net_pay", None))


def test_server_has_list_tax_brackets_tool():
    """MCP server must expose list_tax_brackets as a callable."""
    mod = importlib.import_module("dedukto_mcp.server")
    assert callable(getattr(mod, "list_tax_brackets", None))


def test_calculate_paye_tool_returns_correct_structure():
    """calculate_paye must return a dict with all required keys."""
    from dedukto_mcp.server import calculate_paye
    result = calculate_paye(gross_income=600_000, jurisdiction="ZA", age=30)
    required_keys = {
        "jurisdiction", "currency", "gross_annual", "gross_monthly",
        "paye_annual", "paye_monthly", "effective_rate_pct",
        "marginal_rate_pct", "rebate_applied", "uif_monthly",
        "sdl_monthly_employer", "net_annual", "net_monthly", "tax_year",
    }
    assert required_keys.issubset(result.keys())
    assert result["jurisdiction"] == "ZA"
    assert result["currency"] == "ZAR"
    assert result["tax_year"] == "2024/25"
    assert result["paye_annual"] > 0
    assert result["net_monthly"] > 0


def test_calculate_paye_tool_unsupported_jurisdiction():
    """calculate_paye must raise ValueError for unsupported jurisdictions."""
    from dedukto_mcp.server import calculate_paye
    with pytest.raises(ValueError, match="Unsupported jurisdiction"):
        calculate_paye(gross_income=600_000, jurisdiction="UK")


def test_calculate_net_pay_tool():
    """calculate_net_pay must return net_monthly rounded correctly."""
    from dedukto_mcp.server import calculate_net_pay
    result = calculate_net_pay(gross_monthly=50_000, jurisdiction="ZA")
    assert "net_monthly" in result
    assert result["gross_monthly"] == 50_000
    assert result["net_monthly"] < 50_000  # deductions must reduce take-home


def test_list_tax_brackets_returns_seven_brackets():
    """list_tax_brackets must return all 7 SARS 2024/25 brackets."""
    from dedukto_mcp.server import list_tax_brackets
    result = list_tax_brackets(jurisdiction="ZA")
    assert result["tax_year"] == "2024/25"
    assert len(result["brackets"]) == 7
    assert result["primary_rebate"] == 17_235.0
