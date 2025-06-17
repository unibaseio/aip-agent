#!/usr/bin/env python3
"""
AIP DEX Token Data Scheduler
Periodically fetches top tokens and updates pool data with metrics and signals
"""

import asyncio
import logging
from datetime import datetime, timedelta, UTC
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from models.database import get_db, create_tables, create_indexes, Token, TokenPool, PoolMetric
from services.token_service import TokenService
from data_aggregator.birdeye import BirdEyeProvider
from data_aggregator.dex_screener import DexScreenerProvider
from indicators.calculator import TokenSignalCalculator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TokenDataScheduler:
    """Scheduler for periodic token data updates"""
    
    def __init__(self, chain: str = "bsc", fetch_limit: int = 50):
        self.chain = chain
        self.fetch_limit = fetch_limit
        self.token_service = TokenService()
        self.birdeye = BirdEyeProvider()
        self.dex_screener = DexScreenerProvider()
        self.signal_calculator = TokenSignalCalculator()
        
    async def initialize(self):
        """Initialize database tables and indexes"""
        try:
            create_tables()
            create_indexes()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def fetch_and_save_top_tokens(self, db: Session) -> List[Token]:
        """Fetch top tokens from BirdEye and save to database with pool information"""
        logger.info(f"Fetching top {self.fetch_limit} tokens from BirdEye (chain: {self.chain})")
        
        try:
            # Get top tokens by volume from BirdEye API
            result = await self.birdeye.get_top_tokens_by_volume(
                chain=self.chain,
                limit=self.fetch_limit,
                min_liquidity=100
            )
            
            if not result or not result.get("tokens"):
                logger.error("Failed to fetch tokens from BirdEye API")
                return []
            
            tokens_data = result.get("tokens", [])
            logger.info(f"Successfully fetched {len(tokens_data)} token data from BirdEye")
            
            # Use unified method to add tokens with pool information
            saved_tokens = []
            for token_data in tokens_data:
                if token_data.get("symbol") and token_data.get("address"):
                    try:
                        # Use simplified TokenService methods
                        token = await self.token_service.get_or_create_token(
                            db=db,
                            symbol=token_data["symbol"],
                            contract_address=token_data["address"],
                            chain=self.chain,
                            name=token_data.get("name")
                        )
                        
                        if token:
                            saved_tokens.append(token)
                            logger.debug(f"Added token {token.symbol}")
                        else:
                            logger.warning(f"Failed to add token {token_data['symbol']}")
                            
                    except Exception as e:
                        logger.error(f"Error processing token {token_data.get('symbol', 'Unknown')}: {e}")
            
            logger.info(f"Successfully added {len(saved_tokens)} tokens to database")
            return saved_tokens
            
        except Exception as e:
            logger.error(f"Error fetching and saving top tokens: {e}")
            return []
    
    async def update_token_pools(self, db: Session, specific_tokens: Optional[List[Token]] = None) -> Dict[str, int]:
        """Update pool information for tokens using simplified TokenService
        
        Args:
            db: Database session
            specific_tokens: If provided, update only these tokens. Otherwise, update all tokens from database for the chain.
        """
        stats = {"updated_pools": 0, "new_pools": 0, "errors": 0, "processed_tokens": 0}
        
        # Get tokens to process - either specific tokens or all tokens from database for the chain
        if specific_tokens:
            tokens = specific_tokens
            logger.info(f"Updating pool data for {len(tokens)} specific tokens")
        else:
            # Get all tokens for this chain from database
            from models.database import Token
            tokens = db.query(Token).filter(Token.chain == self.chain).all()
            logger.info(f"Updating pool data for all {len(tokens)} tokens in chain '{self.chain}' from database")
        
        if not tokens:
            logger.warning(f"No tokens found for chain '{self.chain}'")
            return stats
        
        for token in tokens:
            try:
                stats["processed_tokens"] += 1
                
                # Use simplified TokenService method to update token pools
                result = await self.token_service.update_token_pools(
                    db=db,
                    token_id=str(token.id),
                    force_update=False
                )
                
                if result.get("success"):
                    stats["new_pools"] += result.get("new_pools", 0)
                    stats["updated_pools"] += result.get("updated_metrics", 0)
                    logger.debug(f"Updated {result.get('new_pools', 0)} pools for token {token.symbol}")
                else:
                    logger.warning(f"Failed to update pools for token {token.symbol}: {result.get('error')}")
                    stats["errors"] += 1
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error updating pools for token {token.symbol}: {e}")
                stats["errors"] += 1
        
        logger.info(f"Pool update stats: {stats}")
        return stats
    
    async def calculate_and_save_signals(self, db: Session, tokens: List[Token]) -> Dict[str, int]:
        """Calculate signals and metrics for tokens using simplified TokenService"""
        stats = {"calculated": 0, "errors": 0}
        
        logger.info(f"Calculating token metrics and signals for {len(tokens)} tokens")
        
        for token in tokens:
            try:
                # Use simplified TokenService method to update token metrics and signals
                result = await self.token_service.update_token(
                    db=db,
                    token_id=str(token.id),
                    force_update=False
                )
                
                if result.get("success") and (result.get("metrics_updated") or result.get("signals_updated")):
                    stats["calculated"] += 1
                    logger.debug(f"Calculated metrics and signals for {token.symbol}")
                else:
                    stats["errors"] += 1
                    logger.warning(f"Failed to calculate metrics for {token.symbol}: {result.get('error', 'Unknown error')}")
                
            except Exception as e:
                logger.error(f"Error calculating signals for {token.symbol}: {e}")
                stats["errors"] += 1
        
        logger.info(f"Signal calculation stats: {stats}")
        return stats
    
    async def run_single_update(self, update_all_tokens: bool = True):
        """Run a single update cycle
        
        Args:
            update_all_tokens: If True, update pools for all tokens in database.
                              If False, only update pools for newly fetched tokens.
        """
        start_time = datetime.now(UTC)
        logger.info("=" * 50)
        logger.info(f"Starting scheduled update at {start_time}")
        
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            # Step 1: Fetch and save top tokens
            new_tokens = await self.fetch_and_save_top_tokens(db)
            if not new_tokens:
                logger.warning("No new tokens fetched")
            
            # Step 2: Update pool information
            if update_all_tokens:
                # Update pools for all tokens in database (recommended approach)
                logger.info("Updating pools for all tokens in database")
                pool_stats = await self.update_token_pools(db, specific_tokens=None)
            else:
                # Only update pools for newly fetched tokens
                if not new_tokens:
                    logger.warning("No tokens to update pools for, skipping pool updates")
                    return
                logger.info("Updating pools only for newly fetched tokens")
                pool_stats = await self.update_token_pools(db, specific_tokens=new_tokens)
            
            # Step 3: Calculate metrics and signals for all tokens in database
            from models.database import Token
            all_tokens = db.query(Token).filter(Token.chain == self.chain).all()
            signal_stats = await self.calculate_and_save_signals(db, all_tokens)
            
            # Log summary
            end_time = datetime.now(UTC)
            duration = end_time - start_time
            
            logger.info("Update completed successfully!")
            logger.info(f"Duration: {duration.total_seconds():.2f} seconds")
            logger.info(f"New tokens fetched: {len(new_tokens) if new_tokens else 0}")
            logger.info(f"Tokens processed for pools: {pool_stats.get('processed_tokens', 0)}")
            logger.info(f"Pools updated: {pool_stats.get('updated_pools', 0)}")
            logger.info(f"New pools: {pool_stats.get('new_pools', 0)}")
            logger.info(f"Signals calculated: {signal_stats.get('calculated', 0)}")
            logger.info(f"Total errors: {pool_stats.get('errors', 0) + signal_stats.get('errors', 0)}")
            
        except Exception as e:
            logger.error(f"Error during scheduled update: {e}")
            raise
        finally:
            db.close()
    
    async def run_scheduler(self, interval_hours: int = 1, update_all_tokens: bool = True):
        """Run the scheduler continuously
        
        Args:
            interval_hours: Update interval in hours
            update_all_tokens: If True, update pools for all tokens in database
        """
        logger.info(f"Starting scheduler with {interval_hours} hour interval")
        logger.info(f"Update mode: {'All database tokens' if update_all_tokens else 'New tokens only'}")
        
        # Initialize database
        await self.initialize()
        
        # Run initial update
        await self.run_single_update(update_all_tokens=update_all_tokens)
        
        # Schedule periodic updates
        while True:
            try:
                await asyncio.sleep(interval_hours * 3600)  # Convert hours to seconds
                await self.run_single_update(update_all_tokens=update_all_tokens)
            except KeyboardInterrupt:
                logger.info("Scheduler interrupted by user")
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                # Wait a bit before retrying
                await asyncio.sleep(300)  # 5 minutes
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            await self.birdeye.close()
            await self.dex_screener.close()
            await self.token_service.close()
            logger.info("Resources cleaned up successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

async def main():
    """Main entry point"""
    scheduler = TokenDataScheduler(chain="bsc", fetch_limit=50)
    
    try:
        await scheduler.run_scheduler(interval_hours=1)
    except KeyboardInterrupt:
        logger.info("Shutting down scheduler...")
    finally:
        await scheduler.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 