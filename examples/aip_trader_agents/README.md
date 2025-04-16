# AIP Automated Trader Agents

An automated trading agent system based on the AIP framework, supporting token trading on the BSC testnet/mainnet. The system provides an intuitive Gradio web interface for monitoring trading status, viewing wallet information, and executing trading operations.

## Features

- Real-time wallet balance and trading history monitoring
- Support for automated trading strategy execution
- Intuitive web interface
- Customizable trading strategies
- Comprehensive trading log recording
- Docker deployment support

## Requirements

- Install uv package manager:
   + Follow the official installation guide: https://docs.astral.sh/uv/getting-started/installation/
- Docker (optional)
- BSC testnet/mainnet wallet

## Configuration

### Environment Variables

Before running, you need to set the following environment variables:

```shell
# Set agent ID
export MEMBASE_ID="<your_agent_id>"

# Set wallet address
export MEMBASE_ACCOUNT="membase account"

# Set wallet private key
export MEMBASE_SECRET_KEY="membase secret key"

# Set target token address
# Default token address is "0x2e6b3f12408d5441e56c3C20848A57fd53a78931"
# This token is paired with WBNB on PancakeSwap V3 on BSC testnet
export MEMBASE_TARGET_TOKEN="your target token"

export OPENAI_API_KEY="your_openai_api_key"

# GRADIO Server configuration
export GRADIO_SERVER_NAME=127.0.0.1
export GRADIO_SERVER_PORT=7860
```

## Local Deployment

1. Navigate to project directory:
```shell
cd examples/aip_trader_agents
```

2. Run trading agent:
```shell
uv run trader_agent_gradio.py
```

3. Access Web Interface:
- Open browser and visit `http://localhost:7860`
- In the interface you can:
  - View wallet balance and trading history
  - Start/stop automated trading
  - Modify trading strategies
  - Execute manual trading operations

## Docker Deployment

### Configuration

1. Copy environment variables to `.env` file:
```shell
cp .env.example .env
```

2. Edit `.env` file with your configuration values

### Usage 

1. Build and start container:
```shell
docker compose up -d --build
```

2. Access Web Interface:
- Open browser and visit `http://localhost:7860`

## Important Notes

1. Ensure you have sufficient BNB on BSC testnet for trading and gas fees
2. Double-check token addresses and trading parameters before executing trades
3. It's recommended to test thoroughly on testnet first
4. Keep your private keys secure and never share them

## Troubleshooting

1. If experiencing connection issues, check:
   - Network connectivity
   - Environment variables configuration
   - BSC testnet/mainnet node accessibility

2. If trades fail, check:
   - Wallet balance
   - Trading parameters

## Support

For issues or questions, please submit an Issue or contact the support team.