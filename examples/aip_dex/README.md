# 📘 AIP DEX Signal Aggregator

A LLM-powered Web3 token signal aggregator providing real-time trading signals and chat interaction functionality.

## 🎯 Features

- **Enhanced Multi-source Data Aggregation**: Intelligent data fusion from CoinGecko, DEX Screener, Moralis, and BirdEye
- **Smart Token Resolution**: Automatically determines best data source based on token type and availability
- **Comprehensive Technical Analysis**: RSI, Moving Averages, Volume/Holder Analysis, Breakout Detection
- **LLM-Enhanced Signals**: GPT-4 powered analysis with comprehensive metrics and reasoning
- **Real-time Trading Data**: Live DEX prices, liquidity, and transaction activity
- **On-chain Analytics**: Holder counts, transfer activity, and wallet analysis
- **REST API**: Complete FastAPI interface with detailed token metrics
- **Interactive Chat**: Natural language queries with rich, formatted responses
- **Multi-DEX Analysis**: Compare prices and liquidity across different DEXs
- **Pool-Level Metrics**: Detailed metrics for each trading pool
- **Enhanced Signals**: AI-powered trading signals with confidence scores
- **LLM Chat Interface**: Natural language token analysis
- **Automated Data Collection**: Scheduled updates for token and pool data

## Unified Token Management

To prevent conflicts between the background scheduler and API calls, the system uses a unified token management approach:

### 1. Background Scheduler
The scheduler automatically discovers and adds trending tokens:
```python
# Automatically runs every hour
scheduler = TokenDataScheduler(chain="bsc", fetch_limit=50)
await scheduler.run_scheduler(interval_hours=1)
```

### 2. API Token Addition
Manual token addition via API:
```bash
# Add specific token via API
curl -X POST "http://localhost:8000/api/v1/tokens" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "DOGE",
    "contract_address": "0xba2ae424d960c26247dd6c32edc70b295c744c43",
    "chain": "bsc",
    "name": "Dogecoin"
  }'
```

### 3. Conflict Prevention
Both methods use the same unified `add_token_with_pools()` method which:
- ✅ Prevents duplicate token creation
- ✅ Avoids redundant pool updates (max once per hour)
- ✅ Automatically discovers pool information
- ✅ Maintains data consistency

### 4. Smart Update Logic
```python
# The unified method includes smart update logic:
if not should_update and existing_pools:
    # Check if any pool was updated recently (within last hour)
    one_hour_ago = datetime.now(UTC) - timedelta(hours=1)
    recent_updates = [p for p in existing_pools if p.updated_at and p.updated_at > one_hour_ago]
    should_update = len(recent_updates) == 0
```

This ensures that:
- If a token is added via API, the scheduler won't redundantly update its pools within the same hour
- If the scheduler processes a token, manual API calls won't trigger unnecessary updates
- Users can safely add tokens via API without worrying about conflicts with the background scheduler

## 🏗️ Architecture

```
aip_dex/
├── models/           # Data models (SQLAlchemy) with enhanced metrics
├── data_aggregator/  # Multi-source providers with intelligent routing
│   ├── coingecko.py     # CoinGecko SDK integration
│   ├── dex_screener.py  # DEX Screener API with correct endpoints
│   ├── moralis.py       # Moralis SDK for on-chain data
│   └── birdeye.py       # BirdEye API for high-volume token data
├── indicators/       # Enhanced technical indicator calculations
├── llm/             # OpenAI integration with comprehensive prompts
├── services/        # Smart data fusion and token resolution
├── api/             # FastAPI routes with detailed metrics
└── main.py          # Application entry point
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd examples/aip_dex
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `env.example` to `.env` and fill in the configuration:

```bash
cp env.example .env
```

```env
DATABASE_URL=postgresql://username:password@localhost/aip_dex
OPENAI_API_KEY=your_openai_api_key_here
COINGECKO_API_KEY=your_coingecko_api_key_here
MORALIS_API_KEY=your_moralis_api_key_here
BIRDEYE_API_KEY=your_birdeye_api_key_here
```

### 3. Setup Database

Ensure PostgreSQL is running and create the database:

```sql
CREATE DATABASE aip_dex;
```

### 4. Run System Tests

```bash
python test_system.py
```

### 5. Start API Service

```bash
python main.py
```

Or using uvicorn:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 📡 API Endpoints

### Basic Information

- `GET /` - API information
- `GET /api/v1/health` - Health check
- `GET /docs` - Swagger documentation

### Token Management

- `GET /api/v1/tokens` - Get all tokens
- `POST /api/v1/tokens` - Add new token

### Trading Signals

- `GET /api/v1/tokens/{token_id}/signal` - Get token trading signal

### Chat Interaction

- `POST /api/v1/chat` - Send chat message

## 💬 Usage Examples

### Chat Query

```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the outlook on DOGE?"}'
```

### Add Token

```bash
curl -X POST "http://localhost:8000/api/v1/tokens" \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "PEPE",
    "contract_address": "0x6982508145454ce325ddbe47a25d4ec3d2311933",
    "chain": "eth"
  }'
