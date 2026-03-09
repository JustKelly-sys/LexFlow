"""Alert formatting and delivery system."""
import asyncio
from datetime import datetime, timedelta
from telegram import Bot
from loguru import logger
from ..models import ArbitrageOpportunity, UserTier
from ..cache.redis_client import RedisCache
from ..config import settings


class AlertSystem:
    """Manages alert delivery to Telegram users."""
    
    def __init__(self, bot: Bot, cache: RedisCache):
        self.bot = bot
        self.cache = cache
    
    async def start_alert_loop(self):
        """Continuously poll Redis for new arbitrage opportunities and send alerts."""
        logger.info("Starting alert delivery loop...")
        
        while True:
            try:
                # Get top arbitrage opportunities from Redis
                opportunities = await self.cache.get_top_arbitrages(limit=10)
                
                for opp in opportunities:
                    await self.process_opportunity(opp)
                
                # Wait before next check
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error in alert loop: {e}")
                await asyncio.sleep(10)
    
    async def process_opportunity(self, opportunity: ArbitrageOpportunity):
        """Process and send alerts for an arbitrage opportunity."""
        # Get all subscribed users (this is simplified - in production would query DB)
        # For now, we'll send to users who have interacted with the bot
        
        # Format alert message
        message = self.format_alert(opportunity)
        
        # Send to users based on tier (simplified for MVP)
        # In production, would iterate through user database
        logger.info(f"Alert ready: {opportunity.market.name} ({opportunity.net_profit_pct:.2f}%)")
    
    async def send_alert(self, telegram_id: int, opportunity: ArbitrageOpportunity, tier: UserTier):
        """Send alert to a specific user based on their tier."""
        try:
            # Check tier and apply delay
            delay_seconds = self.get_delay_for_tier(tier)
            
            if delay_seconds > 0:
                # Free tier - delay alert
                await asyncio.sleep(delay_seconds)
            
            # Format and send message
            message = self.format_alert(opportunity)
            await self.bot.send_message(chat_id=telegram_id, text=message, parse_mode="Markdown")
            
            # Add to user history
            await self.cache.add_to_history(telegram_id, opportunity.market.market_id)
            
            logger.info(f"Alert sent to {telegram_id} (tier: {tier.value})")
            
        except Exception as e:
            logger.error(f"Failed to send alert to {telegram_id}: {e}")
    
    def format_alert(self, opp: ArbitrageOpportunity) -> str:
        """Format arbitrage opportunity as Telegram message."""
        message = (
            " *ARBITRAGE OPPORTUNITY*\n\n"
            f" *Market:* {opp.market.name}\n"
            f" *Category:* {opp.market.category.value.title()}\n"
            f" *Profit:* {opp.net_profit_pct:.2f}% (${opp.net_profit_usd_per_1k:.2f} per $1,000)\n"
            f" *Sum of YES prices:* {opp.sum_of_prices:.3f}\n"
            f" *Detected:* {self.time_ago(opp.detected_at)}\n\n"
            f" [Trade on Polymarket]({opp.market.url})\n\n"
            f" *Strategy:* Sell YES on all outcomes\n"
            f" *Fees:* ~{opp.fees_total_pct:.1f}% (already accounted for in profit)"
        )
        
        return message
    
    def get_delay_for_tier(self, tier: UserTier) -> int:
        """Get alert delay in seconds based on user tier."""
        delays = {
            UserTier.FREE: 1800,  # 30 minutes
            UserTier.PRO: 0,      # Instant
            UserTier.ELITE: 0,    # Instant
        }
        return delays.get(tier, 1800)
    
    def time_ago(self, dt: datetime) -> str:
        """Convert datetime to human-readable 'time ago' string."""
        now = datetime.utcnow()
        diff = now - dt
        
        if diff < timedelta(seconds=60):
            return f"{int(diff.total_seconds())}s ago"
        elif diff < timedelta(hours=1):
            return f"{int(diff.total_seconds() / 60)}m ago"
        elif diff < timedelta(days=1):
            return f"{int(diff.total_seconds() / 3600)}h ago"
        else:
            return f"{int(diff.days)}d ago"
