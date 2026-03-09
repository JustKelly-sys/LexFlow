"""Main arbitrage detection engine."""
import asyncio
from loguru import logger
from ..models import Market, ArbitrageOpportunity
from .calculator import ProfitCalculator
from ..config import settings


class ArbitrageDetector:
    """Scans markets and detects arbitrage opportunities."""
    
    def __init__(self):
        self.calculator = ProfitCalculator()
        self.scan_interval = settings.scan_interval_seconds
    
    async def scan_markets(self, markets: list[Market]) -> list[ArbitrageOpportunity]:
        """
        Scan all markets for arbitrage opportunities.
        
        Args:
            markets: List of markets to scan
            
        Returns:
            List of profitable arbitrage opportunities
        """
        opportunities = []
        
        for market in markets:
            # Only scan markets with mutually exclusive outcomes
            if not self._is_mutually_exclusive(market):
                continue
            
            # Calculate arbitrage
            opportunity = self.calculator.calculate_arbitrage(market)
            
            if opportunity:
                logger.info(
                    f"Arbitrage found: {market.name} | "
                    f"Profit: {opportunity.net_profit_pct:.2f}% | "
                    f"Sum: {opportunity.sum_of_prices:.3f}"
                )
                opportunities.append(opportunity)
        
        return opportunities
    
    def _is_mutually_exclusive(self, market: Market) -> bool:
        """
        Check if market has mutually exclusive outcomes.
        
        For now, assume all markets are mutually exclusive.
        In practice, would need to check market metadata.
        """
        return len(market.outcomes) >= 2
