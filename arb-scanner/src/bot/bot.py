"""Telegram bot main entry point."""
import asyncio
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from loguru import logger
from ..config import settings
from ..cache.redis_client import RedisCache
from ..db.users import UserDatabase
from .handlers import BotHandlers
from .alerts import AlertSystem


class TelegramBot:
    """Main Telegram bot application."""
    
    def __init__(self):
        self.token = settings.telegram_bot_token
        self.cache = RedisCache()
        self.db = UserDatabase()
        self.app = None
        self.handlers = None
        self.alert_system = None
    
    async def initialize(self):
        """Initialize bot components."""
        logger.info("Initializing Telegram bot...")
        
        # Connect to Redis
        await self.cache.connect()
        
        # Initialize database
        await self.db.initialize()
        
        # Create bot application
        self.app = Application.builder().token(self.token).build()
        
        # Initialize handlers
        self.handlers = BotHandlers(self.cache)
        
        # Initialize alert system
        self.alert_system = AlertSystem(self.app.bot, self.cache)
        
        # Register command handlers
        self.app.add_handler(CommandHandler("start", self.handlers.start))
        self.app.add_handler(CommandHandler("stop", self.handlers.stop))
        self.app.add_handler(CommandHandler("help", self.handlers.help))
        self.app.add_handler(CommandHandler("settings", self.handlers.settings))
        self.app.add_handler(CommandHandler("history", self.handlers.history))
        self.app.add_handler(CommandHandler("upgrade", self.handlers.upgrade))
        
        # Register callback query handler for inline buttons
        self.app.add_handler(CallbackQueryHandler(self.handlers.button_callback))
        
        logger.info("Bot initialized successfully!")
    
    async def start(self):
        """Start the bot."""
        await self.initialize()
        
        logger.info("Starting Telegram bot...")
        
        # Start bot polling
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        
        # Start alert delivery loop in background
        alert_task = asyncio.create_task(self.alert_system.start_alert_loop())
        
        logger.success(" Telegram bot is now running!")
        
        try:
            # Keep running
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Shutting down bot...")
        finally:
            # Cleanup
            alert_task.cancel()
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
            await self.cache.close()


async def run_bot():
    """Entry point to run the bot."""
    bot = TelegramBot()
    await bot.start()


if __name__ == "__main__":
    # Configure logging
    logger.add(
        "logs/bot.log",
        rotation="100 MB",
        retention="7 days",
        level=settings.log_level
    )
    
    # Run bot
    asyncio.run(run_bot())
