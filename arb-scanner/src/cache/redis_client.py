"""Redis caching layer for order book and alerts."""
import json
from typing import List
import redis.asyncio as redis
from loguru import logger
from ..config import settings
from ..models import ArbitrageOpportunity, Market


class RedisCache:
    """Redis client for caching and alert queue management."""
    
    def __init__(self):
        self.redis_url = settings.redis_url
        self.client = None
    
    async def connect(self):
        """Connect to Redis."""
        try:
            self.client = await redis.from_url(self.redis_url, decode_responses=True)
            await self.client.ping()
            logger.info(f"Connected to Redis: {self.redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def push_arbitrage(self, opportunity: ArbitrageOpportunity):
        """
        Add arbitrage opportunity to sorted set (ranked by profit).
        
        Args:
            opportunity: Detected arbitrage opportunity
        """
        key = "arbitrage:active"
        score = opportunity.net_profit_pct
        value = opportunity.model_dump_json()
        
        # Add to sorted set with TTL of 60 seconds
        await self.client.zadd(key, {value: score})
        await self.client.expire(key, 60)
        
        logger.debug(f"Pushed arbitrage to Redis: {opportunity.market.name} ({score:.2f}%)")
    
    async def get_top_arbitrages(self, limit: int = 10) -> List[ArbitrageOpportunity]:
        """
        Get top arbitrage opportunities sorted by profit.
        
        Args:
            limit: Maximum number of opportunities to return
            
        Returns:
            List of arbitrage opportunities
        """
        key = "arbitrage:active"
        
        # Get top N by score (descending)
        results = await self.client.zrevrange(key, 0, limit - 1)
        
        opportunities = []
        for result in results:
            try:
                data = json.loads(result)
                opportunities.append(ArbitrageOpportunity(**data))
            except Exception as e:
                logger.error(f"Failed to parse arbitrage from Redis: {e}")
        
        return opportunities
    
    async def store_user_tier(self, telegram_id: int, tier: str):
        """Store user subscription tier."""
        key = f"user:{telegram_id}:tier"
        await self.client.set(key, tier)
    
    async def get_user_tier(self, telegram_id: int) -> str:
        """Get user subscription tier."""
        key = f"user:{telegram_id}:tier"
        tier = await self.client.get(key)
        return tier or "free"
    
    async def add_to_history(self, telegram_id: int, market_id: str):
        """Add arbitrage to user history."""
        key = f"history:{telegram_id}"
        await self.client.lpush(key, market_id)
        await self.client.ltrim(key, 0, 49)  # Keep last 50
    
    async def get_history(self, telegram_id: int, limit: int = 10) -> List[str]:
        """Get user alert history."""
        key = f"history:{telegram_id}"
        return await self.client.lrange(key, 0, limit - 1)
    
    async def close(self):
        """Close Redis connection."""
        if self.client:
            await self.client.close()
            logger.info("Disconnected from Redis")
