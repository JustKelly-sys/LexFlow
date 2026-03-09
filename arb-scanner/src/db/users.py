"""User database management with SQLite."""
import sqlite3
import aiosqlite
from pathlib import Path
from loguru import logger
from ..models import User, UserTier, MarketCategory
from ..config import settings


class UserDatabase:
    """SQLite database for user subscriptions and preferences."""
    
    def __init__(self):
        self.db_path = Path(settings.db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        """Create database tables if they don't exist."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id INTEGER PRIMARY KEY,
                    tier TEXT NOT NULL DEFAULT 'free',
                    filters TEXT,
                    min_profit_pct REAL DEFAULT 1.0,
                    subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    stripe_customer_id TEXT,
                    stripe_subscription_id TEXT
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS alert_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    market_id TEXT NOT NULL,
                    profit_pct REAL,
                    alerted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
                )
            """)
            
            await db.commit()
            logger.info(f"Database initialized: {self.db_path}")
    
    async def create_user(self, telegram_id: int, tier: str = "free") -> User:
        """Create a new user or update existing."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO users (telegram_id, tier)
                VALUES (?, ?)
                ON CONFLICT(telegram_id) DO UPDATE SET tier = excluded.tier
                """,
                (telegram_id, tier)
            )
            await db.commit()
        
        return await self.get_user(telegram_id)
    
    async def get_user(self, telegram_id: int) -> User | None:
        """Get user by Telegram ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
            ) as cursor:
                row = await cursor.fetchone()
                
                if row:
                    # Parse filters (stored as comma-separated string)
                    filters_str = row["filters"] or ""
                    filters = set(filters_str.split(",")) if filters_str else set()
                    
                    return User(
                        telegram_id=row["telegram_id"],
                        tier=UserTier(row["tier"]),
                        filters={MarketCategory(f) for f in filters if f},
                        min_profit_pct=row["min_profit_pct"],
                        stripe_customer_id=row["stripe_customer_id"],
                        stripe_subscription_id=row["stripe_subscription_id"],
                    )
        
        return None
    
    async def update_tier(self, telegram_id: int, tier: str):
        """Update user subscription tier."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET tier = ? WHERE telegram_id = ?",
                (tier, telegram_id)
            )
            await db.commit()
    
    async def update_filters(self, telegram_id: int, filters: set[MarketCategory]):
        """Update user category filters."""
        filters_str = ",".join([f.value for f in filters])
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET filters = ? WHERE telegram_id = ?",
                (filters_str, telegram_id)
            )
            await db.commit()
    
    async def get_all_active_users(self) -> list[User]:
        """Get all users with active subscriptions (not 'inactive' tier)."""
        users = []
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE tier != 'inactive'"
            ) as cursor:
                async for row in cursor:
                    filters_str = row["filters"] or ""
                    filters = set(filters_str.split(",")) if filters_str else set()
                    
                    user = User(
                        telegram_id=row["telegram_id"],
                        tier=UserTier(row["tier"]),
                        filters={MarketCategory(f) for f in filters if f},
                        min_profit_pct=row["min_profit_pct"],
                    )
                    users.append(user)
        
        return users
    
    async def add_alert_history(self, telegram_id: int, market_id: str, profit_pct: float):
        """Add alert to user history."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO alert_history (telegram_id, market_id, profit_pct)
                VALUES (?, ?, ?)
                """,
                (telegram_id, market_id, profit_pct)
            )
            await db.commit()
