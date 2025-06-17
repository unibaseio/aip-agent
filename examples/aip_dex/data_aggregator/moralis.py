from typing import Dict, Any, Optional, List
import httpx
import asyncio
import os

class MoralisProvider:
    """Moralis API data provider using official SDK"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.supported_chains = ["bsc", "solana"]
        self.api_key = api_key or os.getenv("MORALIS_API_KEY")
        self.base_url = "https://deep-index.moralis.io/api/v2.2"
        self.session = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Accept": "application/json",
                "X-API-Key": self.api_key
            }
        )
    
    async def get_token_analytics(self, token_address: str, chain: str = "bsc") -> Optional[Dict[str, Any]]:
        """
        Get token analytics including trading volume, buyer/seller stats, and price changes
        
        Args:
            token_address: Token contract address
            chain: Blockchain name (default: bsc)
            
        Returns:
            Dict with analytics data or None if failed
        """
        try:
            chain = chain.lower()
            if chain not in self.supported_chains:
                raise ValueError(f"Unsupported chain: {chain}")
            
            url = f"{self.base_url}/tokens/{token_address}/analytics"
            params = {"chain": chain}
            
            response = await self.session.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Transform response to standardized format
                analytics = {
                    "token_address": data.get("tokenAddress"),
                    
                    # Buy/Sell Volume
                    "buy_volume_5m": float(data.get("totalBuyVolume", {}).get("5m", 0)),
                    "buy_volume_1h": float(data.get("totalBuyVolume", {}).get("1h", 0)),
                    "buy_volume_6h": float(data.get("totalBuyVolume", {}).get("6h", 0)),
                    "buy_volume_24h": float(data.get("totalBuyVolume", {}).get("24h", 0)),
                    
                    "sell_volume_5m": float(data.get("totalSellVolume", {}).get("5m", 0)),
                    "sell_volume_1h": float(data.get("totalSellVolume", {}).get("1h", 0)),
                    "sell_volume_6h": float(data.get("totalSellVolume", {}).get("6h", 0)),
                    "sell_volume_24h": float(data.get("totalSellVolume", {}).get("24h", 0)),
                    
                    # Buyer/Seller Count
                    "total_buyers_5m": data.get("totalBuyers", {}).get("5m", 0),
                    "total_buyers_1h": data.get("totalBuyers", {}).get("1h", 0),
                    "total_buyers_6h": data.get("totalBuyers", {}).get("6h", 0),
                    "total_buyers_24h": data.get("totalBuyers", {}).get("24h", 0),
                    
                    "total_sellers_5m": data.get("totalSellers", {}).get("5m", 0),
                    "total_sellers_1h": data.get("totalSellers", {}).get("1h", 0),
                    "total_sellers_6h": data.get("totalSellers", {}).get("6h", 0),
                    "total_sellers_24h": data.get("totalSellers", {}).get("24h", 0),
                    
                    # Buy/Sell Transaction Count
                    "total_buys_5m": data.get("totalBuys", {}).get("5m", 0),
                    "total_buys_1h": data.get("totalBuys", {}).get("1h", 0),
                    "total_buys_6h": data.get("totalBuys", {}).get("6h", 0),
                    "total_buys_24h": data.get("totalBuys", {}).get("24h", 0),
                    
                    "total_sells_5m": data.get("totalSells", {}).get("5m", 0),
                    "total_sells_1h": data.get("totalSells", {}).get("1h", 0),
                    "total_sells_6h": data.get("totalSells", {}).get("6h", 0),
                    "total_sells_24h": data.get("totalSells", {}).get("24h", 0),
                    
                    # Unique Wallets
                    "unique_wallets_5m": data.get("uniqueWallets", {}).get("5m", 0),
                    "unique_wallets_1h": data.get("uniqueWallets", {}).get("1h", 0),
                    "unique_wallets_6h": data.get("uniqueWallets", {}).get("6h", 0),
                    "unique_wallets_24h": data.get("uniqueWallets", {}).get("24h", 0),
                    
                    # Price Changes
                    "price_change_5m": float(data.get("pricePercentChange", {}).get("5m", 0)),
                    "price_change_1h": float(data.get("pricePercentChange", {}).get("1h", 0)),
                    "price_change_6h": float(data.get("pricePercentChange", {}).get("6h", 0)),
                    "price_change_24h": float(data.get("pricePercentChange", {}).get("24h", 0)),
                    
                    # Current Price and Market Data
                    "usd_price": float(data.get("usdPrice", 0)),
                    "total_liquidity_usd": float(data.get("totalLiquidityUsd", 0)),
                    "total_fdv": float(data.get("totalFullyDilutedValuation", 0)),
                    
                    # Meta
                    "data_source": "moralis",
                    "chain": chain
                }
                
                return analytics
                
            else:
                print(f"Moralis token analytics API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Error fetching token analytics from Moralis: {e}")
            return None
    
    async def get_holder_stats(self, token_address: str, chain: str = "bsc") -> Optional[Dict[str, Any]]:
        """
        Get token holder statistics including count, distribution, and changes
        
        Args:
            token_address: Token contract address
            chain: Blockchain name (default: bsc)
            
        Returns:
            Dict with holder stats or None if failed
        """
        try:
            chain = chain.lower()
            if chain not in self.supported_chains:
                raise ValueError(f"Unsupported chain: {chain}")
            
            url = f"{self.base_url}/erc20/{token_address}/holders"
            params = {"chain": chain}
            
            response = await self.session.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Transform response to standardized format
                holder_stats = {
                    "token_address": token_address,
                    
                    # Total Holders
                    "total_holders": data.get("totalHolders", 0),
                    
                    # Holders by Acquisition
                    "holders_by_swap": data.get("holdersByAcquisition", {}).get("swap", 0),
                    "holders_by_transfer": data.get("holdersByAcquisition", {}).get("transfer", 0),
                    "holders_by_airdrop": data.get("holdersByAcquisition", {}).get("airdrop", 0),
                    
                    # Holder Changes
                    "holder_change_5m": data.get("holderChange", {}).get("5min", {}).get("change", 0),
                    "holder_change_5m_percent": float(data.get("holderChange", {}).get("5min", {}).get("changePercent", 0)),
                    
                    "holder_change_1h": data.get("holderChange", {}).get("1h", {}).get("change", 0),
                    "holder_change_1h_percent": float(data.get("holderChange", {}).get("1h", {}).get("changePercent", 0)),
                    
                    "holder_change_6h": data.get("holderChange", {}).get("6h", {}).get("change", 0),
                    "holder_change_6h_percent": float(data.get("holderChange", {}).get("6h", {}).get("changePercent", 0)),
                    
                    "holder_change_24h": data.get("holderChange", {}).get("24h", {}).get("change", 0),
                    "holder_change_24h_percent": float(data.get("holderChange", {}).get("24h", {}).get("changePercent", 0)),
                    
                    "holder_change_3d": data.get("holderChange", {}).get("3d", {}).get("change", 0),
                    "holder_change_3d_percent": float(data.get("holderChange", {}).get("3d", {}).get("changePercent", 0)),
                    
                    "holder_change_7d": data.get("holderChange", {}).get("7d", {}).get("change", 0),
                    "holder_change_7d_percent": float(data.get("holderChange", {}).get("7d", {}).get("changePercent", 0)),
                    
                    "holder_change_30d": data.get("holderChange", {}).get("30d", {}).get("change", 0),
                    "holder_change_30d_percent": float(data.get("holderChange", {}).get("30d", {}).get("changePercent", 0)),
                    
                    # Supply Distribution by Top Holders
                    "top10_supply_percent": float(data.get("holderSupply", {}).get("top10", {}).get("supplyPercent", 0)),
                    "top25_supply_percent": float(data.get("holderSupply", {}).get("top25", {}).get("supplyPercent", 0)),
                    "top50_supply_percent": float(data.get("holderSupply", {}).get("top50", {}).get("supplyPercent", 0)),
                    "top100_supply_percent": float(data.get("holderSupply", {}).get("top100", {}).get("supplyPercent", 0)),
                    "top250_supply_percent": float(data.get("holderSupply", {}).get("top250", {}).get("supplyPercent", 0)),
                    "top500_supply_percent": float(data.get("holderSupply", {}).get("top500", {}).get("supplyPercent", 0)),
                    
                    # Holder Distribution by Size
                    "whales_count": data.get("holderDistribution", {}).get("whales", 0),
                    "sharks_count": data.get("holderDistribution", {}).get("sharks", 0),
                    "dolphins_count": data.get("holderDistribution", {}).get("dolphins", 0),
                    "fish_count": data.get("holderDistribution", {}).get("fish", 0),
                    "octopus_count": data.get("holderDistribution", {}).get("octopus", 0),
                    "crabs_count": data.get("holderDistribution", {}).get("crabs", 0),
                    "shrimps_count": data.get("holderDistribution", {}).get("shrimps", 0),
                    
                    # Meta
                    "data_source": "moralis",
                    "chain": chain
                }
                
                return holder_stats
                
            else:
                print(f"Moralis holder stats API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Error fetching holder stats from Moralis: {e}")
            return None
    
    async def get_token_stats(self, token_address: str, chain: str = "bsc") -> Dict[str, Any]:
        """
        Get comprehensive token statistics combining analytics and holder data
        
        Args:
            token_address: Token contract address
            chain: Blockchain name (default: bsc)
            
        Returns:
            Combined token statistics
        """
        try:
            # Fetch both analytics and holder stats concurrently
            analytics_task = self.get_token_analytics(token_address, chain)
            holder_stats_task = self.get_holder_stats(token_address, chain)
            
            analytics_data, holder_data = await asyncio.gather(
                analytics_task, holder_stats_task, return_exceptions=True
            )
            
            # Combine results
            combined_stats = {}
            
            # Add analytics data
            if isinstance(analytics_data, dict):
                combined_stats.update(analytics_data)
            
            # Add holder data
            if isinstance(holder_data, dict):
                combined_stats.update(holder_data)
            
            # Add computed metrics
            if combined_stats:
                # Buy/Sell ratio
                buy_vol_24h = combined_stats.get("buy_volume_24h", 0)
                sell_vol_24h = combined_stats.get("sell_volume_24h", 0)
                
                if sell_vol_24h > 0:
                    combined_stats["buy_sell_ratio_24h"] = buy_vol_24h / sell_vol_24h
                else:
                    combined_stats["buy_sell_ratio_24h"] = float('inf') if buy_vol_24h > 0 else 0
                
                # Total volume
                combined_stats["total_volume_24h"] = buy_vol_24h + sell_vol_24h
                
                # Net volume (buy - sell)
                combined_stats["net_volume_24h"] = buy_vol_24h - sell_vol_24h
            
            return combined_stats
            
        except Exception as e:
            print(f"Error fetching combined token stats from Moralis: {e}")
            return {}
    
    async def close(self):
        """Close the HTTP session"""
        await self.session.aclose()