```

## 🔧 Signal Levels

| Signal Level | Meaning | Example Reason |
|-------------|---------|----------------|
| **Strong Buy** | Strong buy signal | "RSI 45, breakout confirmed, volume surged 3x" |
| **Buy** | Buy signal | "MA7 > MA30, RSI 55, healthy uptrend forming" |
| **Watch** | Watch signal | "RSI above 70, strong momentum but may continue" |
| **Hold** | Hold signal | "MA7 ≈ MA30, RSI neutral, no clear direction" |
| **Sell** | Sell signal | "Price down 12%, RSI > 75, likely cooling off" |
| **Strong Sell** | Strong sell signal | "MA30 > MA7, RSI < 30, strong downward pressure" |

## 🧪 Testing

Run the test script to verify all components:

```bash
python test_system.py
```

Tests include:
- Data provider connectivity
- Technical indicator calculations
- OpenAI integration

## 📊 Enhanced Data Sources & Metrics

### 🔗 Data Source Specialization
- **CoinGecko**: Major tokens, historical data, market rankings, supply metrics
- **DEX Screener**: Real-time DEX prices, liquidity pools, trading activity, new tokens
- **Moralis**: On-chain holder analytics, transfer activity, wallet interactions
- **BirdEye**: High-volume token discovery, BSC/Ethereum trending tokens, security analysis

### 📈 Technical Indicators
- **RSI (14-day)**: Relative Strength Index with momentum analysis
- **MA7/MA30**: 7-day and 30-day Moving Averages with trend detection
- **Volume Analysis**: 24h/6h/1h volume tracking and delta calculations
- **Holder Metrics**: Holder count changes and activity scoring
- **Breakout Detection**: Price/volume breakout confirmation
- **Liquidity Analysis**: DEX liquidity depth and stability

### 🧠 Smart Token Resolution
- **Strategy 1**: Contract address provided → DEX Screener + Moralis (best for new/DeFi tokens)
- **Strategy 2**: Major tokens → CoinGecko primary (comprehensive market data)
- **Strategy 3**: Fallback → Multi-source search and data fusion

## 🔑 API Key Setup

- **OpenAI**: [platform.openai.com](https://platform.openai.com)
- **CoinGecko**: [coingecko.com/api](https://coingecko.com/api)
- **Moralis**: [moralis.io](https://moralis.io)
- **BirdEye**: [birdeye.so](https://birdeye.so) - Get API key from BirdEye dashboard

## ⚠️ Disclaimer

This project is for educational and research purposes only. It does not constitute investment advice. Cryptocurrency trading involves risks, please invest cautiously.

## 📝 Development Notes

- Code and comments use English
- Follow PEP 8 coding standards
- Use type hints
- Async programming best practices

## 🔮 Enhancement Features

Based on the design document, optional enhancements include:

- Telegram/Discord bots
- Sentiment analysis (Twitter API)
- Wallet analytics (Moralis + address tracking)
- Portfolio simulation/backtesting

---

**Built with ❤️ for the Web3 community** 