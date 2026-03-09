"""Run both scanner and Telegram bot concurrently."""
import asyncio
from loguru import logger
from src.config import settings
from src.polymarket.client import PolymarketClient
from src.scanner.detector import ArbitrageDetector
from src.cache.redis_client import RedisCache
from src.bot.bot import TelegramBot


async def run_scanner(cache: RedisCache):
    """Run the arbitrage scanner."""
    logger.info("Starting scanner component...")
    
    polymarket = PolymarketClient()
    detector = ArbitrageDetector()
    
    try:
        await polymarket.connect()
        
        async def handle_market_update(market):
            """Process market update and detect arbitrage."""
            opportunities = await detector.scan_markets([market])
            
            for opp in opportunities:
                await cache.push_arbitrage(opp)
                
                logger.success(
                    f" ARBITRAGE: {opp.market.name} | "
                    f"{opp.net_profit_pct:.2f}% | "
                    f"Sum: {opp.sum_of_prices:.3f}"
                )
        
        await polymarket.subscribe_to_markets(handle_market_update)
        
    except Exception as e:
        logger.error(f"Scanner error: {e}")
    finally:
        await polymarket.close()


async def main():
    """Run both scanner and bot concurrently."""
    logger.info(" Starting Polymarket Arbitrage Scanner + Telegram Bot")
    logger.info(f"Profit threshold: {settings.profit_threshold_pct}%")
    
    # Shared Redis cache
    cache = RedisCache()
    await cache.connect()
    
    # Create bot
    bot = TelegramBot()
    await bot.initialize()
    
    try:
        # Run scanner and bot concurrently
        await asyncio.gather(
            run_scanner(cache),
            bot.start(),
        )
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await cache.close()
        logger.info("Goodbye!")


if __name__ == "__main__":
    # Configure logging
    logger.add(
        "logs/app.log",
        rotation="100 MB",
        retention="7 days",
        level=settings.log_level
    )
    
    asyncio.run(main())
