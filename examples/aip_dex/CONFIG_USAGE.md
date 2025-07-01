# AIP DEX Trading Bot Configuration

This document explains how to use configuration files with the AIP DEX Trading Bot.

## Configuration File Format

The bot supports JSON configuration files. Here's an example configuration:

```json
{
    "bot_name": "AIP DEX Trading Bot",
    "account_address": "0x1234567890abcdef1234567890abcdef12345678",
    "chain": "bsc",
    "initial_balance_usd": 1000.0,
    "strategy_type": "aggressive",
    "polling_interval_hours": 0.1,
    "min_trade_amount_usd": 10.0,
    "is_active": true
}
```

## Required Configuration Fields

- `bot_name`: Name of the trading bot
- `account_address`: Ethereum wallet address for trading
- `chain`: Blockchain network (e.g., "bsc", "ethereum")
- `initial_balance_usd`: Initial balance in USD
- `strategy_type`: Trading strategy type
- `polling_interval_hours`: How often to check for opportunities (in hours)
- `min_trade_amount_usd`: Minimum trade amount in USD
- `is_active`: Whether the bot should be active

## Usage Methods

### 1. Command Line with Config File

```bash
python run_bot.py --config bot_config.json
```

or

```bash
python run_bot.py -c config_example.json
```

### 2. Command Line with Default Config

```bash
python run_bot.py --default
```

### 3. Interactive Mode

```bash
python run_bot.py
```

This will prompt you to choose between loading from a config file or using default configuration.

## Example Configuration Files

- `config_example.json`: Basic configuration example
- `config_minutes_example.json`: High-frequency trading configuration

## Error Handling

The bot will validate configuration files and provide helpful error messages for:
- Missing configuration files
- Invalid JSON format
- Missing required fields

## Tips

1. Always backup your configuration files
2. Test configurations with small amounts first
3. Use descriptive bot names for easy identification
4. Adjust polling intervals based on your trading strategy 