from typing import Dict, Any, Optional, List, Literal
import httpx
import os

class BirdEyeProvider:
    """BirdEye API data provider for DeFi token data"""
    # bsc, solana
    def __init__(self, api_key: Optional[str] = None):
        self.supported_chains = ["bsc", "solana"]
        self.api_key = api_key or os.getenv("BIRDEYE_API_KEY")
        self.session = httpx.AsyncClient()
        self.base_url = "https://public-api.birdeye.so"
        
        # Default headers
        self.headers = {
            "accept": "application/json",
            "X-API-KEY": self.api_key
        }
    
    async def close(self):
        """Close the HTTP session"""
        await self.session.aclose()
    
    async def _make_request(self, url: str, headers: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request with error handling"""
        try:
            response = await self.session.get(url, headers=headers, params=params)
            print(f"Response: {response.json()}")
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            print(f"Request error: {e}")
            return {}
        except httpx.HTTPStatusError as e:
            print(f"HTTP error: {e}")
            return {}
    
    async def get_top_tokens(self, chain: str = "bsc", sort_by: Literal["v24hUSD", "mc", "v24hChangePercent", "liquidity"] = "v24hUSD", sort_type: Literal["desc", "asc"] = "desc", offset: int = 0, limit: int = 50, min_liquidity: int = 100) -> Dict[str, Any]:
        """Get top tokens sorted by 24h volume"""
        url = f"{self.base_url}/defi/tokenlist"
        
        params = {
            "sort_by": sort_by,
            "sort_type": sort_type,
            "offset": offset,
            "limit": limit,
            "min_liquidity": min_liquidity
        }
        
        headers = {**self.headers, "x-chain": chain}
        
        data = await self._make_request(url, headers=headers, params=params)
        
        if not data or not data.get("success"):
            return {}
        
        tokens = data.get("data", {}).get("tokens", [])
        
        # Process and standardize token data
        processed_tokens = []
        for token in tokens:
            print(f"Token: {token}")
            processed_token = {
                "name": token.get("name"),
                "symbol": token.get("symbol"),
                "address": token.get("address"),
                "price_usd": float(token.get("price") or 0),
                "volume_24h": float(token.get("v24hUSD") or 0),
                "volume_change_24h": float(token.get("v24hChangePercent") or 0),
                "market_cap": float(token.get("mc") or 0),
                "liquidity": float(token.get("liquidity") or 0),
                "decimals": int(token.get("decimals") or 18),
                "logo_uri": token.get("logoURI"),
                "last_trade_unix_time": token.get("lastTradeUnixTime")
            }
            print(f"Processed token: {processed_token}")
            processed_tokens.append(processed_token)
        
        return {
            "tokens": processed_tokens,
            "total_tokens": len(processed_tokens),
            "chain": chain,
            "sort_by": sort_by,
            "provider": "birdeye",
            "update_time": data.get("data", {}).get("updateTime"),
            "update_unix_time": data.get("data", {}).get("updateUnixTime"),
            "success": True
        }
    
    async def get_top_tokens_by_volume(self, chain: str = "bsc", limit: int = 50, min_liquidity: int = 100) -> Dict[str, Any]:
        """Get top tokens by 24h volume (wrapper method for compatibility)"""
        return await self.get_top_tokens(
            chain=chain,
            sort_by="v24hUSD",
            sort_type="desc",
            limit=limit,
            min_liquidity=min_liquidity
        )
    
    async def get_top_tokens_by_market_cap(self, chain: str = "bsc", limit: int = 50, min_liquidity: int = 100) -> Dict[str, Any]:
        """Get top tokens by market cap (wrapper method for compatibility)"""
        return await self.get_top_tokens(
            chain=chain,
            sort_by="mc",
            sort_type="desc",
            limit=limit,
            min_liquidity=min_liquidity
        )

    