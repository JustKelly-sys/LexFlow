""\"Pydantic configuration settings loaded from environment variables.""\"
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ""\"Application configuration.""\"
    
    # Telegram
    telegram_bot_token: str
    
    # Redis
    redis_url: str = ""redis://localhost:6379""
    
    # OpenAI
    openai_api_key: str
    
    # Stripe (optional)
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    
    # Polymarket
    polymarket_ws_url: str = ""wss://ws-subscriptions.polymarket.com/ws/markets""
    polymarket_clob_url: str = ""https://clob.polymarket.com""
    
    # Scanner config
    profit_threshold_pct: float = 1.0
    scan_interval_seconds: int = 5
    taker_fee_pct: float = 2.0
    gas_cost_usd: float = 0.005
    slippage_buffer_pct: float = 0.5
    
    # Database
    db_path: str = ""./data/scanner.db""
    
    # Logging
    log_level: str = ""INFO""
    
    model_config = SettingsConfigDict(
        env_file="".env"",
        env_file_encoding=""utf-8"",
        case_sensitive=False,
    )


# Singleton instance
settings = Settings()

# Payment wallet addresses (add these to .env)
payment_wallet_polygon: str | None = None
payment_wallet_ethereum: str | None = None
payment_wallet_solana: str | None = None

# Blockchain API keys (optional but recommended)
polygonscan_api_key: str | None = None
etherscan_api_key: str | None = None
