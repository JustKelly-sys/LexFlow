"""Fee and profit calculations for arbitrage opportunities."""
from ..config import settings
from ..models import Market, ArbitrageOpportunity


class ProfitCalculator:
    """Calculates arbitrage profits accounting for all fees and costs."""
    
    def __init__(self):
        self.taker_fee_pct = settings.taker_fee_pct
        self.gas_cost_usd = settings.gas_cost_usd
        self.slippage_buffer_pct = settings.slippage_buffer_pct
    
    def calculate_arbitrage(self, market: Market) -> ArbitrageOpportunity | None:
        """
        Calculate if a market has profitable arbitrage.
        
        For mutually exclusive outcomes, sum of YES prices should = $1.00.
        If sum > 1.00, we can sell YES on all outcomes for risk-free profit.
        
        Args:
            market: Market data with outcome prices
            
        Returns:
            ArbitrageOpportunity if profitable, None otherwise
        """
        # Sum all YES prices (best ask)
        sum_of_prices = sum(market.outcome_prices.values())
        
        # Gross profit before fees
        gross_profit_pct = (sum_of_prices - 1.0) * 100
        
        # Calculate total fees
        # 1. Taker fee (charged on each outcome)
        taker_fee_pct = self.taker_fee_pct
        
        # 2. Gas cost as percentage (assuming $1000 position size for estimation)
        gas_pct = (self.gas_cost_usd / 1000.0) * 100
        
        # 3. Slippage buffer
        slippage_pct = self.slippage_buffer_pct
        
        fees_total_pct = taker_fee_pct + gas_pct + slippage_pct
        
        # Net profit after all costs
        net_profit_pct = gross_profit_pct - fees_total_pct
        
        # Profit per $1000 invested
        net_profit_usd_per_1k = net_profit_pct * 10
        
        opportunity = ArbitrageOpportunity(
            market=market,
            sum_of_prices=sum_of_prices,
            gross_profit_pct=gross_profit_pct,
            net_profit_pct=net_profit_pct,
            net_profit_usd_per_1k=net_profit_usd_per_1k,
            fees_total_pct=fees_total_pct,
        )
        
        # Only return if profitable after fees AND meets minimum threshold
        if opportunity.is_profitable and net_profit_pct >= settings.profit_threshold_pct:
            return opportunity
        
        return None
