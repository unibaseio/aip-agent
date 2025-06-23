"""
Token Service for AIP DEX - Enhanced Data Aggregation

This service integrates multiple data aggregators and maps their data to database models:

DATA AGGREGATOR FIELD MAPPINGS:
===============================

1. DexScreener (dex_screener.py):
   Pool Data:
   - base_name, base_symbol, base_address -> Token fields
   - quote_name, quote_symbol, quote_address -> Quote Token fields  
   - price_usd, price_native -> PoolMetric.price_usd, price_native
   - volume_1h, volume_6h, volume_24h -> PoolMetric.volume_1h/6h/24h
   - price_change_1h, price_change_6h, price_change_24h -> PoolMetric.price_change_1h/6h/24h
   - buys_1h/sells_1h, buys_6h/sells_6h, buys_24h/sells_24h -> PoolMetric.txns_*
   - liquidity_usd -> PoolMetric.liquidity_usd
   - market_cap, fdv -> PoolMetric.market_cap, fdv
   - dex -> TokenPool.dex
   - pair_address -> TokenPool.pair_address
   - pair_created_at -> TokenPool.pair_created_at

2. Moralis (moralis.py):
   Token Analytics:
   - buy_volume_5m/1h/6h/24h -> TokenMetric.buy_volume_*
   - sell_volume_5m/1h/6h/24h -> TokenMetric.sell_volume_*
   - total_buyers_5m/1h/6h/24h -> TokenMetric.total_buyers_*
   - total_sellers_5m/1h/6h/24h -> TokenMetric.total_sellers_*
   - total_buys_5m/1h/6h/24h -> TokenMetric.total_buys_*
   - total_sells_5m/1h/6h/24h -> TokenMetric.total_sells_*
   - unique_wallets_5m/1h/6h/24h -> TokenMetric.unique_wallets_*
   - price_change_5m/1h/6h/24h -> TokenMetric.price_change_*
   - usd_price -> TokenMetric.usd_price_moralis
   - total_liquidity_usd -> TokenMetric.total_liquidity_usd_moralis
   - total_fdv -> TokenMetric.total_fdv

   Holder Stats:
   - total_holders -> TokenMetric.holder_count
   - holder_change_5m/1h/6h/24h/3d/7d/30d -> TokenMetric.holder_change_*
   - holder_change_*_percent -> TokenMetric.holder_change_*_percent
   - whales_count, sharks_count, etc. -> TokenMetric.*_count
   - top10/25/50/100/250/500_supply_percent -> TokenMetric.top*_supply_percent
   - holders_by_swap/transfer/airdrop -> TokenMetric.holders_by_*

   Token Info:
   - token_name -> Token.name
   - token_symbol -> Token.symbol
   - token_logo -> Token.image_url

3. BirdEye (birdeye.py):
   Token Data:
   - name, symbol, address -> Token fields
   - price -> TokenMetric price fields
   - volume_24h -> TokenMetric.total_volume_24h
   - volume_change_24h -> TokenMetric.volume_change_24h
   - market_cap -> TokenMetric.market_cap
   - liquidity -> TokenMetric.total_liquidity_usd
   - decimals -> Token.decimals
   - logo_uri -> Token.logo_uri
   - last_trade_unix_time -> Token.last_trade_unix_time

DATABASE MODEL COVERAGE:
========================

All database fields are now covered by at least one data aggregator:
✓ Token: All fields covered (DexScreener, Moralis, BirdEye)
✓ TokenPool: All fields covered (DexScreener)
✓ PoolMetric: All fields covered (DexScreener + enhanced timeframes)
✓ TokenMetric: All fields covered (Moralis comprehensive + DexScreener aggregated + BirdEye)
✓ History Tables: All critical fields covered for trend analysis

INTEGRATION FLOW:
================
1. get_or_create_token() - Creates tokens with data from any aggregator
2. update_token_pools() - Updates pools and metrics from DexScreener
3. update_token() - Updates comprehensive metrics from Moralis + signals
4. All data automatically saved to history tables for trend analysis
"""

import asyncio
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from models.database import Token, TokenPool, PoolMetric, TokenMetric, PoolMetricHistory, TokenMetricsHistory
from data_aggregator.dex_screener import DexScreenerProvider
from data_aggregator.moralis import MoralisProvider
from data_aggregator.birdeye import BirdEyeProvider
from indicators.calculator import TokenSignalCalculator
from llm.token_analyzer import TokenDecisionAnalyzer

