"""
Dedukto MCP Server

Exposes South African payroll calculation as MCP tools.
Any MCP-compatible AI agent can call these tools without
reimplementing the SARS tax logic.

Run:
    python -m dedukto_mcp.server
"""
from mcp.server.fastmcp import FastMCP
from dedukto_mcp.tax_engine import (
    calculate_paye_za,
    calculate_uif_za,
    ZA_BRACKETS_SUMMARY,
)

mcp = FastMCP("Dedukto Payroll Engine")


@mcp.tool()
def calculate_paye(gross_income: float, jurisdiction: str = "ZA", age: int = 30) -> dict:
    """
    Calculate PAYE, UIF, SDL and net pay for an employee.

    Args:
        gross_income: Annual gross income in the local currency.
        jurisdiction: Tax jurisdiction code. Currently supported: 'ZA' (South Africa).
        age: Employee age (affects rebate tier in ZA).

    Returns:
        Dictionary with paye_annual, paye_monthly, effective_rate_pct,
        marginal_rate_pct, uif_monthly, sdl_monthly, net_monthly, net_annual.
    """
    if jurisdiction.upper() == "ZA":
        result = calculate_paye_za(annual_gross=gross_income, age=age)
        return {
            "jurisdiction": "ZA",
            "currency": "ZAR",
            "gross_annual": gross_income,
            "gross_monthly": round(gross_income / 12, 2),
            "paye_annual": result.paye_annual,
            "paye_monthly": result.paye_monthly,
            "effective_rate_pct": result.effective_rate_pct,
            "marginal_rate_pct": result.marginal_rate_pct,
            "rebate_applied": result.rebate_applied,
            "uif_monthly": result.uif_monthly,
            "sdl_monthly_employer": result.sdl_monthly,
            "net_annual": result.net_annual,
            "net_monthly": result.net_monthly,
            "tax_year": "2024/25",
        }
    raise ValueError(f"Unsupported jurisdiction: {jurisdiction}. Supported: ZA")


@mcp.tool()
def calculate_net_pay(gross_monthly: float, jurisdiction: str = "ZA", age: int = 30) -> dict:
    """
    Calculate monthly net pay from a monthly gross amount.

    Args:
        gross_monthly: Monthly gross income in local currency.
        jurisdiction: Tax jurisdiction code. Currently supported: 'ZA'.
        age: Employee age.

    Returns:
        Dictionary with gross_monthly, paye_monthly, uif_monthly, net_monthly.
    """
    annual = gross_monthly * 12
    result = calculate_paye(gross_income=annual, jurisdiction=jurisdiction, age=age)
    return {
        "jurisdiction": result["jurisdiction"],
        "currency": result["currency"],
        "gross_monthly": gross_monthly,
        "paye_monthly": result["paye_monthly"],
        "uif_monthly": result["uif_monthly"],
        "net_monthly": result["net_monthly"],
        "effective_rate_pct": result["effective_rate_pct"],
    }


@mcp.tool()
def list_tax_brackets(jurisdiction: str = "ZA") -> dict:
    """
    Return the income tax brackets for a given jurisdiction.

    Args:
        jurisdiction: Tax jurisdiction code. Currently supported: 'ZA'.

    Returns:
        Dictionary with tax_year, jurisdiction, and a list of bracket objects.
    """
    if jurisdiction.upper() == "ZA":
        return {
            "jurisdiction": "ZA",
            "tax_year": "2024/25",
            "primary_rebate": 17_235.0,
            "brackets": ZA_BRACKETS_SUMMARY,
        }
    raise ValueError(f"Unsupported jurisdiction: {jurisdiction}. Supported: ZA")


if __name__ == "__main__":
    mcp.run()

