# Polymarket Arbitrage Scanner

A Telegram-first arbitrage scanner for Polymarket prediction markets.

## Quick Start

```powershell
# 1. Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env
# Edit .env with your API keys

# 4. Start Redis (using Docker)
docker run -d -p 6379:6379 redis:alpine

# 5. Run scanner
python main.py
```

## Project Structure

- `src/` - All source code
  - `config.py` - Environment configuration
  - `models.py` - Pydantic data models
  - `polymarket/` - Polymarket CLOB client
  - `scanner/` - Arbitrage detection logic
  - `cache/` - Redis caching layer
  - `bot/` - Telegram bot (coming in Phase 4)
  - `db/` - User database (coming in Phase 4)
- `tests/` - Unit tests
- `main.py` - Application entry point

## Testing

```powershell
# Run unit tests
pytest tests/ -v

# Test specific module
pytest tests/test_calculator.py -v
```

## How It Works

1. **Scanner** connects to Polymarket CLOB WebSocket
2. **Detector** analyzes markets for "Negative Risk" arbitrage
3. **Calculator** computes net profit after fees (2% + gas + slippage)
4. **Cache** stores opportunities in Redis (sorted by profit %)
5. **Bot** (Phase 4) delivers alerts to Telegram subscribers

## What is "Negative Risk" Arbitrage?

In mutually exclusive markets (e.g., "Who will win the election?"), the sum of all YES prices should equal $1.00. When retail traders push the sum above $1.00 (e.g., $1.05), you can sell YES on all outcomes and lock in guaranteed profit regardless of which outcome wins.

**Example:**
- Outcome A: YES = $0.52
- Outcome B: YES = $0.53
- Sum = $1.05

**Strategy:** Sell $1000 YES on both outcomes
- Revenue: $1050 (sum of prices  position size)
- Cost: $1000 (your capital)
- Fees: ~$30 (2% taker fee + gas)
- **Net Profit: $20** (2% return, risk-free)

## Development Roadmap

- [x] Phase 1: Backend scanner (Weeks 1-2)
- [ ] Phase 2: Telegram bot (Weeks 3-4)
- [ ] Phase 3: Payments (Weeks 5-6)
- [ ] Phase 4: Launch (Week 6)

## License

MIT
