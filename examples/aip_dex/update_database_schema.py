#!/usr/bin/env python3
"""
Database schema update script to fix numeric overflow issue
Updates price change fields from DECIMAL(10,4) to DECIMAL(15,4)
"""

import os
import sys
from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker

def update_database_schema():
    """Update database schema to handle extreme price changes"""
    
    # Get database URL from environment or use default
    database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/aip_dex')
    
    try:
        # Create engine and session
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        print("🔄 Starting database schema update...")
        
        # List of ALTER TABLE statements to update precision
        update_statements = [
            # pool_metrics table
            "ALTER TABLE pool_metrics ALTER COLUMN price_change_1h TYPE DECIMAL(15,4)",
            "ALTER TABLE pool_metrics ALTER COLUMN price_change_6h TYPE DECIMAL(15,4)",
            "ALTER TABLE pool_metrics ALTER COLUMN price_change_24h TYPE DECIMAL(15,4)",
            
            # pool_metrics_history table
            "ALTER TABLE pool_metrics_history ALTER COLUMN price_change_1h TYPE DECIMAL(15,4)",
            "ALTER TABLE pool_metrics_history ALTER COLUMN price_change_6h TYPE DECIMAL(15,4)",
            "ALTER TABLE pool_metrics_history ALTER COLUMN price_change_24h TYPE DECIMAL(15,4)",
            
            # token_metrics table
            "ALTER TABLE token_metrics ALTER COLUMN price_change_5m TYPE DECIMAL(15,4)",
            "ALTER TABLE token_metrics ALTER COLUMN price_change_1h TYPE DECIMAL(15,4)",
            "ALTER TABLE token_metrics ALTER COLUMN price_change_6h TYPE DECIMAL(15,4)",
            "ALTER TABLE token_metrics ALTER COLUMN price_change_24h TYPE DECIMAL(15,4)",
            "ALTER TABLE token_metrics ALTER COLUMN holder_change_5m_percent TYPE DECIMAL(15,4)",
            "ALTER TABLE token_metrics ALTER COLUMN holder_change_1h_percent TYPE DECIMAL(15,4)",
            "ALTER TABLE token_metrics ALTER COLUMN holder_change_6h_percent TYPE DECIMAL(15,4)",
            "ALTER TABLE token_metrics ALTER COLUMN holder_change_24h_percent TYPE DECIMAL(15,4)",
            "ALTER TABLE token_metrics ALTER COLUMN holder_change_3d_percent TYPE DECIMAL(15,4)",
            "ALTER TABLE token_metrics ALTER COLUMN holder_change_7d_percent TYPE DECIMAL(15,4)",
            "ALTER TABLE token_metrics ALTER COLUMN holder_change_30d_percent TYPE DECIMAL(15,4)",
            "ALTER TABLE token_metrics ALTER COLUMN volume_change_24h TYPE DECIMAL(15,4)",
            
            # token_metrics_history table
            "ALTER TABLE token_metrics_history ALTER COLUMN price_change_24h TYPE DECIMAL(15,4)",
            "ALTER TABLE token_metrics_history ALTER COLUMN price_change_5m TYPE DECIMAL(15,4)",
            "ALTER TABLE token_metrics_history ALTER COLUMN price_change_1h TYPE DECIMAL(15,4)",
            "ALTER TABLE token_metrics_history ALTER COLUMN price_change_6h TYPE DECIMAL(15,4)",
            "ALTER TABLE token_metrics_history ALTER COLUMN holder_change_24h_percent TYPE DECIMAL(15,4)",
        ]
        
        success_count = 0
        total_statements = len(update_statements)
        
        # Execute each update statement
        for i, statement in enumerate(update_statements, 1):
            try:
                print(f"  [{i}/{total_statements}] Executing: {statement}")
                session.execute(text(statement))
                session.commit()
                success_count += 1
                print(f"  ✓ Success")
            except Exception as e:
                print(f"  ⚠️  Warning: {e}")
                session.rollback()
                continue
        
        session.close()
        
        print(f"\n🎉 Database schema update completed!")
        print(f"   ✓ {success_count}/{total_statements} statements executed successfully")
        
        if success_count < total_statements:
            print(f"   ⚠️  {total_statements - success_count} statements failed (may be already applied)")
        
        return True
        
    except Exception as e:
        print(f"❌ Database schema update failed: {e}")
        return False

def check_current_schema():
    """Check current schema for debugging"""
    database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/aip_dex')
    
    try:
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Check current column definitions
        check_query = """
        SELECT 
            table_name, 
            column_name, 
            data_type, 
            numeric_precision, 
            numeric_scale
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND column_name LIKE '%price_change%'
        ORDER BY table_name, column_name;
        """
        
        result = session.execute(text(check_query))
        rows = result.fetchall()
        
        print("\n📊 Current price change column definitions:")
        print("-" * 80)
        print(f"{'Table':<25} {'Column':<25} {'Type':<15} {'Precision':<10} {'Scale':<5}")
        print("-" * 80)
        
        for row in rows:
            table_name = row[0]
            column_name = row[1]
            data_type = row[2]
            precision = row[3] or 'N/A'
            scale = row[4] or 'N/A'
            print(f"{table_name:<25} {column_name:<25} {data_type:<15} {precision:<10} {scale:<5}")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Schema check failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        check_current_schema()
    else:
        print("🚀 AIP DEX Database Schema Update")
        print("=" * 50)
        
        # Show current schema first
        check_current_schema()
        
        # Ask for confirmation
        response = input("\n❓ Do you want to proceed with the schema update? (y/N): ")
        if response.lower() in ['y', 'yes']:
            if update_database_schema():
                print("\n✅ Schema update completed successfully!")
                # Show updated schema
                check_current_schema()
            else:
                print("\n❌ Schema update failed!")
                sys.exit(1)
        else:
            print("❌ Schema update cancelled by user") 