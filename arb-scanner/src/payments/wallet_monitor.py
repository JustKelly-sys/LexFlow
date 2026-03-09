"""Multi-chain wallet payment monitoring for USDC, SOL, ETH, MATIC."""
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Callable
from loguru import logger
from ..config import settings
from ..models import UserTier


# Supported payment methods
PAYMENT_METHODS = {
    "usdc_polygon": {
        "name": "USDC (Polygon)",
        "symbol": "USDC",
        "chain": "polygon",
        "contract": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",  # USDC on Polygon
        "decimals": 6,
    },
    "usdc_eth": {
        "name": "USDC (Ethereum)",
        "symbol": "USDC",
        "chain": "ethereum",
        "contract": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "decimals": 6,
    },
    "eth": {
        "name": "ETH",
        "symbol": "ETH",
        "chain": "ethereum",
        "contract": None,  # Native token
        "decimals": 18,
    },
    "matic": {
        "name": "MATIC (Polygon)",
        "symbol": "MATIC",
        "chain": "polygon",
        "contract": None,  # Native token
        "decimals": 18,
    },
    "sol": {
        "name": "SOL",
        "symbol": "SOL",
        "chain": "solana",
        "contract": None,  # Native token
        "decimals": 9,
    },
    "usdc_sol": {
        "name": "USDC (Solana)",
        "symbol": "USDC",
        "chain": "solana",
        "contract": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC on Solana
        "decimals": 6,
    },
}

# Pricing in USD
TIER_PRICES = {
    "pro": 29,
    "elite": 79,
}


