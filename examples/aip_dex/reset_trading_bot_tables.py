#!/usr/bin/env python3
"""
Reset TradingBot tables - Drop existing tables and recreate them
This script will delete all TradingBot related tables and recreate them with the latest schema
"""

import os
import sys
from sqlalchemy import text, create_engine, inspect
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone

def reset_trading_bot_tables():
    """Drop and recreate all TradingBot related tables"""
    
    # Get database URL from environment or use default
    database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/aip_dex')
    
    try:
        # Create engine and session
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        print("🔄 Starting TradingBot tables reset...")
        print(f"   Database: {database_url}")
        
        # List of TradingBot related tables to drop (in dependency order)
        trading_bot_tables = [
            'revenue_snapshots',      # Depends on trading_bots
            'llm_decisions',          # Depends on trading_bots
            'transactions',           # Depends on trading_bots, positions
            'position_history',       # Depends on positions, trading_bots
            'positions',              # Depends on trading_bots, tokens
            'trading_bots',           # Depends on bot_owners, trading_strategies
            'trading_strategies',     # Depends on bot_owners
            'bot_owners',             # Base table
            'trading_configs'         # Independent table
        ]
        
        # Check which tables exist
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        print(f"\n📋 Existing tables: {existing_tables}")
        
        # Drop tables in reverse dependency order
        dropped_tables = []
        for table_name in trading_bot_tables:
            if table_name in existing_tables:
                try:
                    print(f"  🗑️  Dropping table: {table_name}")
                    session.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
                    session.commit()
                    dropped_tables.append(table_name)
                    print(f"  ✓ Dropped {table_name}")
                except Exception as e:
                    print(f"  ❌ Failed to drop {table_name}: {e}")
                    session.rollback()
            else:
                print(f"  ⚠️  Table {table_name} does not exist, skipping")
        
        print(f"\n🗑️  Dropped {len(dropped_tables)} tables: {dropped_tables}")
        
        # Import models to recreate tables
        print("\n🔨 Recreating tables...")
        
        # Import the database models
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from models.database import (
            Base, BotOwner, TradingStrategy, TradingBot, Position, 
            PositionHistory, Transaction, LLMDecision, RevenueSnapshot, TradingConfig
        )
        
        # Create all tables
        try:
            Base.metadata.create_all(bind=engine)
            print("  ✓ All tables created successfully")
        except Exception as e:
            print(f"  ❌ Failed to create tables: {e}")
            return False
        
        # Create indexes
        print("\n🔧 Creating indexes...")
        indexes = [
            # Bot Owner indexes
            "CREATE INDEX IF NOT EXISTS idx_bot_owners_email ON bot_owners(email)",
            "CREATE INDEX IF NOT EXISTS idx_bot_owners_wallet ON bot_owners(wallet_address)",
            "CREATE INDEX IF NOT EXISTS idx_bot_owners_active ON bot_owners(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_bot_owners_subscription ON bot_owners(subscription_tier)",
            
            # Trading Strategy indexes
            "CREATE INDEX IF NOT EXISTS idx_trading_strategies_owner ON trading_strategies(owner_id)",
            "CREATE INDEX IF NOT EXISTS idx_trading_strategies_type ON trading_strategies(strategy_type)",
            "CREATE INDEX IF NOT EXISTS idx_trading_strategies_risk ON trading_strategies(risk_level)",
            "CREATE INDEX IF NOT EXISTS idx_trading_strategies_active ON trading_strategies(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_trading_strategies_public ON trading_strategies(is_public)",
            "CREATE INDEX IF NOT EXISTS idx_trading_strategies_default ON trading_strategies(is_default)",
            
            # Trading Bot indexes
            "CREATE INDEX IF NOT EXISTS idx_trading_bots_owner ON trading_bots(owner_id)",
            "CREATE INDEX IF NOT EXISTS idx_trading_bots_strategy ON trading_bots(strategy_id)",
            "CREATE INDEX IF NOT EXISTS idx_trading_bots_account_chain ON trading_bots(account_address, chain)",
            "CREATE INDEX IF NOT EXISTS idx_trading_bots_active ON trading_bots(is_active)",
            
            # Position indexes
            "CREATE INDEX IF NOT EXISTS idx_positions_bot_active ON positions(bot_id, is_active)",
            "CREATE INDEX IF NOT EXISTS idx_positions_token ON positions(token_id)",
            "CREATE INDEX IF NOT EXISTS idx_positions_bot_token ON positions(bot_id, token_id)",
            
            # Position History indexes
            "CREATE INDEX IF NOT EXISTS idx_position_history_position_recorded ON position_history(position_id, recorded_at)",
            "CREATE INDEX IF NOT EXISTS idx_position_history_bot_recorded ON position_history(bot_id, recorded_at)",
            "CREATE INDEX IF NOT EXISTS idx_position_history_token_recorded ON position_history(token_id, recorded_at)",
            "CREATE INDEX IF NOT EXISTS idx_position_history_trigger ON position_history(trigger_event)",
            "CREATE INDEX IF NOT EXISTS idx_position_history_transaction ON position_history(transaction_id)",
            
            # Transaction indexes
            "CREATE INDEX IF NOT EXISTS idx_transactions_bot_created ON transactions(bot_id, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_type_date ON transactions(transaction_type, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_token ON transactions(token_id)",
            
            # LLM Decision indexes
            "CREATE INDEX IF NOT EXISTS idx_llm_decisions_bot_created ON llm_decisions(bot_id, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_llm_decisions_executed ON llm_decisions(was_executed)",
            
            # Revenue Snapshot indexes
            "CREATE INDEX IF NOT EXISTS idx_revenue_bot_created ON revenue_snapshots(bot_id, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_revenue_bot_snapshot_time ON revenue_snapshots(bot_id, snapshot_time)",
            "CREATE INDEX IF NOT EXISTS idx_revenue_type ON revenue_snapshots(snapshot_type)",
            "CREATE INDEX IF NOT EXISTS idx_revenue_snapshot_time ON revenue_snapshots(snapshot_time)",
            "CREATE INDEX IF NOT EXISTS idx_revenue_calculation_method ON revenue_snapshots(calculation_method)",
            
            # Trading Config indexes
            "CREATE INDEX IF NOT EXISTS idx_trading_configs_strategy ON trading_configs(strategy_name)",
            "CREATE INDEX IF NOT EXISTS idx_trading_configs_active ON trading_configs(is_active)"
        ]
        
        success_count = 0
        for i, index_sql in enumerate(indexes, 1):
            try:
                session.execute(text(index_sql))
                session.commit()
                success_count += 1
            except Exception as e:
                print(f"  ⚠️  Index creation warning: {e}")
                session.rollback()
        
        print(f"  ✓ Created {success_count}/{len(indexes)} indexes successfully")
        
        # Verify tables were created
        inspector = inspect(engine)
        new_tables = inspector.get_table_names()
        trading_bot_tables_created = [table for table in trading_bot_tables if table in new_tables]
        
        print(f"\n✅ TradingBot tables reset completed!")
        print(f"   Created tables: {trading_bot_tables_created}")
        print(f"   Total tables in database: {len(new_tables)}")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ TradingBot tables reset failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 TradingBot Tables Reset Script")
    print("=" * 50)
    
    success = reset_trading_bot_tables()
    
    if success:
        print("\n🎉 Reset completed successfully!")
        print("   You can now use the new TradingBot tables with the latest schema.")
    else:
        print("\n❌ Reset failed!")
        sys.exit(1) 