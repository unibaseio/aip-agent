from typing import Dict, Any, Optional, List
import httpx
import asyncio

class DexScreenerProvider:
    """DEX Screener API data provider"""
    # bsc, solana
    def __init__(self, api_key: Optional[str] = None):
        self.supported_chains = ["bsc", "solana"]
        self.api_key = api_key
        self.session = httpx.AsyncClient()
        self.base_url = "https://api.dexscreener.com"
    
    async def close(self):
        """Close the HTTP session"""
        await self.session.aclose()
    
    async def _make_request(self, url: str, headers: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request with error handling"""
        try:
            response = await self.session.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            print(f"Request error: {e}")
            return {}
        except httpx.HTTPStatusError as e:
            print(f"HTTP error: {e}")
            return {}

    async def get_token_pools_by_address(self, chain: str, token_address: str, limit: int = 10) -> Dict[str, Any]:
        """Fetch token data by chain ID and contract address using /tokens/v1/{chainId}/{tokenAddresses}"""
        url = f"{self.base_url}/token-pairs/v1/{chain}/{token_address}"
        
        pairs = await self._make_request(url)
        
        if not pairs or not isinstance(pairs, list) or len(pairs) == 0:
            return {}
        
        # filter base token address
        pairs = [pair for pair in pairs if pair.get("baseToken", {}).get("address") == token_address]
        # Sort by liquidity and take the highest, 
        pairs.sort(key=lambda x: float(x.get("liquidity", {}).get("usd", 0)), reverse=True)
        
        if limit > len(pairs) or limit <= 0:
            limit = len(pairs)
        
        return {
            "pools": [self._extract_pair_data(pair) for pair in pairs[:limit]],
            "total_pools": len(pairs),
            "query": token_address,
            "provider": "dexscreener"
        }
    
    async def search_token(self, chain_id:str = None, query: str = None, limit: int = 10) -> Dict[str, Any]:
        """Search for tokens by name or symbol using /latest/dex/search"""
        url = f"{self.base_url}/latest/dex/search"
        params = {"q": query}
        
        data = await self._make_request(url, params=params)
        
        if not data or not data.get("pairs"):
            return {}
        
        pairs = data.get("pairs", [])
        if not pairs:
            return {}
        
        if chain_id:
            pairs = [pair for pair in pairs if pair.get("chainId") == chain_id]
        

        # Sort by liquidity for consistent ordering
        pairs.sort(key=lambda x: float(x.get("liquidity", {}).get("usd", 0)), reverse=True)

        # Return the first 10 pairs
        if limit > len(pairs) or limit <= 0:
            limit = len(pairs)
        
        return {
            "pools": [self._extract_pair_data(pair) for pair in pairs[:limit]],
            "total_pools": len(pairs),
            "query": query,
            "provider": "dexscreener"
        }
    
    async def get_token_address(self, chain_id: str, symbol: str) -> str:
        """Get token base data by chain ID and contract address using /tokens/v1/{chainId}/{tokenAddresses}"""
        res = await self.search_token(chain_id, symbol, limit=1)
        if not res or not res.get("tokens"):
            return {}
        if len(res["pools"]) == 0:
            return ""
        return res["pools"][0].get("base_address")
    
    async def get_token_pools(self, chain_id: str = 'bsc', identifier: str = None, limit: int = 10) -> Dict[str, Any]:
        """Main method to fetch token data - try by address first, then by search"""
        if not identifier:
            return {}
        
        # If chain_id provided and identifier looks like an address, use direct API
        if chain_id and len(identifier) == 42 and identifier.startswith('0x'):
            result = await self.get_token_pools_by_address(chain_id, identifier, limit)
            return result
        
        # Otherwise search by name/symbol (this now returns all pairs)
        result = await self.search_token(chain_id, identifier, limit)
        return result
    
    def _extract_pair_data(self, pair: Dict[str, Any]) -> Dict[str, Any]:
        """Extract standardized data from a DEX pair"""
        base_token = pair.get("baseToken", {})
        quote_token = pair.get("quoteToken", {})
        txns_24h = pair.get("txns", {}).get("h24", {})
        txns_6h = pair.get("txns", {}).get("h6", {})
        txns_1h = pair.get("txns", {}).get("h1", {})

        dex = pair.get("dexId", "unknown")
        dex_label = pair.get("labels")
        if dex_label and len(dex_label) > 0:
            dex = dex + "-" + dex_label[0]
        
        return {
            "base_name": base_token.get("name"),
            "base_symbol": base_token.get("symbol", ""),
            "base_address": base_token.get("address"),
            "quote_name": quote_token.get("name"),
            "quote_symbol": quote_token.get("symbol", ""),
            "quote_address": quote_token.get("address"),
            "price_usd": float(pair.get("priceUsd", 0)),
            "price_native": float(pair.get("priceNative", 0)),
            "price_change_24h": float(pair.get("priceChange", {}).get("h24", 0)),
            "price_change_6h": float(pair.get("priceChange", {}).get("h6", 0)),
            "price_change_1h": float(pair.get("priceChange", {}).get("h1", 0)),
            "volume_24h": float(pair.get("volume", {}).get("h24", 0)),
            "volume_6h": float(pair.get("volume", {}).get("h6", 0)),
            "volume_1h": float(pair.get("volume", {}).get("h1", 0)),
            "liquidity_usd": float(pair.get("liquidity", {}).get("usd", 0)),
            "market_cap": float(pair.get("marketCap", 0)),
            "fdv": float(pair.get("fdv", 0)),
            "dex": dex,
            "chain": pair.get("chainId"),
            "pair_address": pair.get("pairAddress"),
            "buys_24h": txns_24h.get("buys", 0),
            "sells_24h": txns_24h.get("sells", 0),
            "buys_6h": txns_6h.get("buys", 0),
            "sells_6h": txns_6h.get("sells", 0),
            "buys_1h": txns_1h.get("buys", 0),
            "sells_1h": txns_1h.get("sells", 0),
            "total_txns_24h": txns_24h.get("buys", 0) + txns_24h.get("sells", 0),
            "pair_created_at": pair.get("pairCreatedAt"),
            "provider": "dexscreener"
        } 