class WalletMonitor:
    """Monitors wallet addresses for incoming payments."""
    
    def __init__(self):
        # Your payment wallet addresses
        self.wallets = {
            "polygon": settings.payment_wallet_polygon,
            "ethereum": settings.payment_wallet_ethereum, 
            "solana": settings.payment_wallet_solana,
        }
        
        # Pending payments: {telegram_id: {tier, amount, expires_at, payment_method}}
        self.pending_payments = {}
        
        # Processed transaction hashes (avoid double-processing)
        self.processed_txs = set()
        
        # Callback when payment confirmed
        self.on_payment_confirmed: Callable = None
    
    def create_payment_request(
        self, 
        telegram_id: int, 
        tier: str,
        payment_method: str = "usdc_polygon"
    ) -> dict:
        """
        Create a payment request for a user.
        
        Returns payment details including wallet address and amount.
        """
        method = PAYMENT_METHODS[payment_method]
        price_usd = TIER_PRICES[tier]
        
        # Get crypto amount (use live price API in production)
        amount = self._get_crypto_amount(price_usd, payment_method)
        
        # Store pending payment
        self.pending_payments[telegram_id] = {
            "tier": tier,
            "amount": amount,
            "amount_usd": price_usd,
            "payment_method": payment_method,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(hours=1),
        }
        
        wallet = self.wallets[method["chain"]]
        
        return {
            "wallet_address": wallet,
            "amount": amount,
            "symbol": method["symbol"],
            "chain": method["chain"],
            "expires_in": "1 hour",
            "telegram_id": telegram_id,
        }
    
    def _get_crypto_amount(self, usd_amount: float, payment_method: str) -> float:
        """Convert USD to crypto amount. Uses approximate prices for MVP."""
        # In production, fetch live prices from CoinGecko/etc
        prices = {
            "usdc_polygon": 1.0,
            "usdc_eth": 1.0,
            "usdc_sol": 1.0,
            "eth": 3500,      # Approximate ETH price
            "matic": 0.50,    # Approximate MATIC price
            "sol": 200,       # Approximate SOL price
        }
        
        crypto_price = prices.get(payment_method, 1.0)
        return round(usd_amount / crypto_price, 6)
    
    async def start_monitoring(self):
        """Start monitoring all wallets for incoming payments."""
        logger.info("Starting wallet payment monitor...")
        
        while True:
            try:
                # Check each chain
                await asyncio.gather(
                    self._check_polygon_payments(),
                    self._check_ethereum_payments(),
                    self._check_solana_payments(),
                )
                
                # Clean up expired payments
                self._cleanup_expired()
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Wallet monitor error: {e}")
                await asyncio.sleep(60)
    
    async def _check_polygon_payments(self):
        """Check Polygon for USDC and MATIC payments."""
        wallet = self.wallets.get("polygon")
        if not wallet:
            return
        
        # Use Polygonscan API
        api_url = f"https://api.polygonscan.com/api"
        
        # Check MATIC transfers
        async with aiohttp.ClientSession() as session:
            # Get recent transactions
            params = {
                "module": "account",
                "action": "txlist",
                "address": wallet,
                "startblock": 0,
                "endblock": 99999999,
                "page": 1,
                "offset": 20,
                "sort": "desc",
                "apikey": settings.polygonscan_api_key or "",
            }
            
            async with session.get(api_url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("status") == "1":
                        for tx in data.get("result", []):
                            await self._process_transaction(tx, "polygon")
    
    async def _check_ethereum_payments(self):
        """Check Ethereum for USDC and ETH payments."""
        wallet = self.wallets.get("ethereum")
        if not wallet:
            return
        
        # Use Etherscan API (similar to Polygon)
        # Implementation similar to _check_polygon_payments
        pass
    
    async def _check_solana_payments(self):
        """Check Solana for USDC and SOL payments."""
        wallet = self.wallets.get("solana")
        if not wallet:
            return
        
        # Use Helius or Solana RPC
        # Implementation for Solana transaction monitoring
        pass
    
    async def _process_transaction(self, tx: dict, chain: str):
        """Process a detected transaction."""
        tx_hash = tx.get("hash")
        
        # Skip if already processed
        if tx_hash in self.processed_txs:
            return
        
        # Get transaction details
        from_address = tx.get("from", "").lower()
        value_wei = int(tx.get("value", 0))
        
        # Convert to amount
        decimals = 18 if chain == "polygon" else 18  # MATIC/ETH
        amount = value_wei / (10 ** decimals)
        
        # Find matching pending payment
        matching_user = self._find_matching_payment(amount, chain)
        
        if matching_user:
            telegram_id = matching_user
            pending = self.pending_payments[telegram_id]
            
            logger.success(
                f" Payment confirmed! "
                f"User: {telegram_id} | "
                f"Amount: {amount} | "
                f"Tier: {pending['tier']} | "
                f"TX: {tx_hash[:16]}..."
            )
            
            # Mark as processed
            self.processed_txs.add(tx_hash)
            
            # Trigger callback
            if self.on_payment_confirmed:
                await self.on_payment_confirmed(
                    telegram_id=telegram_id,
                    tier=pending["tier"],
                    amount=amount,
                    tx_hash=tx_hash,
                    chain=chain,
                    from_address=from_address,
                )
            
            # Remove from pending
            del self.pending_payments[telegram_id]
    
    def _find_matching_payment(self, amount: float, chain: str) -> int | None:
        """Find pending payment that matches the received amount."""
        now = datetime.utcnow()
        
        for telegram_id, pending in self.pending_payments.items():
            # Check chain matches
            method = PAYMENT_METHODS[pending["payment_method"]]
            if method["chain"] != chain:
                continue
            
            # Check if expired
            if pending["expires_at"] < now:
                continue
            
            # Check amount (allow 1% tolerance for price fluctuation)
            expected = pending["amount"]
            tolerance = expected * 0.01
            
            if abs(amount - expected) <= tolerance:
                return telegram_id
        
        return None
    
    def _cleanup_expired(self):
        """Remove expired pending payments."""
        now = datetime.utcnow()
        expired = [
            tid for tid, p in self.pending_payments.items()
            if p["expires_at"] < now
        ]
        
        for tid in expired:
            logger.info(f"Payment expired for user {tid}")
            del self.pending_payments[tid]
