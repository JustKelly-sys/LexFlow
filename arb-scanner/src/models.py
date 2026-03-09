"""Pydantic data models for the scanner."""
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class MarketCategory(str, Enum):
    """Market category types."""
    SPORTS = "sports"
    POLITICS = "politics"
    ECONOMICS = "economics"
    CRYPTO = "crypto"
    ENTERTAINMENT = "entertainment"
    OTHER = "other"


class Market(BaseModel):
    """Polymarket market data."""
    market_id: str
    name: str
    category: MarketCategory = MarketCategory.OTHER
    outcomes: list[str]
    outcome_prices: dict[str, float]  # outcome -> best_ask price
    liquidity_usd: float = 0.0
    volume_24h: float = 0.0
    url: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ArbitrageOpportunity(BaseModel):
    """Detected arbitrage opportunity."""
    market: Market
    sum_of_prices: float
    gross_profit_pct: float
    net_profit_pct: float
    net_profit_usd_per_1k: float
    fees_total_pct: float
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def is_profitable(self) -> bool:
        """Check if opportunity is profitable after all costs."""
        return self.net_profit_pct > 0


class UserTier(str, Enum):
    """Subscription tier levels."""
    FREE = "free"
    PRO = "pro"
    ELITE = "elite"


class User(BaseModel):
    """Telegram user subscription data."""
    telegram_id: int
    tier: UserTier = UserTier.FREE
    filters: set[MarketCategory] = Field(default_factory=set)
    min_profit_pct: float = 1.0
    subscribed_at: datetime = Field(default_factory=datetime.utcnow)
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
