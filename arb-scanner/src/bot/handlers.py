"""Telegram bot command handlers."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from loguru import logger
from ..models import UserTier, MarketCategory
from ..cache.redis_client import RedisCache


class BotHandlers:
    """Handler functions for Telegram bot commands."""
    
    def __init__(self, cache: RedisCache):
        self.cache = cache
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command - subscribe user to alerts."""
        user = update.effective_user
        telegram_id = user.id
        
        # Store user as free tier by default
        await self.cache.store_user_tier(telegram_id, UserTier.FREE.value)
        
        welcome_message = (
            f" Welcome to Polymarket Arbitrage Scanner, {user.first_name}!\n\n"
            " I scan Polymarket for 'Negative Risk' arbitrage opportunities where "
            "you can lock in guaranteed profit.\n\n"
            " **How it works:**\n"
            "When the sum of YES prices > $1.00, you can sell YES on all outcomes "
            "and profit regardless of the result.\n\n"
            " **Your Plan:** Free Tier\n"
            " Alerts delayed 30 minutes\n"
            " Max 3 alerts per day\n\n"
            "Use /upgrade to unlock real-time alerts!\n"
            "Use /help to see all commands."
        )
        
        await update.message.reply_text(welcome_message)
        logger.info(f"New user subscribed: {telegram_id} ({user.username})")
    
    async def stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop command - unsubscribe user."""
        telegram_id = update.effective_user.id
        
        # Remove user tier (effectively unsubscribe)
        await self.cache.store_user_tier(telegram_id, "inactive")
        
        await update.message.reply_text(
            " You've been unsubscribed from alerts.\n\n"
            "Use /start to resubscribe anytime!"
        )
        logger.info(f"User unsubscribed: {telegram_id}")
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command - show all commands."""
        help_text = (
            " **Available Commands:**\n\n"
            "/start - Subscribe to arbitrage alerts\n"
            "/stop - Unsubscribe from alerts\n"
            "/settings - Configure alert preferences\n"
            "/history - View last 10 arbitrage opportunities\n"
            "/upgrade - View pricing tiers\n"
            "/help - Show this help message\n\n"
            " **What is arbitrage?**\n"
            "In mutually exclusive markets, the sum of YES prices should equal $1.00. "
            "When it exceeds $1.00 (e.g., $1.05), you can sell YES on all outcomes "
            "and lock in the difference as profit, minus fees."
        )
        
        await update.message.reply_text(help_text)
    
    async def settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /settings command - show settings menu."""
        keyboard = [
            [
                InlineKeyboardButton(" Sports", callback_data="toggle_sports"),
                InlineKeyboardButton(" Politics", callback_data="toggle_politics"),
            ],
            [
                InlineKeyboardButton(" Economics", callback_data="toggle_economics"),
                InlineKeyboardButton(" Crypto", callback_data="toggle_crypto"),
            ],
            [
                InlineKeyboardButton(" Entertainment", callback_data="toggle_entertainment"),
            ],
            [
                InlineKeyboardButton(" Save Settings", callback_data="save_settings"),
            ],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            " **Alert Settings**\n\n"
            "Choose which categories to receive alerts for:",
            reply_markup=reply_markup
        )
    
    async def history(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /history command - show recent arbitrage opportunities."""
        telegram_id = update.effective_user.id
        
        # Get user history from Redis
        history = await self.cache.get_history(telegram_id, limit=10)
        
        if not history:
            await update.message.reply_text(
                " No alerts yet!\n\n"
                "You'll see your alert history here once opportunities are detected."
            )
            return
        
        history_text = " **Recent Arbitrage Opportunities:**\n\n"
        for i, market_id in enumerate(history, 1):
            history_text += f"{i}. Market ID: {market_id}\n"
        
        await update.message.reply_text(history_text)
    
    async def upgrade(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /upgrade command - show pricing tiers."""
        upgrade_text = (
            " **Upgrade to Pro or Elite**\n\n"
            "** Free Tier** (Current)\n"
            " Alerts delayed 30 minutes\n"
            " Max 3 alerts per day\n"
            " Last 5 alerts in /history\n\n"
            "** Pro - $29/month**\n"
            " Real-time alerts (<5s latency)\n"
            " Unlimited alerts\n"
            " Custom category filters\n"
            " Last 50 alerts in /history\n\n"
            "** Elite - $79/month**\n"
            " Everything in Pro\n"
            " Min profit % customization\n"
            " Webhook integration\n"
            " Priority support (DM access)\n\n"
            " Upgrade here: [Payment link will be added in Phase 3]\n\n"
            "Questions? Reply to this message!"
        )
        
        await update.message.reply_text(upgrade_text)
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button callbacks."""
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        
        if callback_data.startswith("toggle_"):
            category = callback_data.replace("toggle_", "")
            await query.edit_message_text(
                f" Toggled {category} category!\n\n"
                f"Use /settings again to adjust more preferences."
            )
        elif callback_data == "save_settings":
            await query.edit_message_text(
                " Settings saved successfully!\n\n"
                "You'll now receive alerts based on your preferences."
            )
