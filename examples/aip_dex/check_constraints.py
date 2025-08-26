#!/usr/bin/env python3
"""
Check database constraints for trading_bots table
"""

import os
from sqlalchemy import create_engine, text

def check_trading_bots_constraints():
    """Check constraints on trading_bots table"""
    
    # Get database URL from environment or use default
    database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/aip_dex')
    
    try:
        # Create engine
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Check constraints on trading_bots table
            result = conn.execute(text("""
                SELECT conname, contype, pg_get_constraintdef(oid) as definition
                FROM pg_constraint 
                WHERE conrelid = (SELECT oid FROM pg_class WHERE relname = 'trading_bots')
            """))
            
            print("Trading bots table constraints:")
            print("=" * 50)
            
            constraints = list(result)
            if not constraints:
                print("No constraints found on trading_bots table")
            else:
                for row in constraints:
                    constraint_name = row[0]
                    constraint_type = row[1]
                    definition = row[2]
                    
                    type_map = {
                        'p': 'PRIMARY KEY',
                        'f': 'FOREIGN KEY', 
                        'u': 'UNIQUE',
                        'c': 'CHECK',
                        'x': 'EXCLUDE'
                    }
                    
                    type_desc = type_map.get(constraint_type, constraint_type)
                    print(f"- {constraint_name} ({type_desc})")
                    print(f"  Definition: {definition}")
                    print()
            
            # Also check indexes
            result = conn.execute(text("""
                SELECT indexname, indexdef
                FROM pg_indexes 
                WHERE tablename = 'trading_bots'
            """))
            
            print("\nTrading bots table indexes:")
            print("=" * 50)
            
            indexes = list(result)
            if not indexes:
                print("No indexes found on trading_bots table")
            else:
                for row in indexes:
                    index_name = row[0]
                    index_def = row[1]
                    print(f"- {index_name}")
                    print(f"  Definition: {index_def}")
                    print()
                    
    except Exception as e:
        print(f"Error checking constraints: {e}")
        return False
    
    return True

if __name__ == "__main__":
    check_trading_bots_constraints()