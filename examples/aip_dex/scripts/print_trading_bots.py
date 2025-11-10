#!/usr/bin/env python3
"""
Simple script to load the examples/aip_dex models/database.py module,
query the `TradingBot` table and print each bot as JSON-friendly output.

Notes:
- This script will try to import the database module by path so it does not
  require package __init__ files.
- If the database is unreachable, the script will show a helpful error and exit.
"""
import os
import sys
import json
import decimal
import importlib.util
from pathlib import Path

# Resolve path to the database module relative to this script
CURRENT = Path(__file__).resolve()
DB_MODULE_PATH = (CURRENT.parent.parent / "models" / "database.py").resolve()

if not DB_MODULE_PATH.exists():
    print(f"Error: database module not found at: {DB_MODULE_PATH}")
    sys.exit(1)

spec = importlib.util.spec_from_file_location("aip_dex_database", str(DB_MODULE_PATH))
db_mod = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(db_mod)
except Exception as e:
    print(f"Failed to import database module: {e}")
    sys.exit(1)

# Grab needed symbols
try:
    TradingBot = getattr(db_mod, "TradingBot")
    SessionLocal = getattr(db_mod, "SessionLocal")
except AttributeError as e:
    print(f"Required symbol missing in database module: {e}")
    sys.exit(1)

# Fields to display for each TradingBot (adjust as needed)
DISPLAY_FIELDS = [
    "id",
    "bot_name",
    "owner_id",
    "strategy_id",
    "account_address",
    "chain",
    "initial_balance_usd",
    "current_balance_usd",
    "total_assets_usd",
    "is_active",
    "is_configured",
    "total_trades",
    "profitable_trades",
    "total_profit_usd",
    "max_drawdown_percentage",
    "created_at",
    "updated_at",
    "last_activity_at",
]


def serialize_value(v):
    """Convert common DB/Python types to JSON-friendly values."""
    if v is None:
        return None
    # decimals
    if isinstance(v, decimal.Decimal):
        # keep numeric precision as string to avoid float rounding
        return str(v)
    # UUIDs
    try:
        import uuid

        if isinstance(v, uuid.UUID):
            return str(v)
    except Exception:
        pass
    # datetimes
    try:
        from datetime import datetime

        if isinstance(v, datetime):
            return v.isoformat()
    except Exception:
        pass
    # fallback
    return v


def main():
    # Create a session and query TradingBot
    session = None
    try:
        session = SessionLocal()
    except Exception as e:
        print(f"Failed to create DB session: {e}")
        sys.exit(1)

    try:
        bots = session.query(TradingBot).all()
    except Exception as e:
        print(f"Failed to query TradingBot: {e}")
        if session:
            session.close()
        sys.exit(1)

    if not bots:
        print("No trading_bots found.")
    else:
        out = []
        for b in bots:
            record = {}
            for f in DISPLAY_FIELDS:
                try:
                    val = getattr(b, f)
                except Exception:
                    val = None
                record[f] = serialize_value(val)
            out.append(record)

        # Pretty-print JSON
        print(json.dumps(out, indent=2, ensure_ascii=False))

    session.close()


if __name__ == "__main__":
    main()