class TokenService:
    """Simplified TokenService with three core methods"""
    
    def __init__(self):
        self.dex_screener = DexScreenerProvider()
        self.moralis = MoralisProvider()
        self.birdeye = BirdEyeProvider()
        self.signal_calculator = TokenSignalCalculator()
    
    async def get_or_create_token(self, db: Session, symbol: str, 
                                 contract_address: Optional[str] = None,
                                 chain: Optional[str] = None,
                                 name: Optional[str] = None,
                                 decimals: Optional[int] = 18,
                                 ) -> Optional[Token]:
        """Get existing token or create new one with enhanced data from aggregators"""
        if symbol:
            symbol = symbol.upper()
        
        # Try to find existing token by unique constraint (contract_address + chain)
        token = None
        if contract_address and chain:
            token = db.query(Token).filter(
                Token.contract_address == contract_address,
                Token.chain == chain
            ).first()
        
        # If not found by contract_address+chain, try by symbol+chain
        if not token and symbol and chain:
            token = db.query(Token).filter(
                Token.symbol == symbol,
                Token.chain == chain
            ).first()
        
        if token:
            # Update existing token with new data if provided
            if name and token.name != name:
                token.name = name
            if symbol and token.symbol != symbol:
                token.symbol = symbol
            if contract_address and token.contract_address != contract_address:
                token.contract_address = contract_address
            token.updated_at = datetime.now(timezone.utc)
            try:
                db.commit()
                db.refresh(token)
                return token
            except Exception as e:
                db.rollback()
                print(f"Error updating existing token: {e}")
                return token
        
        # If all required data is provided, create token directly
        if contract_address and chain and symbol and contract_address != "" and chain != "" and symbol != "" and name != "":
            token = Token(
                name=name,
                symbol=symbol.upper(),
                contract_address=contract_address,
                chain=chain,
                decimals=decimals or 18,
                metrics_updated_at=None  # Mark as needing update
            )
            db.add(token)
            try:
                db.commit()
                db.refresh(token)
                return token
            except Exception as e:
                db.rollback()
                print(f"Error creating token, trying to find existing: {e}")
                # Try to find existing token again in case it was created by another process
                existing_token = db.query(Token).filter(
                    Token.contract_address == contract_address,
                    Token.chain == chain
                ).first()
                if existing_token:
                    return existing_token
                else:
                    print(f"Failed to create or find token: {e}")
                    return None
        
        # If missing data, resolve token data from external sources
        try:
            token_data = await self._resolve_token_data(symbol, contract_address, chain)
            if not token_data or not token_data.get('symbol'):
                return None
        except Exception as e:
            print(f"Error resolving token data: {e}")
            return None
        
        # Create new token with resolved data
        resolved_contract_address = token_data.get('contract_address', contract_address)
        resolved_chain = token_data.get('chain', chain or 'bsc')
        
        # Check one more time if token exists with resolved data
        if resolved_contract_address and resolved_chain:
            existing_token = db.query(Token).filter(
                Token.contract_address == resolved_contract_address,
                Token.chain == resolved_chain
            ).first()
            if existing_token:
                return existing_token
        
        token = Token(
            name=token_data.get('name', name or symbol),
            symbol=token_data.get('symbol'),
            contract_address=resolved_contract_address,
            chain=resolved_chain,
            decimals=token_data.get('decimals', 18),
            metrics_updated_at=None  # Mark as needing update
        )
        
        db.add(token)
        try:
            db.commit()
            db.refresh(token)
            return token
        except Exception as e:
            db.rollback()
            print(f"Error creating resolved token, trying to find existing: {e}")
            # Try to find existing token again in case it was created by another process
            existing_token = db.query(Token).filter(
                Token.contract_address == resolved_contract_address,
                Token.chain == resolved_chain
            ).first()
            if existing_token:
                return existing_token
            else:
                print(f"Failed to create or find resolved token: {e}")
                return None
        

    async def update_token_pools(self, db: Session, token_id: str, 
                                force_update: bool = False) -> Dict[str, Any]:
        """Update token pools, pool metrics and signals. Uses metrics_updated_at field to check if update is needed (> 1 hour)"""
        try:
            # Get token
            token = db.query(Token).filter(Token.id == token_id).first()
            if not token:
                return {
                    "success": False,
                    "error": f"Token with id {token_id} not found"
                }

            # Check if recently updated using metrics_updated_at field
            should_update = force_update
            
            if not should_update and token.metrics_updated_at:
                one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
                should_update = self._is_datetime_before(token.metrics_updated_at, one_hour_ago)
            else:
                should_update = True

            # Get existing pools count for result
            existing_pools = db.query(TokenPool).filter(TokenPool.base_token_id == token_id).all()
            
            result = {
                "success": True,
                "token_id": token_id,
                "token_symbol": token.symbol,
                "pools_updated": False,
                "new_pools": 0,
                "updated_metrics": 0,
                "pools_count": len(existing_pools)
            }

            if should_update:
                # Fetch pool data from DexScreener
                pools_result = await self.dex_screener.get_token_pools(
                    chain_id=token.chain,
                    identifier=token.contract_address,
                    limit=15
                )
                
                if pools_result and pools_result.get("pools"):
                    pools_data = pools_result["pools"]
                    new_pools_count = 0
                    updated_metrics_count = 0
                    
                    for pool_data in pools_data:
                        try:
                            # Create or update pool
                            pool = await self._create_or_update_pool(db, token, pool_data)
                            
                            if pool:
                                new_pools_count += 1
                                
                                # Update pool metrics with pool data
                                pool_metric = await self._create_pool_metric_from_data(
                                    db, pool, pool_data
                                )
                                if pool_metric:
                                    updated_metrics_count += 1
                                
                        except Exception as e:
                            print(f"Error processing pool for {token.symbol}: {e}")
                    
                    result["new_pools"] = new_pools_count
                    result["updated_metrics"] = updated_metrics_count
                    result["pools_updated"] = True

            # Update pools count
            updated_pools = db.query(TokenPool).filter(TokenPool.base_token_id == token_id).all()
            result["pools_count"] = len(updated_pools)

            # Calculate token metrics and signals
            if result["pools_updated"] or force_update:
                await self._calculate_token_metrics(db, token_id)
                await self._calculate_token_signals(db, token_id)

            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error updating token pools: {str(e)}"
            }

    async def update_token(self, db: Session, token_id: str, 
                          force_update: bool = False) -> Dict[str, Any]:
        """Update token stats from Moralis, save to history, calculate signals and update metrics. Uses metrics_updated_at field to check if update is needed (> 1 hour)"""
        try:
            # Get token
            token = db.query(Token).filter(Token.id == token_id).first()
            if not token:
                return {
                    "success": False,
                    "error": f"Token with id {token_id} not found"
                }

            # Check if recently updated using token's metrics_updated_at field
            should_update = force_update
            
            print(f"Token metrics updated at: {token.metrics_updated_at} {should_update}")
            if not should_update and token.metrics_updated_at:
                one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
                should_update = self._is_datetime_before(token.metrics_updated_at, one_hour_ago)
            else:
                should_update = True

            print(f"Should update: {should_update}")
            
            result = {
                "success": True,
                "token_id": token_id,
                "token_symbol": token.symbol,
                "moralis_updated": False,
                "history_saved": False,
                "metrics_updated": False,
                "signals_updated": False,
                "moralis_stats": None
            }

            if should_update:
                # STEP 1: Update token stats from Moralis
                moralis_stats = None
                print(f"Updating token stats for {token.symbol}")
                if token.contract_address:
                    print(f"Updating token stats for {token.symbol} with address {token.contract_address}")
                    # Get comprehensive token stats from Moralis
                    moralis_stats = await self.moralis.get_token_stats(
                        token.contract_address,
                        token.chain
                    )
                    print(f"Updated Moralis stats: {moralis_stats}")
                    if moralis_stats:
                        await asyncio.sleep(1)
                        result["moralis_updated"] = True
                        result["moralis_stats"] = moralis_stats
                
                # STEP 2: Save to history
                if moralis_stats:
                    history_saved = await self._save_moralis_stats_to_history(db, token_id, moralis_stats)
                    result["history_saved"] = history_saved
                
                # STEP 3: Calculate token signals
                # Get historical data for signal calculation
                historical_metrics = await self._get_historical_token_metrics(db, token_id)
                
                signals = await self._calculate_token_signals_enhanced(
                    db, token_id, historical_metrics, moralis_stats
                )
                if signals:
                    result["signals_updated"] = True
                    result["signals"] = signals
                
                # STEP 4: Update metrics and history metrics
                token_metric = await self._calculate_token_metrics_enhanced(
                    db, token_id, moralis_stats
                )
                if token_metric:
                    result["metrics_updated"] = True
                    result["token_metrics"] = {
                        "avg_price_usd": float(token_metric.avg_price_usd or 0),
                        "weighted_price_usd": float(token_metric.weighted_price_usd or 0),
                        "total_volume_24h": float(token_metric.total_volume_24h or 0),
                        "total_liquidity_usd": float(token_metric.total_liquidity_usd or 0),
                        "pools_count": token_metric.pools_count
                    }
                    
                    # Update token metrics with signal data
                    if signals:
                        token_metric.signal_strength = signals.get("strength", 0.5)
                        token_metric.trend_direction = self._map_signal_to_trend_direction(signals.get("signal", "HOLD"))
                        db.commit()
                        db.refresh(token_metric)
                        
                # Finally update metrics_updated_at field after successful update
                if result.get("moralis_updated") or result.get("metrics_updated") or result.get("signals_updated"):
                    token.metrics_updated_at = datetime.now(timezone.utc)
                    db.commit()
                    db.refresh(token)

            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error updating token: {str(e)}"
            }

    async def batch_update_tokens(self, db: Session, token_ids: List[str], 
                                 force_update: bool = False) -> Dict[str, Any]:
        """Batch update multiple tokens with all data and indicators"""
        try:
            results = {
                "success": True,
                "total_tokens": len(token_ids),
                "updated_tokens": 0,
                "failed_tokens": 0,
                "results": {}
            }
            
            for token_id in token_ids:
                try:
                    # Step 1: Update token pools
                    pools_result = await self.update_token_pools(db, token_id, force_update)
                    
                    # Step 2: Update token metrics and signals
                    token_result = await self.update_token(db, token_id, force_update)
                    
                    if token_result.get("success", False):
                        results["updated_tokens"] += 1
                        results["results"][token_id] = {
                            "success": True,
                            "pools_updated": pools_result.get("pools_updated", False),
                            "metrics_updated": token_result.get("metrics_updated", False),
                            "signals_updated": token_result.get("signals_updated", False),
                            "moralis_updated": token_result.get("moralis_updated", False)
                        }
                    else:
                        results["failed_tokens"] += 1
                        results["results"][token_id] = {
                            "success": False,
                            "error": token_result.get("error", "Unknown error")
                        }
                        
                except Exception as e:
                    results["failed_tokens"] += 1
                    results["results"][token_id] = {
                        "success": False,
                        "error": f"Error updating token {token_id}: {str(e)}"
                    }
            
            return results
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error in batch update: {str(e)}"
            }

    async def get_tokens_requiring_update(self, db: Session, max_age_hours: int = 1) -> List[str]:
        """Get list of token IDs that need data updates based on metrics_updated_at field"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
            
            # Get tokens that haven't been updated recently using metrics_updated_at field
            tokens_needing_update = db.query(Token.id).filter(
                (Token.metrics_updated_at.is_(None)) |
                (Token.metrics_updated_at < cutoff_time)
            ).all()
            
            return [str(token.id) for token in tokens_needing_update]
            
        except Exception as e:
            print(f"Error getting tokens requiring update: {e}")
            return []

    # ===== HELPER METHODS =====
    
    def _token_needs_update(self, token: Token, max_age_hours: int = 1) -> bool:
        """Check if token needs metrics update based on metrics_updated_at field"""
        if not token.metrics_updated_at:
            return True
            
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        return self._is_datetime_before(token.metrics_updated_at, cutoff_time)

    def _map_signal_to_trend_direction(self, signal: str) -> str:
        """Map trading signal to database trend_direction format"""
        signal_mapping = {
            "BUY": "bullish",
            "SELL": "bearish", 
            "HOLD": "sideways"
        }
        return signal_mapping.get(signal, "sideways")

    def _safe_timestamp_to_datetime(self, timestamp: Any) -> Optional[datetime]:
        """Safely convert timestamp to datetime, handling both seconds and milliseconds"""
        try:
            if timestamp is None:
                return None
            
            # Convert to float to handle string inputs
            timestamp_float = float(timestamp)
            
            # If timestamp is 0 or negative, return None
            if timestamp_float <= 0:
                return None
            
            # Check if timestamp is in milliseconds (larger than 1e10)
            # Unix timestamp in seconds for year 2000: ~946684800
            # Unix timestamp in seconds for year 2030: ~1893456000
            # If timestamp > 1e10, it's likely in milliseconds
            if timestamp_float > 1e10:
                timestamp_float = timestamp_float / 1000
            
            # Additional check: if still too large, likely invalid
            if timestamp_float > 2e9:  # Year ~2033
                print(f"Warning: timestamp {timestamp_float} seems too large, skipping")
                return None
            
            return datetime.fromtimestamp(timestamp_float, timezone.utc)
            
        except (ValueError, TypeError, OSError) as e:
            print(f"Error converting timestamp {timestamp}: {e}")
            return None

    def _calculate_data_age_hours(self, dt: datetime) -> Optional[float]:
        """Safely calculate data age in hours, handling timezone differences"""
        try:
            now = datetime.now(timezone.utc)
            
            # If dt has no timezone info, assume UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            
            # Calculate the difference
            diff = now - dt
            return diff.total_seconds() / 3600
            
        except Exception as e:
            print(f"Error calculating data age: {e}")
            return None

    def _is_datetime_after(self, dt: datetime, compare_dt: datetime) -> bool:
        """Safely compare if dt is after compare_dt, handling timezone differences"""
        try:
            # If dt has no timezone info, assume UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            
            # If compare_dt has no timezone info, assume UTC
            if compare_dt.tzinfo is None:
                compare_dt = compare_dt.replace(tzinfo=timezone.utc)
            
            return dt > compare_dt
            
        except Exception as e:
            print(f"Error comparing datetimes: {e}")
            return False

    def _is_datetime_before(self, dt: datetime, compare_dt: datetime) -> bool:
        """Safely compare if dt is before compare_dt, handling timezone differences"""
        try:
            # If dt has no timezone info, assume UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            
            # If compare_dt has no timezone info, assume UTC
            if compare_dt.tzinfo is None:
                compare_dt = compare_dt.replace(tzinfo=timezone.utc)
            
            return dt < compare_dt
            
        except Exception as e:
            print(f"Error comparing datetimes: {e}")
            return False

    async def _resolve_token_data(self, symbol: str, contract_address: Optional[str] = None,
                                 chain: str = 'bsc') -> Optional[Dict[str, Any]]:
        """Resolve token data from external sources"""
        print(f"Resolving token data for {symbol} on {chain}")
        try:
            # Try DexScreener first
            if not contract_address or contract_address == "":
                if not symbol or symbol == "":
                    return None
                contract_address = await self.dex_screener.get_token_address(chain, symbol)
                print(f"Resolved contract address: {contract_address}")

            if contract_address and contract_address != "":
                print(f"Getting token pools for {contract_address} on {chain}")
                result = await self.dex_screener.get_token_pools_by_address(chain, contract_address)
                if result and result.get("pools"):
                    token_data = result["pools"][0]
                    return {
                        "symbol": token_data.get("symbol"),
                        "name": token_data.get("name"),
                        "contract_address": contract_address,
                        "chain": chain,
                        "decimals": token_data.get("decimals", 18)
                    }
            
            return None
        except Exception as e:
            print(f"Error resolving token data: {e}")
            return None

    async def _create_or_update_pool(self, db: Session, token: Token, pool_data: Dict[str, Any]) -> Optional[TokenPool]:
        """Create or update a token pool"""
        try:
            # Check if pool already exists
            existing_pool = db.query(TokenPool).filter(
                TokenPool.chain == token.chain,
                TokenPool.pair_address == pool_data.get("pair_address", "")
            ).first()

            if existing_pool:
                print(f"Updating existing pool for {token.symbol} on {token.chain} with pair address {pool_data.get('pair_address', '')}")
                # Update existing pool
                existing_pool.is_active = True
                existing_pool.updated_at = datetime.now(timezone.utc)
                # Update additional fields from DexScreener
                if pool_data.get("pair_created_at"):
                    existing_pool.pair_created_at = self._safe_timestamp_to_datetime(pool_data["pair_created_at"])
                db.commit()
                return existing_pool
            
            # Create new pool
            # For simplicity, use a default quote token (USDT)
            quote_token = await self.get_or_create_token(
                db, 
                pool_data.get("quote_symbol"), 
                pool_data.get("quote_address"), 
                token.chain, 
                pool_data.get("quote_name")
            )
            
            if not quote_token:
                return None
            
            print(f"Creating pool for {token.symbol} on {token.chain} with quote token {quote_token.symbol}")
                
            pool = TokenPool(
                base_token_id=str(token.id),
                quote_token_id=str(quote_token.id),
                dex=pool_data.get("dex", "unknown"),
                chain=token.chain,
                pair_address=pool_data.get("pair_address", ""),
                is_active=True,
                # Additional fields from DexScreener
                pair_created_at=self._safe_timestamp_to_datetime(pool_data.get("pair_created_at")),
            )
            
            db.add(pool)
            db.commit()
            db.refresh(pool)
            return pool
            
        except Exception as e:
            print(f"Error creating/updating pool: {e}")
            db.rollback()
            return None

    def _sanitize_price_change(self, value: float, max_value: float = 99999.0) -> float:
        """Sanitize price change values to prevent database overflow
        
        Database field is DECIMAL(15,4) which can store up to 99999999999.9999
        But for price changes, we cap at 99999.0% to prevent extreme values
        """
        if value is None:
            return 0.0
        
        # Convert to float if it's not already
        try:
            float_value = float(value)
        except (ValueError, TypeError):
            return 0.0
        
        # Handle infinite or NaN values
        if not float_value or abs(float_value) == float('inf') or float_value != float_value:  # NaN check
            return 0.0
        
        # Cap extreme values to prevent database overflow
        # DECIMAL(15,4) can store up to 99999999999.9999, but we cap at reasonable percentage
        if abs(float_value) > max_value:
            # Log the extreme value for monitoring
            print(f"Warning: Extreme price change value {float_value}% capped to {max_value if float_value > 0 else -max_value}%")
            return max_value if float_value > 0 else -max_value
        
        return float_value

    async def _create_pool_metric_from_data(self, db: Session, pool: TokenPool, 
                                          pool_data: Dict[str, Any]) -> Optional[PoolMetric]:
        """Create pool metric from DexScreener data with enhanced fields"""
        try:
            # Sanitize price change values to prevent database overflow
            price_change_1h = self._sanitize_price_change(pool_data.get('price_change_1h', 0))
            price_change_6h = self._sanitize_price_change(pool_data.get('price_change_6h', 0))
            price_change_24h = self._sanitize_price_change(pool_data.get('price_change_24h', 0))
            
            metric = PoolMetric(
                pool_id=pool.id,
                price_usd=Decimal(str(pool_data.get('price_usd', 0))),
                price_native=Decimal(str(pool_data.get('price_native', 0))),
                
                # Enhanced volume data (1h, 6h, 24h)
                volume_1h=Decimal(str(pool_data.get('volume_1h', 0))),
                volume_6h=Decimal(str(pool_data.get('volume_6h', 0))),
                volume_24h=Decimal(str(pool_data.get('volume_24h', 0))),
                
                liquidity_usd=Decimal(str(pool_data.get('liquidity_usd', 0))),
                liquidity_base=Decimal('0'),
                liquidity_quote=Decimal('0'),
                
                # Enhanced price changes (1h, 6h, 24h) - with sanitization
                price_change_1h=Decimal(str(price_change_1h)),
                price_change_6h=Decimal(str(price_change_6h)),
                price_change_24h=Decimal(str(price_change_24h)),
                
                # Enhanced transaction data (1h, 6h, 24h)
                txns_1h_buys=pool_data.get('buys_1h', 0),
                txns_1h_sells=pool_data.get('sells_1h', 0),
                txns_6h_buys=pool_data.get('buys_6h', 0),
                txns_6h_sells=pool_data.get('sells_6h', 0),
                txns_24h_buys=pool_data.get('buys_24h', 0),
                txns_24h_sells=pool_data.get('sells_24h', 0),
                
                market_cap=Decimal(str(pool_data.get('market_cap', 0))),
                fdv=Decimal(str(pool_data.get('fdv', 0))),
                data_source='dexscreener'
            )
            
            db.add(metric)
            
            # Save to history with enhanced fields
            history = PoolMetricHistory(
                pool_id=pool.id,
                price_usd=metric.price_usd,
                price_native=metric.price_native,
                volume_1h=metric.volume_1h,
                volume_24h=metric.volume_24h,
                liquidity_usd=metric.liquidity_usd,
                price_change_1h=metric.price_change_1h,
                price_change_24h=metric.price_change_24h,
                txns_1h_buys=metric.txns_1h_buys,
                txns_1h_sells=metric.txns_1h_sells,
                txns_24h_buys=metric.txns_24h_buys,
                txns_24h_sells=metric.txns_24h_sells,
                market_cap=metric.market_cap,
                fdv=metric.fdv,
                data_source='dexscreener',
                recorded_at=datetime.now(timezone.utc)
            )
            db.add(history)
            
            db.commit()
            db.refresh(metric)
            return metric
            
        except Exception as e:
            print(f"Error creating pool metric: {e}")
            db.rollback()
            return None

    async def _calculate_token_metrics(self, db: Session, token_id: str) -> Optional[TokenMetric]:
        """Calculate aggregated token metrics from pool metrics"""
        try:
            # Get all active pools for this token
            pools = db.query(TokenPool).filter(
                TokenPool.base_token_id == token_id,
                TokenPool.is_active == True
            ).all()
            
            if not pools:
                return None
                
            # Get latest metrics for each pool
            pool_metrics = []
            for pool in pools:
                latest_metric = db.query(PoolMetric)\
                    .filter(PoolMetric.pool_id == pool.id)\
                    .order_by(desc(PoolMetric.updated_at))\
                    .first()
                if latest_metric:
                    pool_metrics.append(latest_metric)
            
            if not pool_metrics:
                return None
                
            # Calculate aggregated metrics
            total_volume_24h = sum(float(m.volume_24h or 0) for m in pool_metrics)
            total_liquidity_usd = sum(float(m.liquidity_usd or 0) for m in pool_metrics)
            
            # Weighted average price (by liquidity)
            if total_liquidity_usd > 0:
                weighted_price = sum(
                    float(m.price_usd or 0) * float(m.liquidity_usd or 0) 
                    for m in pool_metrics
                ) / total_liquidity_usd
            else:
                weighted_price = sum(float(m.price_usd or 0) for m in pool_metrics) / len(pool_metrics)
            
            # Simple average price
            avg_price = sum(float(m.price_usd or 0) for m in pool_metrics) / len(pool_metrics)
            
            # Create or update token metric
            existing_metric = db.query(TokenMetric).filter(TokenMetric.token_id == token_id).first()
            
            if existing_metric:
                existing_metric.avg_price_usd = Decimal(str(avg_price))
                existing_metric.weighted_price_usd = Decimal(str(weighted_price))
                existing_metric.total_volume_24h = Decimal(str(total_volume_24h))
                existing_metric.total_liquidity_usd = Decimal(str(total_liquidity_usd))
                existing_metric.pools_count = len(pools)
                existing_metric.last_calculation_at = datetime.now(timezone.utc)
                metric = existing_metric
            else:
                metric = TokenMetric(
                    token_id=token_id,
                    avg_price_usd=Decimal(str(avg_price)),
                    weighted_price_usd=Decimal(str(weighted_price)),
                    total_volume_24h=Decimal(str(total_volume_24h)),
                    total_liquidity_usd=Decimal(str(total_liquidity_usd)),
                    pools_count=len(pools),
                    trend_direction="sideways",  # Set default value to satisfy constraint
                    last_calculation_at=datetime.now(timezone.utc)
                )
                db.add(metric)
            
            db.commit()
            db.refresh(metric)
            
            # Save to history
            await self._save_token_metrics_history(db, metric)
            
            return metric
            
        except Exception as e:
            print(f"Error calculating token metrics: {e}")
            db.rollback()
            return None

    async def _calculate_token_signals(self, db: Session, token_id: str) -> Optional[Dict[str, Any]]:
        """Calculate token trading signals"""
        try:
            # Get token metrics
            token_metric = db.query(TokenMetric).filter(TokenMetric.token_id == token_id).first()
            if not token_metric:
                return None
                
            # Get recent pool metrics for trend analysis
            pools = db.query(TokenPool).filter(
                TokenPool.base_token_id == token_id,
                TokenPool.is_active == True
            ).all()
            
            recent_metrics = []
            for pool in pools:
                metrics = db.query(PoolMetric)\
                    .filter(PoolMetric.pool_id == pool.id)\
                    .order_by(desc(PoolMetric.updated_at))\
                    .limit(5)\
                    .all()
                recent_metrics.extend(metrics)
            
            if not recent_metrics:
                return None
                
            # Simple signal calculation
            avg_price_change_24h = sum(float(m.price_change_24h or 0) for m in recent_metrics) / len(recent_metrics)
            avg_volume_24h = sum(float(m.volume_24h or 0) for m in recent_metrics) / len(recent_metrics)
            
            # Determine signals
            if avg_price_change_24h > 5 and avg_volume_24h > 1000:
                signal = "BUY"
                strength = min(0.9, 0.5 + abs(avg_price_change_24h) / 20)
            elif avg_price_change_24h < -5:
                signal = "SELL"
                strength = min(0.9, 0.5 + abs(avg_price_change_24h) / 20)
            else:
                signal = "HOLD"
                strength = 0.5
                
            return {
                "signal": signal,
                "strength": strength,
                "avg_price_change_24h": avg_price_change_24h,
                "avg_volume_24h": avg_volume_24h,
                "calculated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            print(f"Error calculating token signals: {e}")
            return None

    async def _get_historical_token_metrics(self, db: Session, token_id: str, 
                                           days: int = 7, use_history_table: bool = True, daily_sample: bool = False) -> List[Dict[str, Any]]:
        """Get historical TokenMetric records for trend analysis"""
        try:
            if use_history_table:
                # Use dedicated history table for better performance and more data
                return await self._get_historical_token_metrics_from_history(db, token_id, days, daily_sample)
            
            # Fallback to current TokenMetric table (legacy method)
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Get all TokenMetric records for this token
            metrics = db.query(TokenMetric).filter(
                TokenMetric.token_id == token_id,
                TokenMetric.last_calculation_at >= cutoff_date
            ).order_by(desc(TokenMetric.last_calculation_at)).all()
            
            historical_data = []
            for metric in metrics:
                historical_data.append({
                    "timestamp": metric.last_calculation_at.isoformat() if metric.last_calculation_at else None,
                    "avg_price_usd": float(metric.avg_price_usd or 0),
                    "weighted_price_usd": float(metric.weighted_price_usd or 0),
                    "total_volume_24h": float(metric.total_volume_24h or 0),
                    "total_liquidity_usd": float(metric.total_liquidity_usd or 0),
                    "pools_count": metric.pools_count,
                    "data_source": "current_table"
                })
            
            return historical_data
            
        except Exception as e:
            print(f"Error getting historical token metrics: {e}")
            return []

    async def _calculate_token_metrics_enhanced(self, db: Session, token_id: str, 
                                              moralis_stats: Optional[Dict[str, Any]] = None) -> Optional[TokenMetric]:
        """Calculate enhanced token metrics using pool data and external sources"""
        try:
            # Start with basic calculation from pool data
            token_metric = await self._calculate_token_metrics(db, token_id)
            
            if not token_metric:
                return None
                
            # Enhance with Moralis data if available
            if moralis_stats:
                # Update core price and liquidity data
                if moralis_stats.get("usd_price", 0) > 0:
                    token_metric.usd_price_moralis = Decimal(str(moralis_stats["usd_price"]))
                    token_metric.weighted_price_usd = Decimal(str(moralis_stats["usd_price"]))
                    
                if moralis_stats.get("total_liquidity_usd", 0) > 0:
                    token_metric.total_liquidity_usd_moralis = Decimal(str(moralis_stats["total_liquidity_usd"]))
                    token_metric.total_liquidity_usd = Decimal(str(moralis_stats["total_liquidity_usd"]))
                    
                if moralis_stats.get("total_fdv", 0) > 0:
                    token_metric.total_fdv = Decimal(str(moralis_stats["total_fdv"]))
                    token_metric.market_cap = Decimal(str(moralis_stats["total_fdv"]))
                
                # Buy/Sell Volume data (5m, 1h, 6h, 24h)
                token_metric.buy_volume_5m = Decimal(str(moralis_stats.get("buy_volume_5m", 0)))
                token_metric.buy_volume_1h = Decimal(str(moralis_stats.get("buy_volume_1h", 0)))
                token_metric.buy_volume_6h = Decimal(str(moralis_stats.get("buy_volume_6h", 0)))
                token_metric.buy_volume_24h = Decimal(str(moralis_stats.get("buy_volume_24h", 0)))
                
                token_metric.sell_volume_5m = Decimal(str(moralis_stats.get("sell_volume_5m", 0)))
                token_metric.sell_volume_1h = Decimal(str(moralis_stats.get("sell_volume_1h", 0)))
                token_metric.sell_volume_6h = Decimal(str(moralis_stats.get("sell_volume_6h", 0)))
                token_metric.sell_volume_24h = Decimal(str(moralis_stats.get("sell_volume_24h", 0)))
                
                # Buyer/Seller counts
                token_metric.total_buyers_5m = moralis_stats.get("total_buyers_5m", 0)
                token_metric.total_buyers_1h = moralis_stats.get("total_buyers_1h", 0)
                token_metric.total_buyers_6h = moralis_stats.get("total_buyers_6h", 0)
                token_metric.total_buyers_24h = moralis_stats.get("total_buyers_24h", 0)
                
                token_metric.total_sellers_5m = moralis_stats.get("total_sellers_5m", 0)
                token_metric.total_sellers_1h = moralis_stats.get("total_sellers_1h", 0)
                token_metric.total_sellers_6h = moralis_stats.get("total_sellers_6h", 0)
                token_metric.total_sellers_24h = moralis_stats.get("total_sellers_24h", 0)
                
                # Transaction counts
                token_metric.total_buys_5m = moralis_stats.get("total_buys_5m", 0)
                token_metric.total_buys_1h = moralis_stats.get("total_buys_1h", 0)
                token_metric.total_buys_6h = moralis_stats.get("total_buys_6h", 0)
                token_metric.total_buys_24h = moralis_stats.get("total_buys_24h", 0)
                
                token_metric.total_sells_5m = moralis_stats.get("total_sells_5m", 0)
                token_metric.total_sells_1h = moralis_stats.get("total_sells_1h", 0)
                token_metric.total_sells_6h = moralis_stats.get("total_sells_6h", 0)
                token_metric.total_sells_24h = moralis_stats.get("total_sells_24h", 0)
                
                # Unique wallets
                token_metric.unique_wallets_5m = moralis_stats.get("unique_wallets_5m", 0)
                token_metric.unique_wallets_1h = moralis_stats.get("unique_wallets_1h", 0)
                token_metric.unique_wallets_6h = moralis_stats.get("unique_wallets_6h", 0)
                token_metric.unique_wallets_24h = moralis_stats.get("unique_wallets_24h", 0)
                
                # Price changes - with sanitization to prevent database overflow
                token_metric.price_change_5m = Decimal(str(self._sanitize_price_change(moralis_stats.get("price_change_5m", 0))))
                token_metric.price_change_1h = Decimal(str(self._sanitize_price_change(moralis_stats.get("price_change_1h", 0))))
                token_metric.price_change_6h = Decimal(str(self._sanitize_price_change(moralis_stats.get("price_change_6h", 0))))
                token_metric.price_change_24h = Decimal(str(self._sanitize_price_change(moralis_stats.get("price_change_24h", 0))))
                
                # Holder stats from combined data
                token_metric.holder_count = moralis_stats.get("total_holders", 0)
                
                # Holder changes - with sanitization for percentage fields
                token_metric.holder_change_5m = moralis_stats.get("holder_change_5m", 0)
                token_metric.holder_change_5m_percent = Decimal(str(self._sanitize_price_change(moralis_stats.get("holder_change_5m_percent", 0))))
                token_metric.holder_change_1h = moralis_stats.get("holder_change_1h", 0)
                token_metric.holder_change_1h_percent = Decimal(str(self._sanitize_price_change(moralis_stats.get("holder_change_1h_percent", 0))))
                token_metric.holder_change_6h = moralis_stats.get("holder_change_6h", 0)
                token_metric.holder_change_6h_percent = Decimal(str(self._sanitize_price_change(moralis_stats.get("holder_change_6h_percent", 0))))
                token_metric.holder_change_24h = moralis_stats.get("holder_change_24h", 0)
                token_metric.holder_change_24h_percent = Decimal(str(self._sanitize_price_change(moralis_stats.get("holder_change_24h_percent", 0))))
                token_metric.holder_change_3d = moralis_stats.get("holder_change_3d", 0)
                token_metric.holder_change_3d_percent = Decimal(str(self._sanitize_price_change(moralis_stats.get("holder_change_3d_percent", 0))))
                token_metric.holder_change_7d = moralis_stats.get("holder_change_7d", 0)
                token_metric.holder_change_7d_percent = Decimal(str(self._sanitize_price_change(moralis_stats.get("holder_change_7d_percent", 0))))
                token_metric.holder_change_30d = moralis_stats.get("holder_change_30d", 0)
                token_metric.holder_change_30d_percent = Decimal(str(self._sanitize_price_change(moralis_stats.get("holder_change_30d_percent", 0))))
                
                # Holder distribution
                token_metric.whales_count = moralis_stats.get("whales_count", 0)
                token_metric.sharks_count = moralis_stats.get("sharks_count", 0)
                token_metric.dolphins_count = moralis_stats.get("dolphins_count", 0)
                token_metric.fish_count = moralis_stats.get("fish_count", 0)
                token_metric.octopus_count = moralis_stats.get("octopus_count", 0)
                token_metric.crabs_count = moralis_stats.get("crabs_count", 0)
                token_metric.shrimps_count = moralis_stats.get("shrimps_count", 0)
                
                # Supply distribution
                token_metric.top10_supply_percent = Decimal(str(moralis_stats.get("top10_supply_percent", 0)))
                token_metric.top25_supply_percent = Decimal(str(moralis_stats.get("top25_supply_percent", 0)))
                token_metric.top50_supply_percent = Decimal(str(moralis_stats.get("top50_supply_percent", 0)))
                token_metric.top100_supply_percent = Decimal(str(moralis_stats.get("top100_supply_percent", 0)))
                token_metric.top250_supply_percent = Decimal(str(moralis_stats.get("top250_supply_percent", 0)))
                token_metric.top500_supply_percent = Decimal(str(moralis_stats.get("top500_supply_percent", 0)))
                
                # Holder acquisition stats
                token_metric.holders_by_swap = moralis_stats.get("holders_by_swap", 0)
                token_metric.holders_by_transfer = moralis_stats.get("holders_by_transfer", 0)
                token_metric.holders_by_airdrop = moralis_stats.get("holders_by_airdrop", 0)
                
                # Update timestamp
                token_metric.last_calculation_at = datetime.now(timezone.utc)
                
                db.commit()
                db.refresh(token_metric)
                
                # Save enhanced metrics to history
                await self._save_token_metrics_history(db, token_metric, "enhanced_moralis")
                
            return token_metric
            
        except Exception as e:
            print(f"Error calculating enhanced token metrics: {e}")
            db.rollback()
            return None

    async def _calculate_token_signals_enhanced(self, db: Session, token_id: str,
                                              historical_metrics: List[Dict[str, Any]],
                                              moralis_stats: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Calculate enhanced token trading signals using historical data, technical indicators and external sources"""
        try:
            # STEP 1: Calculate technical indicators using TokenSignalCalculator
            technical_indicators = self._calculate_technical_indicators(historical_metrics, moralis_stats)
            
            # STEP 2: Start with basic signal calculation
            basic_signals = await self._calculate_token_signals(db, token_id)
            
            if not basic_signals:
                return None
                
            # STEP 3: Enhance signals with historical trend analysis
            price_trend = self._analyze_price_trend(historical_metrics)
            volume_trend = self._analyze_volume_trend(historical_metrics)
            
            # STEP 4: Enhance with Moralis analytics if available
            moralis_signals = {}
            if moralis_stats:
                # Analyze buy/sell ratio
                buy_sell_ratio = moralis_stats.get("buy_sell_ratio_24h", 1.0)
                net_volume = moralis_stats.get("net_volume_24h", 0)
                
                # Holder analysis
                holder_change_24h = moralis_stats.get("holder_change_24h_percent", 0)
                
                # Price changes from multiple timeframes
                price_change_5m = moralis_stats.get("price_change_5m", 0)
                price_change_1h = moralis_stats.get("price_change_1h", 0)
                price_change_24h = moralis_stats.get("price_change_24h", 0)
                
                moralis_signals = {
                    "buy_sell_ratio_24h": buy_sell_ratio,
                    "net_volume_24h": net_volume,
                    "holder_change_24h_percent": holder_change_24h,
                    "price_change_5m": price_change_5m,
                    "price_change_1h": price_change_1h,
                    "price_change_24h": price_change_24h
                }
            
            # STEP 5: Combine all signals including technical indicators
            enhanced_signal = self._combine_signals_with_indicators(
                basic_signals, price_trend, volume_trend, moralis_signals, technical_indicators
            )
            
            # STEP 6: Save technical indicators to TokenMetric for LLM decision making
            await self._save_technical_indicators_to_metrics(db, token_id, technical_indicators)
            
            return enhanced_signal
            
        except Exception as e:
            print(f"Error calculating enhanced token signals: {e}")
            return None

    def _analyze_price_trend(self, historical_metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze price trend from historical data"""
        if len(historical_metrics) < 2:
            return {"trend": "UNKNOWN", "strength": 0.0}
            
        prices = [m["weighted_price_usd"] for m in historical_metrics if m["weighted_price_usd"] > 0]
        
        if len(prices) < 2:
            return {"trend": "UNKNOWN", "strength": 0.0}
            
        # Calculate trend direction
        price_changes = []
        for i in range(1, len(prices)):
            change = (prices[i] - prices[i-1]) / prices[i-1] * 100
            price_changes.append(change)
            
        avg_change = sum(price_changes) / len(price_changes)
        
        if avg_change > 2:
            trend = "UP"
        elif avg_change < -2:
            trend = "DOWN"
        else:
            trend = "STABLE"
            
        strength = min(0.9, abs(avg_change) / 10)
        
        return {"trend": trend, "strength": strength, "avg_change": avg_change}

    def _analyze_volume_trend(self, historical_metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze volume trend from historical data"""
        if len(historical_metrics) < 2:
            return {"trend": "UNKNOWN", "strength": 0.0}
            
        volumes = [m["total_volume_24h"] for m in historical_metrics if m["total_volume_24h"] > 0]
        
        if len(volumes) < 2:
            return {"trend": "UNKNOWN", "strength": 0.0}
            
        # Calculate volume trend
        recent_avg = sum(volumes[:len(volumes)//2]) / (len(volumes)//2)
        older_avg = sum(volumes[len(volumes)//2:]) / (len(volumes) - len(volumes)//2)
        
        if older_avg > 0:
            volume_change = (recent_avg - older_avg) / older_avg * 100
        else:
            volume_change = 0
            
        if volume_change > 20:
            trend = "INCREASING"
        elif volume_change < -20:
            trend = "DECREASING"
        else:
            trend = "STABLE"
            
        strength = min(0.9, abs(volume_change) / 50)
        
        return {"trend": trend, "strength": strength, "change": volume_change}

    def _calculate_technical_indicators(self, historical_metrics: List[Dict[str, Any]], 
                                       moralis_stats: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Calculate technical indicators using TokenSignalCalculator"""
        try:
            # Prepare data for indicator calculation
            indicator_data = []
            
            # Use historical metrics first
            for metric in historical_metrics:
                indicator_data.append({
                    'price_usd': metric.get('weighted_price_usd', 0),
                    'volume_24h': metric.get('total_volume_24h', 0),
                    'holders': metric.get('holder_count', 0)
                })
            
            # Add current Moralis data if available
            if moralis_stats:
                current_data = {
                    'price_usd': moralis_stats.get('usd_price', 0),
                    'volume_24h': moralis_stats.get('total_volume_24h', 0),
                    'holders': moralis_stats.get('total_holders', 0)
                }
                indicator_data.append(current_data)
            
            # Calculate indicators using TokenSignalCalculator
            indicators = self.signal_calculator.calculate_indicators(indicator_data)
            
            # Calculate additional volatility indicator
            prices = [float(data.get('price_usd', 0)) for data in indicator_data]
            volatility = self._calculate_volatility(prices) if len(prices) > 1 else 0.0
            
            indicators['volatility_24h'] = volatility
            
            return indicators
            
        except Exception as e:
            print(f"Error calculating technical indicators: {e}")
            return self.signal_calculator._default_indicators()
    
    def _calculate_volatility(self, prices: List[float]) -> float:
        """Calculate price volatility"""
        if len(prices) < 2:
            return 0.0
        
        # Calculate returns
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] != 0:
                returns.append((prices[i] - prices[i-1]) / prices[i-1])
        
        if not returns:
            return 0.0
        
        # Calculate standard deviation of returns
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        volatility = (variance ** 0.5) * 100  # Convert to percentage
        
        return volatility

    async def _save_technical_indicators_to_metrics(self, db: Session, token_id: str, 
                                                   indicators: Dict[str, Any]) -> bool:
        """Save technical indicators to TokenMetric table for LLM decision making"""
        try:
            # Get or create token metric
            token_metric = db.query(TokenMetric).filter(TokenMetric.token_id == token_id).first()
            
            if not token_metric:
                # Create new token metric if doesn't exist
                token_metric = TokenMetric(
                    token_id=token_id,
                    trend_direction="sideways"  # Set default value to satisfy constraint
                )
                db.add(token_metric)
            
            # Update technical indicators
            token_metric.rsi_14d = indicators.get('rsi', 50.0)
            token_metric.ma_7d = indicators.get('ma_7d', 0.0)
            token_metric.ma_30d = indicators.get('ma_30d', 0.0)
            token_metric.volatility_24h = indicators.get('volatility_24h', 0.0)
            token_metric.breakout_signal = indicators.get('breakout', False)
            
            db.commit()
            db.refresh(token_metric)
            
            return True
            
        except Exception as e:
            print(f"Error saving technical indicators to metrics: {e}")
            db.rollback()
            return False

    def _combine_signals_with_indicators(self, basic_signals: Dict[str, Any], price_trend: Dict[str, Any], 
                                        volume_trend: Dict[str, Any], moralis_signals: Dict[str, Any],
                                        technical_indicators: Dict[str, Any]) -> Dict[str, Any]:
        """Combine all signals including technical indicators for enhanced decision making"""
        try:
            # Start with basic signal
            base_signal = basic_signals.get("signal", "HOLD")
            base_strength = basic_signals.get("strength", 0.5)
            
            # Technical indicator adjustments
            rsi = technical_indicators.get('rsi', 50.0)
            breakout = technical_indicators.get('breakout', False)
            volatility = technical_indicators.get('volatility_24h', 0.0)
            
            # RSI adjustments
            rsi_adjustment = 0
            if rsi > 70:  # Overbought
                rsi_adjustment = -0.1
            elif rsi < 30:  # Oversold
                rsi_adjustment = 0.1
            
            # Breakout signal adjustment
            breakout_adjustment = 0.15 if breakout else 0
            
            # Volatility adjustment (high volatility increases uncertainty)
            volatility_adjustment = 0
            if volatility > 10:  # High volatility
                volatility_adjustment = -0.05
            elif volatility < 3:  # Low volatility
                volatility_adjustment = 0.05
            
            # Price trend adjustment
            trend_adjustment = 0
            if price_trend["trend"] == "UP":
                trend_adjustment = 0.2 * price_trend["strength"]
            elif price_trend["trend"] == "DOWN":
                trend_adjustment = -0.2 * price_trend["strength"]
                
            # Volume trend adjustment
            volume_adjustment = 0
            if volume_trend["trend"] == "INCREASING":
                volume_adjustment = 0.1 * volume_trend["strength"]
            elif volume_trend["trend"] == "DECREASING":
                volume_adjustment = -0.1 * volume_trend["strength"]
                
            # Moralis signals adjustment
            moralis_adjustment = 0
            if moralis_signals:
                buy_sell_ratio = moralis_signals.get("buy_sell_ratio_24h", 1.0)
                holder_change = moralis_signals.get("holder_change_24h_percent", 0)
                
                # Positive signals
                if buy_sell_ratio > 1.2:  # More buying than selling
                    moralis_adjustment += 0.15
                elif buy_sell_ratio < 0.8:  # More selling than buying
                    moralis_adjustment -= 0.15
                    
                if holder_change > 5:  # Increasing holders
                    moralis_adjustment += 0.1
                elif holder_change < -5:  # Decreasing holders
                    moralis_adjustment -= 0.1
            
            # Calculate final strength with all adjustments
            final_strength = (base_strength + rsi_adjustment + breakout_adjustment + 
                            volatility_adjustment + trend_adjustment + volume_adjustment + moralis_adjustment)
            final_strength = max(0.0, min(1.0, final_strength))  # Clamp to [0, 1]
            
            # Determine final signal
            if final_strength > 0.7:
                final_signal = "BUY"
            elif final_strength < 0.3:
                final_signal = "SELL"
            else:
                final_signal = "HOLD"
                
            return {
                "signal": final_signal,
                "strength": final_strength,
                "components": {
                    "basic": basic_signals,
                    "price_trend": price_trend,
                    "volume_trend": volume_trend,
                    "moralis": moralis_signals,
                    "technical_indicators": technical_indicators
                },
                "adjustments": {
                    "rsi_adjustment": rsi_adjustment,
                    "breakout_adjustment": breakout_adjustment,
                    "volatility_adjustment": volatility_adjustment,
                    "trend_adjustment": trend_adjustment,
                    "volume_adjustment": volume_adjustment,
                    "moralis_adjustment": moralis_adjustment
                },
                "calculated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            print(f"Error combining signals with indicators: {e}")
            # Return basic signals as fallback
            return basic_signals

    def _combine_signals(self, basic_signals: Dict[str, Any], price_trend: Dict[str, Any], 
                        volume_trend: Dict[str, Any], moralis_signals: Dict[str, Any]) -> Dict[str, Any]:
        """Combine all signals for final trading decision"""
        try:
            # Start with basic signal
            base_signal = basic_signals.get("signal", "HOLD")
            base_strength = basic_signals.get("strength", 0.5)
            
            # Adjust based on price trend
            trend_adjustment = 0
            if price_trend["trend"] == "UP":
                trend_adjustment = 0.2 * price_trend["strength"]
            elif price_trend["trend"] == "DOWN":
                trend_adjustment = -0.2 * price_trend["strength"]
                
            # Adjust based on volume trend
            volume_adjustment = 0
            if volume_trend["trend"] == "INCREASING":
                volume_adjustment = 0.1 * volume_trend["strength"]
            elif volume_trend["trend"] == "DECREASING":
                volume_adjustment = -0.1 * volume_trend["strength"]
                
            # Adjust based on Moralis signals
            moralis_adjustment = 0
            if moralis_signals:
                buy_sell_ratio = moralis_signals.get("buy_sell_ratio_24h", 1.0)
                holder_change = moralis_signals.get("holder_change_24h_percent", 0)
                
                # Positive signals
                if buy_sell_ratio > 1.2:  # More buying than selling
                    moralis_adjustment += 0.15
                elif buy_sell_ratio < 0.8:  # More selling than buying
                    moralis_adjustment -= 0.15
                    
                if holder_change > 5:  # Increasing holders
                    moralis_adjustment += 0.1
                elif holder_change < -5:  # Decreasing holders
                    moralis_adjustment -= 0.1
            
            # Calculate final strength
            final_strength = base_strength + trend_adjustment + volume_adjustment + moralis_adjustment
            final_strength = max(0.0, min(1.0, final_strength))  # Clamp to [0, 1]
            
            # Determine final signal
            if final_strength > 0.7:
                final_signal = "BUY"
            elif final_strength < 0.3:
                final_signal = "SELL"
            else:
                final_signal = "HOLD"
                
            return {
                "signal": final_signal,
                "strength": final_strength,
                "components": {
                    "basic": basic_signals,
                    "price_trend": price_trend,
                    "volume_trend": volume_trend,
                    "moralis": moralis_signals
                },
                "adjustments": {
                    "trend_adjustment": trend_adjustment,
                    "volume_adjustment": volume_adjustment,
                    "moralis_adjustment": moralis_adjustment
                },
                "calculated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            print(f"Error combining signals: {e}")
            # Return basic signals as fallback
            return basic_signals

    async def _save_moralis_stats_to_history(self, db: Session, token_id: str,
                                            moralis_stats: Dict[str, Any]) -> bool:
        """Save Moralis stats directly to history table"""
        try:
            history = TokenMetricsHistory(
                token_id=token_id,
                
                # Core price and volume metrics from Moralis
                weighted_price_usd=Decimal(str(moralis_stats.get("usd_price", 0))),
                total_volume_24h=Decimal(str(moralis_stats.get("total_volume_24h", 0))),
                total_liquidity_usd=Decimal(str(moralis_stats.get("total_liquidity_usd", 0))),
                market_cap=Decimal(str(moralis_stats.get("total_fdv", 0))),
                
                # Price changes - with sanitization to prevent database overflow
                price_change_5m=Decimal(str(self._sanitize_price_change(moralis_stats.get("price_change_5m", 0)))),
                price_change_1h=Decimal(str(self._sanitize_price_change(moralis_stats.get("price_change_1h", 0)))),
                price_change_6h=Decimal(str(self._sanitize_price_change(moralis_stats.get("price_change_6h", 0)))),
                price_change_24h=Decimal(str(self._sanitize_price_change(moralis_stats.get("price_change_24h", 0)))),
                
                # Buy/Sell volumes
                buy_volume_24h=Decimal(str(moralis_stats.get("buy_volume_24h", 0))),
                sell_volume_24h=Decimal(str(moralis_stats.get("sell_volume_24h", 0))),
                
                # Trading activity
                total_buyers_24h=moralis_stats.get("total_buyers_24h", 0),
                total_sellers_24h=moralis_stats.get("total_sellers_24h", 0),
                unique_wallets_24h=moralis_stats.get("unique_wallets_24h", 0),
                
                # Holder metrics
                holder_count=moralis_stats.get("total_holders", 0),
                holder_change_24h_percent=Decimal(str(self._sanitize_price_change(moralis_stats.get("holder_change_24h_percent", 0)))),
                top10_supply_percent=Decimal(str(moralis_stats.get("top10_supply_percent", 0))),
                whales_count=moralis_stats.get("whales_count", 0),
                
                # Meta
                pools_count=0,  # Will be updated later from pool data
                data_source="moralis",
                recorded_at=datetime.now(timezone.utc)
            )
            
            db.add(history)
            db.commit()
            return True
            
        except Exception as e:
            print(f"Error saving Moralis stats to history: {e}")
            db.rollback()
            return False

    async def _save_token_metrics_history(self, db: Session, token_metric: TokenMetric, 
                                         source: str = "basic") -> bool:
        """Save enhanced token metrics to history table"""
        try:
            history = TokenMetricsHistory(
                token_id=token_metric.token_id,
                
                # Core metrics 
                weighted_price_usd=token_metric.weighted_price_usd,
                total_volume_24h=token_metric.total_volume_24h,
                total_liquidity_usd=token_metric.total_liquidity_usd,
                market_cap=token_metric.market_cap,
                
                # Key trend indicators
                price_change_24h=token_metric.price_change_24h,
                signal_strength=token_metric.signal_strength,
                trend_direction=token_metric.trend_direction,
                
                # Enhanced Moralis metrics (critical ones for historical analysis)
                buy_volume_24h=token_metric.buy_volume_24h,
                sell_volume_24h=token_metric.sell_volume_24h,
                holder_change_24h_percent=token_metric.holder_change_24h_percent,
                
                # Additional key Moralis metrics
                total_buyers_24h=token_metric.total_buyers_24h,
                total_sellers_24h=token_metric.total_sellers_24h,
                unique_wallets_24h=token_metric.unique_wallets_24h,
                holder_count=token_metric.holder_count,
                
                # Enhanced price change tracking
                price_change_5m=token_metric.price_change_5m,
                price_change_1h=token_metric.price_change_1h,
                price_change_6h=token_metric.price_change_6h,
                
                # Key holder distribution
                top10_supply_percent=token_metric.top10_supply_percent,
                whales_count=token_metric.whales_count,
                
                # Meta
                pools_count=token_metric.pools_count,
                data_source=source,
                recorded_at=datetime.now(timezone.utc)
            )
            
            db.add(history)
            db.commit()
            return True
            
        except Exception as e:
            print(f"Error saving token metrics history: {e}")
            db.rollback()
            return False

    async def _get_historical_token_metrics_from_history(self, db: Session, token_id: str, 
                                                       days: int = 30, daily_sample: bool = False) -> List[Dict[str, Any]]:
            """Get historical TokenMetric records from history table for comprehensive analysis"""
            try:
                # Get historical metrics from the last N days
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
                
                # Get historical records from TokenMetricsHistory table
                history_records = db.query(TokenMetricsHistory).filter(
                    TokenMetricsHistory.token_id == token_id,
                    TokenMetricsHistory.recorded_at >= cutoff_date
                ).order_by(desc(TokenMetricsHistory.recorded_at)).all()
                
                historical_data = []
                seen_dates = set()
                for record in history_records:
                    record_date = record.recorded_at.date()
                    if daily_sample and record_date in seen_dates:
                        print(f"Skipping duplicate record at date: {record.recorded_at}")
                        continue
                    seen_dates.add(record_date)
                    historical_data.append({
                        "timestamp": record.recorded_at.isoformat(),
                        "weighted_price_usd": float(record.weighted_price_usd or 0),
                        "total_volume_24h": float(record.total_volume_24h or 0),
                        "total_liquidity_usd": float(record.total_liquidity_usd or 0),
                        "market_cap": float(record.market_cap or 0),
                        "pools_count": record.pools_count,
                        "data_source": record.data_source,
                        
                        # Key trend indicators
                        "price_change_24h": float(record.price_change_24h or 0),
                        "signal_strength": record.signal_strength,
                        "trend_direction": record.trend_direction,
                        
                        # Important Moralis metrics
                        "buy_volume_24h": float(record.buy_volume_24h or 0),
                        "sell_volume_24h": float(record.sell_volume_24h or 0),
                        "holder_change_24h_percent": float(record.holder_change_24h_percent or 0)
                    })
                
                return historical_data
                
            except Exception as e:
                print(f"Error getting historical token metrics from history: {e}")
                return []

    async def get_token_decision_data(self, db: Session, token_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive token data for LLM decision making from database"""
        try:
            # Get token basic info
            token = db.query(Token).filter(Token.id == token_id).first()
            if not token:
                return None
                
            # Get latest token metrics with technical indicators
            token_metric = db.query(TokenMetric).filter(TokenMetric.token_id == token_id).first()
            
            # Get historical metrics for trend analysis (last 30 days)
            historical_metrics = await self._get_historical_token_metrics(db, token_id, days=30, daily_sample=True)
            
            # Get active pools
            pools = db.query(TokenPool).filter(
                TokenPool.base_token_id == token_id,
                TokenPool.is_active == True
            ).all()
            
            # Get latest pool metrics
            pool_metrics = []
            for pool in pools:
                latest_metric = db.query(PoolMetric)\
                    .filter(PoolMetric.pool_id == pool.id)\
                    .order_by(desc(PoolMetric.updated_at))\
                    .first()
                if latest_metric:
                    pool_metrics.append({
                        "pool_id": str(pool.id),
                        "dex": pool.dex,
                        "price_usd": float(latest_metric.price_usd or 0),
                        "volume_24h": float(latest_metric.volume_24h or 0),
                        "liquidity_usd": float(latest_metric.liquidity_usd or 0),
                        "price_change_24h": float(latest_metric.price_change_24h or 0),
                        "market_cap": float(latest_metric.market_cap or 0)
                    })
            
            # Prepare comprehensive decision data
            decision_data = {
                "token_info": {
                    "id": str(token.id),
                    "name": token.name,
                    "symbol": token.symbol,
                    "contract_address": token.contract_address,
                    "chain": token.chain
                },
                "current_metrics": {},
                "technical_indicators": {},
                "moralis_data": {},
                "pool_data": pool_metrics,
                "historical_data": historical_metrics,
                "risk_factors": {},
                "data_completeness": {}
            }
            
            # Fill current metrics if available
            if token_metric:
                decision_data["current_metrics"] = {
                    "avg_price_usd": float(token_metric.avg_price_usd or 0),
                    "weighted_price_usd": float(token_metric.weighted_price_usd or 0),
                    "total_volume_24h": float(token_metric.total_volume_24h or 0),
                    "total_liquidity_usd": float(token_metric.total_liquidity_usd or 0),
                    "market_cap": float(token_metric.market_cap or 0),
                    "pools_count": token_metric.pools_count,
                    "last_updated": token_metric.last_calculation_at.isoformat() if token_metric.last_calculation_at else None
                }
                
                # Technical indicators
                decision_data["technical_indicators"] = {
                    "rsi_14d": token_metric.rsi_14d,
                    "ma_7d": token_metric.ma_7d,
                    "ma_30d": token_metric.ma_30d,
                    "volatility_24h": token_metric.volatility_24h,
                    "breakout_signal": token_metric.breakout_signal,
                    "trend_direction": token_metric.trend_direction,
                    "signal_strength": token_metric.signal_strength
                }
                
                # Moralis comprehensive data
                decision_data["moralis_data"] = {
                    "price_changes": {
                        "5m": float(token_metric.price_change_5m or 0),
                        "1h": float(token_metric.price_change_1h or 0),
                        "6h": float(token_metric.price_change_6h or 0),
                        "24h": float(token_metric.price_change_24h or 0)
                    },
                    "volume_analysis": {
                        "buy_volume_24h": float(token_metric.buy_volume_24h or 0),
                        "sell_volume_24h": float(token_metric.sell_volume_24h or 0),
                        "buy_sell_ratio": float(token_metric.buy_volume_24h or 0) / float(token_metric.sell_volume_24h or 1),
                        "net_volume": float(token_metric.buy_volume_24h or 0) - float(token_metric.sell_volume_24h or 0)
                    },
                    "trader_activity": {
                        "total_buyers_24h": token_metric.total_buyers_24h,
                        "total_sellers_24h": token_metric.total_sellers_24h,
                        "unique_wallets_24h": token_metric.unique_wallets_24h,
                        "trader_ratio": token_metric.total_buyers_24h / max(token_metric.total_sellers_24h, 1) if token_metric.total_sellers_24h else 0
                    },
                    "holder_analysis": {
                        "total_holders": token_metric.holder_count,
                        "holder_change_24h": token_metric.holder_change_24h,
                        "holder_change_24h_percent": float(token_metric.holder_change_24h_percent or 0),
                        "holder_change_7d": token_metric.holder_change_7d,
                        "holder_change_7d_percent": float(token_metric.holder_change_7d_percent or 0)
                    },
                    "distribution": {
                        "whales_count": token_metric.whales_count,
                        "top10_supply_percent": float(token_metric.top10_supply_percent or 0),
                        "top25_supply_percent": float(token_metric.top25_supply_percent or 0),
                        "concentration_risk": "HIGH" if float(token_metric.top10_supply_percent or 0) > 50 else "MEDIUM" if float(token_metric.top10_supply_percent or 0) > 30 else "LOW"
                    }
                }
                
                # Risk factors analysis
                decision_data["risk_factors"] = {
                    "volatility_level": "HIGH" if (token_metric.volatility_24h or 0) > 10 else "MEDIUM" if (token_metric.volatility_24h or 0) > 5 else "LOW",
                    "rsi_overbought": (token_metric.rsi_14d or 50) > 70,
                    "rsi_oversold": (token_metric.rsi_14d or 50) < 30,
                    "concentration_risk": float(token_metric.top10_supply_percent or 0) > 50,
                    "holder_decline": (token_metric.holder_change_24h_percent or 0) < -5,
                    "low_liquidity": float(token_metric.total_liquidity_usd or 0) < 10000
                }
            
            # Data completeness check
            decision_data["data_completeness"] = {
                "has_token_metrics": token_metric is not None,
                "has_historical_data": len(historical_metrics) > 0,
                "has_pool_data": len(pool_metrics) > 0,
                "has_technical_indicators": token_metric and token_metric.rsi_14d is not None,
                "has_moralis_data": token_metric and token_metric.buy_volume_24h is not None,
                "data_age_hours": self._calculate_data_age_hours(token_metric.last_calculation_at) if token_metric and token_metric.last_calculation_at else None
            }
            
            return decision_data
            
        except Exception as e:
            print(f"Error getting token decision data: {e}")
            return None

    async def close(self):
        """Close all data provider connections"""
        try:
            await self.dex_screener.close()
            await self.moralis.close()
            await self.birdeye.close()
        except Exception as e:
            print(f"Warning: Error closing connections: {e}")

    async def process_chat_message(self, db: Session, message: str, include_pools: bool = False) -> str:
        """
        Process chat message and return response data for LLM analysis
        Enhanced version: Get token list → LLM token identification → Get decision data → LLM analysis
        
        Args:
            db: Database session
            message: User's chat message
            include_pools: Whether to include detailed pool analysis
            
        Returns:
            Dict containing response, signal_data, intent, and optional pool_analysis
        """
        try:
            token_analyzer = TokenDecisionAnalyzer()
            
            # Step 1: Get available token list from database
            available_tokens = self._get_available_tokens_list(db)
            
            if not available_tokens:
                return f"No tokens found in the database. Please add some tokens first. Available tokens: {', '.join([t['symbol'] for t in available_tokens])}"
            
            # Step 2: Use LLM to determine which token the user is asking about
            llm_token_analysis = await token_analyzer.llm_identify_target_token(message, available_tokens)
            
            print(f"LLM token analysis: {llm_token_analysis}")

            if not llm_token_analysis.get("token_found"):
                return f"I couldn't identify a specific token from your message. Available tokens: {', '.join([t['symbol'] for t in available_tokens])}"
            
            target_token_symbol = llm_token_analysis.get("token_symbol")
            
            # Step 3: Check if the identified token exists in our list
            token_exists = any(token['symbol'].upper() == target_token_symbol.upper() for token in available_tokens)
            
            if not token_exists:
                similar_tokens = [t['symbol'] for t in available_tokens if target_token_symbol.lower() in t['symbol'].lower() or t['symbol'].lower() in target_token_symbol.lower()]
                suggestion = f" Did you mean: {', '.join(similar_tokens[:3])}?" if similar_tokens else ""
                return f"Token {target_token_symbol} is not available in our database. {suggestion}"
            
            # Step 4: Get or create token and retrieve decision data
            token = await self.get_or_create_token(db, symbol=target_token_symbol, chain="bsc")
            if not token:
                return f"Sorry, I couldn't retrieve data for token {target_token_symbol}."

            print(f"Analysing token: {token.symbol}")                
            # Get comprehensive token analysis
            decision_data = await self.get_token_decision_data(db, str(token.id))
            
            if not decision_data:
                return f"I found {target_token_symbol} but couldn't retrieve current analysis data. The token might be new or have limited trading data."
            
            # Step 5: Use LLM to analyze the decision data and generate response
            llm_analysis = await token_analyzer.analyze_token_data_for_user_intent(
                decision_data, llm_token_analysis.get("user_intent", None)
            )

            print(f"LLM analysis: {llm_analysis}")
            
            return llm_analysis
            
        except Exception as e:
            print(f"Error processing chat message: {e}")
            return {
                "response": f"Sorry, I encountered an error while analyzing your request: {str(e)}",
                "signal_data": None,
                "intent": None,
                "pool_analysis": None,
                "available_tokens": None
            }

    def _get_available_tokens_list(self, db: Session, limit: int = 100) -> List[Dict[str, Any]]:
        """Get list of available tokens from database"""
        try:
            # limit = 0; no limit
            query = db.query(Token)
            if limit > 0:
                query = query.limit(limit)
                
            tokens = query.all()
            
            token_list = []
            for token in tokens:
                token_info = {
                    "id": str(token.id),
                    "symbol": token.symbol,
                    "name": token.name,
                    "chain": token.chain,
                    "contract_address": token.contract_address
                }
                token_list.append(token_info)
            
            return token_list
        except Exception as e:
            print(f"Error getting available tokens: {e}")
            return []

    
    def _format_pool_analysis(self, pools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format pool analysis data for response"""
        if not pools:
            return []
        
        formatted_pools = []
        for pool in pools:
            formatted_pool = {
                "dex": pool.get("dex", "Unknown"),
                "price_usd": pool.get("price_usd", 0),
                "liquidity_usd": pool.get("liquidity_usd", 0),
                "volume_24h": pool.get("volume_24h", 0),
                "price_change_24h": pool.get("price_change_24h", 0)
            }
            formatted_pools.append(formatted_pool)
        
        return formatted_pools

    

    
