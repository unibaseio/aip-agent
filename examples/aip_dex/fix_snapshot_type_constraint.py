#!/usr/bin/env python3
"""
Fix snapshot_type constraint to include 'initial' value
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/aip_dex")
engine = create_engine(DATABASE_URL)

def fix_snapshot_type_constraint():
    """Fix snapshot_type constraint to include 'initial' value"""
    try:
        with engine.begin() as conn:
            # Drop the old constraint
            conn.execute(text("""
                ALTER TABLE revenue_snapshots 
                DROP CONSTRAINT IF EXISTS check_snapshot_type
            """))
            
            # Add the new constraint with 'initial' included
            conn.execute(text("""
                ALTER TABLE revenue_snapshots 
                ADD CONSTRAINT check_snapshot_type 
                CHECK (snapshot_type IN ('hourly', 'daily', 'manual', 'triggered', 'initial'))
            """))
            
            print("✓ Fixed snapshot_type constraint to include 'initial'")
            return True
            
    except Exception as e:
        print(f"❌ Error fixing snapshot_type constraint: {e}")
        return False

if __name__ == "__main__":
    print("Fixing snapshot_type constraint...")
    
    if fix_snapshot_type_constraint():
        print("\n✓ Database constraint fix completed successfully")
    else:
        print("\n❌ Database constraint fix failed") 