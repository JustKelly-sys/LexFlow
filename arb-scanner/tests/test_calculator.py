"""Unit tests for profit calculator."""
import pytest
from src.models import Market,MarketCategory
from src.scanner.calculator import ProfitCalculator


@pytest.fixture
def calculator():
    return ProfitCalculator()


@pytest.fixture
def sample_market():
    """Market with profitable arbitrage (sum = 1.05)."""
    return Market(
        market_id="test_123",
        name="Test Market",
        outcomes=["YES", "NO"],
        outcome_prices={"YES": 0.52, "NO": 0.53},  # Sum = 1.05
        url="https://polymarket.com/event/test"
    )


@pytest.fixture
def unprofitable_market():
    """Market with no arbitrage (sum = 1.00)."""
    return Market(
        market_id="test_456",
        name="No Arb Market",
        outcomes=["YES", "NO"],
        outcome_prices={"YES": 0.50, "NO": 0.50},
        url="https://polymarket.com/event/test2"
    )


def test_profitable_arbitrage(calculator, sample_market):
    """Test detection of profitable arbitrage."""
    opportunity = calculator.calculate_arbitrage(sample_market)
    
    assert opportunity is not None
    assert opportunity.sum_of_prices == 1.05
    assert opportunity.gross_profit_pct == 5.0
    assert opportunity.net_profit_pct > 0
    assert opportunity.is_profitable


def test_unprofitable_arbitrage(calculator, unprofitable_market):
    """Test rejection of unprofitable arbitrage."""
    opportunity = calculator.calculate_arbitrage(unprofitable_market)
    
    assert opportunity is None


def test_fee_calculations(calculator, sample_market):
    """Test that fees are properly accounted for."""
    opportunity = calculator.calculate_arbitrage(sample_market)
    
    # Should account for: 2% taker fee + gas (0.5%) + slippage (0.5%) = 3%
    assert opportunity.fees_total_pct >= 2.5
    assert opportunity.net_profit_pct < opportunity.gross_profit_pct


def test_minimum_threshold(calculator):
    """Test that opportunities below threshold are rejected."""
    # Create market with tiny profit (sum = 1.005, only 0.5% gross)
    low_profit_market = Market(
        market_id="test_789",
        name="Low Profit Market",
        outcomes=["YES", "NO"],
        outcome_prices={"YES": 0.5025, "NO": 0.5025},
        url="https://polymarket.com/event/test3"
    )
    
    opportunity = calculator.calculate_arbitrage(low_profit_market)
    
    # Should be rejected even though technically profitable
    # because net profit after 3% fees would be negative
    assert opportunity is None
