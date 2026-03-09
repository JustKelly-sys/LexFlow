"""Updated upgrade command with crypto payment options."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from ..payments.wallet_monitor import WalletMonitor, PAYMENT_METHODS, TIER_PRICES


async def upgrade_with_crypto(update: Update, context: ContextTypes.DEFAULT_TYPE, wallet_monitor: WalletMonitor):
    """Handle /upgrade command - show crypto payment options."""
    telegram_id = update.effective_user.id
    
    keyboard = [
        [InlineKeyboardButton(" Pro - $29/mo", callback_data="pay_pro")],
        [InlineKeyboardButton(" Elite - $79/mo", callback_data="pay_elite")],
    ]
    
    await update.message.reply_text(
        " *Upgrade Your Plan*\n\n"
        "*Current:* Free Tier\n\n"
        "Choose a plan to upgrade:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def handle_payment_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, wallet_monitor: WalletMonitor):
    """Handle tier selection - show payment method options."""
    query = update.callback_query
    await query.answer()
    
    tier = query.data.replace("pay_", "")  # "pro" or "elite"
    
    keyboard = [
        [InlineKeyboardButton(" USDC (Polygon)", callback_data=f"method_{tier}_usdc_polygon")],
        [InlineKeyboardButton(" USDC (Ethereum)", callback_data=f"method_{tier}_usdc_eth")],
        [InlineKeyboardButton(" USDC (Solana)", callback_data=f"method_{tier}_usdc_sol")],
        [InlineKeyboardButton(" ETH", callback_data=f"method_{tier}_eth")],
        [InlineKeyboardButton(" MATIC", callback_data=f"method_{tier}_matic")],
        [InlineKeyboardButton(" SOL", callback_data=f"method_{tier}_sol")],
        [InlineKeyboardButton(" Back", callback_data="upgrade_back")],
    ]
    
    price = TIER_PRICES[tier]
    
    await query.edit_message_text(
        f" *{tier.title()} Plan - ${price}/month*\n\n"
        "Choose payment method:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def handle_method_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, wallet_monitor: WalletMonitor):
    """Handle payment method selection - show wallet address."""
    query = update.callback_query
    await query.answer()
    
    # Parse: method_{tier}_{payment_method}
    parts = query.data.split("_", 2)
    tier = parts[1]
    payment_method = parts[2]
    
    telegram_id = update.effective_user.id
    
    # Create payment request
    payment = wallet_monitor.create_payment_request(
        telegram_id=telegram_id,
        tier=tier,
        payment_method=payment_method,
    )
    
    method = PAYMENT_METHODS[payment_method]
    
    # Format address for easy copying
    wallet = payment["wallet_address"]
    amount = payment["amount"]
    symbol = payment["symbol"]
    chain = payment["chain"].title()
    
    message = (
        f" *Payment Instructions*\n\n"
        f"*Plan:* {tier.title()}\n"
        f"*Amount:* `{amount}` {symbol}\n"
        f"*Network:* {chain}\n\n"
        f"*Send to this address:*\n"
        f"`{wallet}`\n\n"
        f" *Expires in:* 1 hour\n\n"
        f" *Important:*\n"
        f" Send exact amount: `{amount}` {symbol}\n"
        f" Use {chain} network only\n"
        f" You'll be upgraded automatically within 2 minutes\n\n"
        f" After payment, I'll notify you once confirmed!"
    )
    
    keyboard = [
        [InlineKeyboardButton(" Check Payment Status", callback_data=f"check_payment_{telegram_id}")],
        [InlineKeyboardButton(" Choose Different Method", callback_data=f"pay_{tier}")],
    ]
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
