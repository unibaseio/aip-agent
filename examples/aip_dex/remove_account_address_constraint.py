#!/usr/bin/env python3
"""
Remove the unique constraint on account_address from trading_bots table
"""

import os
from sqlalchemy import create_engine, text

def remove_account_address_constraint():
    """Remove unique constraint on account_address"""
    
    # Get database URL from environment or use default
    database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/aip_dex')
    
    try:
        # Create engine
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Start a transaction
            trans = conn.begin()
            
            try:
                print("🔄 Removing unique constraint on account_address...")
                
                # Drop the unique constraint
                conn.execute(text("""
                    ALTER TABLE trading_bots 
                    DROP CONSTRAINT IF EXISTS trading_bots_account_address_key
                """))
                
                print("✅ Successfully removed unique constraint: trading_bots_account_address_key")
                
                # Also drop the unique index if it still exists
                conn.execute(text("""
                    DROP INDEX IF EXISTS trading_bots_account_address_key
                """))
                
                print("✅ Successfully removed unique index: trading_bots_account_address_key")
                
                # Commit the transaction
                trans.commit()
                
                print("\n🎉 Account address unique constraint removed successfully!")
                print("   Multiple bots can now use the same account address.")
                
                # Verify the constraint is gone
                result = conn.execute(text("""
                    SELECT conname, contype 
                    FROM pg_constraint 
                    WHERE conrelid = (SELECT oid FROM pg_class WHERE relname = 'trading_bots')
                    AND conname = 'trading_bots_account_address_key'
                """))
                
                remaining_constraints = list(result)
                if not remaining_constraints:
                    print("✅ Verified: Unique constraint has been completely removed")
                else:
                    print("⚠️  Warning: Some constraints may still exist")
                    for row in remaining_constraints:
                        print(f"   - {row[0]} ({row[1]})")
                
            except Exception as e:
                trans.rollback()
                print(f"❌ Error during constraint removal: {e}")
                return False
                
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Remove Account Address Unique Constraint")
    print("=" * 50)
    
    success = remove_account_address_constraint()
    
    if success:
        print("\n✅ Operation completed successfully!")
        print("   You can now create multiple bots with the same account address.")
    else:
        print("\n❌ Operation failed!")
        exit(1)