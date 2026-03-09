"""Main application entry point for arbitrage scanner."""
import asyncio
from loguru import logger
from src.config import settings
from src.polymarket.client import PolymarketClient
from src.scanner.detector import ArbitrageDetector
from src.cache.redis_client import RedisCache


async def main():
    """Run the arbitrage scanner."""
    logger.info("Starting Polymarket Arbitrage Scanner...")
    logger.info(f"Profit threshold: {settings.profit_threshold_pct}%")
    logger.info(f"Scan interval: {settings.scan_interval_seconds}s")
    
    # Initialize components
    polymarket = PolymarketClient()
    detector = ArbitrageDetector()
    cache = RedisCache()
    
    try:
        # Connect to Redis
        await cache.connect()
        
        # Connect to Polymarket
        await polymarket.connect()
        
        logger.info("All systems online. Scanning for arbitrage opportunities...")
        
        # Subscribe to market updates
        async def handle_market_update(market):
            """Process market update and detect arbitrage."""
            opportunities = await detector.scan_markets([market])
            
            for opp in opportunities:
                # Push to Redis for Telegram bot to consume
                await cache.push_arbitrage(opp)
                
                logger.success(
                    f" ARBITRAGE DETECTED\n"
                    f"   Market: {opp.market.name}\n"
                    f"   Profit: {opp.net_profit_pct:.2f}% (${opp.net_profit_usd_per_1k:.2f} per $1k)\n"
                    f"   Sum: {opp.sum_of_prices:.3f}\n"
                    f"   URL: {opp.market.url}"
                )
        
        # Start listening
        await polymarket.subscribe_to_markets(handle_market_update)
        
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
    finally:
        # Cleanup
        await polymarket.close()
        await cache.close()
        logger.info("Scanner stopped.")


if __name__ == "__main__":
    # Configure logging
    logger.add(
        "logs/scanner.log",
        rotation="100 MB",
        retention="7 days",
        level=settings.log_level
    )
    
    # Run scanner
    asyncio.run(main())
