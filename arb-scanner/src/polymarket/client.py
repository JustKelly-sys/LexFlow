"""Polymarket CLOB WebSocket client."""
import asyncio
import json
from typing import Callable
import websockets
from loguru import logger
from ..config import settings
from ..models import Market, MarketCategory


class PolymarketClient:
    """WebSocket client for Polymarket CLOB API."""
    
    def __init__(self):
        self.ws_url = settings.polymarket_ws_url
        self.connected = False
        self.ws = None
    
    async def connect(self):
        """Establish WebSocket connection."""
        try:
            self.ws = await websockets.connect(self.ws_url)
            self.connected = True
            logger.info(f"Connected to Polymarket CLOB: {self.ws_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Polymarket: {e}")
            raise
    
    async def subscribe_to_markets(self, callback: Callable):
        """
        Subscribe to market updates and process via callback.
        
        Args:
            callback: Async function to handle market data
        """
        if not self.connected:
            await self.connect()
        
        try:
            # Subscribe to all markets
            subscribe_msg = {
                "type": "subscribe",
                "channel": "markets"
            }
            await self.ws.send(json.dumps(subscribe_msg))
            
            # Listen for messages
            async for message in self.ws:
                data = json.loads(message)
                await self._process_message(data, callback)
                
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self.connected = False
        except Exception as e:
            logger.error(f"Error in WebSocket loop: {e}")
            raise
    
    async def _process_message(self, data: dict, callback: Callable):
        """Process incoming WebSocket message."""
        # Parse Polymarket message format and convert to Market model
        # This is a simplified version - actual implementation would need
        # to match Polymarket's specific message format
        
        if data.get("type") == "market_update":
            try:
                market = self._parse_market(data["data"])
                await callback(market)
            except Exception as e:
                logger.error(f"Failed to parse market: {e}")
    
    def _parse_market(self, data: dict) -> Market:
        """Parse Polymarket data into Market model."""
        # Simplified parser - real implementation would match API structure
        return Market(
            market_id=data["id"],
            name=data["question"],
            outcomes=data["outcomes"],
            outcome_prices={
                outcome: float(data["prices"].get(outcome, 0))
                for outcome in data["outcomes"]
            },
            liquidity_usd=float(data.get("liquidity", 0)),
            volume_24h=float(data.get("volume_24h", 0)),
            url=f"https://polymarket.com/event/{data['slug']}",
        )
    
    async def close(self):
        """Close WebSocket connection."""
        if self.ws:
            await self.ws.close()
            self.connected = False
            logger.info("Disconnected from Polymarket")
