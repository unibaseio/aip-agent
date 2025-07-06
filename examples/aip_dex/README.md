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
sudo apt update
sudo apt install -y libpq-dev python3-dev
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
API_BEARER_TOKEN=your_secure_bearer_token_here
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

### Bearer Token Authentication

All API endpoints (except health check and root) require Bearer token authentication:

```bash
# Set your bearer token
export API_TOKEN="your_secure_bearer_token_here"
```

### Chat Query (with Authentication)

```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -d '{"message": "What is the outlook on DOGE?"}'
```

### Get All Tokens (with Authentication)

```bash
curl -X GET "http://localhost:8000/api/v1/tokens" \
  -H "Authorization: Bearer ${API_TOKEN}"
```

### Add Token (with Authentication)

```bash
curl -X POST "http://localhost:8000/api/v1/add_token?symbol=PEPE&chain=eth" \
  -H "Authorization: Bearer ${API_TOKEN}"
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

## Enhanced Web3 Token Signal Aggregator with Three-Tier Architecture

### Key Features
- 🔐 **Bearer Token Authentication** - Secure API access with configurable token
- 🏗️ **Three-Tier Architecture** - Token → Pools → Pool Metrics → Aggregated Token Metrics  
- 📊 **Multi-DEX Analysis** - Compare prices across different DEXs
- 🏊 **Pool-Level Metrics** - Granular data for each trading pool  
- 🎯 **Arbitrage Detection** - Identify price differences between DEXs
- 🤖 **AI-Powered Signals** - Enhanced trading signals with confidence scores
- 💬 **LLM Chat Interface** - Natural language token analysis
- 🔄 **Automated Data Collection** - Scheduled updates from multiple sources

### Data Sources
- **BirdEye** - Top tokens and market data
- **DEX Screener** - Real-time DEX pool information  
- **Moralis** - On-chain metrics and analytics

---

**Built with ❤️ for the Web3 community** 

# AIP DEX Trading Bot

一个基于AI的DEX交易机器人系统，支持灵活的所有者管理和策略配置。

## 系统概述

### 核心特性

- **灵活的所有者管理**：支持机器人所有者创建和管理
- **策略管理系统**：完整的交易策略配置和共享
- **灵活启动模式**：机器人可以不依赖owner和strategy启动
- **智能交易决策**：基于LLM的交易决策系统
- **多链支持**：支持BSC和Solana链
- **实时监控**：完整的交易历史和收益跟踪

### 系统架构

```
BotOwner (所有者)
    ├── TradingStrategy (策略1)
    │   ├── TradingBot (机器人1)
    │   └── TradingBot (机器人2)
    ├── TradingStrategy (策略2)
    │   └── TradingBot (机器人3)
    └── TradingStrategy (策略3)
        └── TradingBot (机器人4)
```

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd examples/aip_dex

# 安装依赖
pip install -r requirements.txt

# 初始化数据库
python -c "from models.database import init_database; init_database()"
```

### 2. 创建所有者

```python
from services.owner_service import OwnerService
from api.schemas import BotOwnerCreate

owner_service = OwnerService()

owner_data = BotOwnerCreate(
    owner_name="Your Name",
    email="your.email@example.com",
    wallet_address="your_wallet_address",
    subscription_tier="basic"
)

owner = await owner_service.create_bot_owner(db, owner_data)
```

### 3. 创建策略

```python
from api.schemas import TradingStrategyCreate

strategy_data = TradingStrategyCreate(
    strategy_name="My Strategy",
    strategy_type="user_defined",
    risk_level="medium",
    max_position_size=Decimal("15.0"),
    stop_loss_percentage=Decimal("8.0"),
    take_profit_percentage=Decimal("20.0"),
    buy_strategy_description="买入策略描述...",
    sell_strategy_description="卖出策略描述...",
    filter_strategy_description="筛选策略描述...",
    summary_strategy_description="策略总结..."
)

strategy = await owner_service.create_trading_strategy(db, owner.id, strategy_data)
```

### 4. 创建机器人

#### 方法A：立即配置

```python
from services.trading_service import TradingService

trading_service = TradingService()

bot_config = {
    "bot_name": "My Trading Bot",
    "account_address": "0x1234567890abcdef1234567890abcdef12345678",
    "chain": "bsc",
    "initial_balance_usd": 5000.0,
    "owner_id": owner.id,
    "strategy_id": strategy.id,
    "is_active": True
}

bot = await trading_service.create_trading_bot(db, bot_config)
```

#### 方法B：灵活启动

```python
# 步骤1：创建未配置机器人
bot_config = {
    "bot_name": "My Trading Bot",
    "account_address": "0x1234567890abcdef1234567890abcdef12345678",
    "chain": "bsc",
    "initial_balance_usd": 5000.0,
    "is_active": True
}

bot = await trading_service.create_trading_bot(db, bot_config)

# 步骤2：稍后配置
configured_bot = await trading_service.configure_bot(
    db, bot.id, owner.id, strategy.id
)
```

### 5. 运行机器人

```bash
# 使用默认配置
python run_bot.py --default

# 使用自定义配置文件
python run_bot.py --config my_config.json

# 交互式配置
python run_bot.py
```

## 核心概念

### BotOwner（机器人所有者）

每个交易机器人可以属于一个所有者。所有者具有以下特性：

- **基本信息**：姓名、邮箱、钱包地址、电话
- **权限控制**：订阅等级、最大机器人数量限制
- **统计信息**：创建的机器人数量、交易量等

### TradingStrategy（交易策略）

策略包含两个主要部分：

#### 1. 数值参数设置（具体数字性）

- **仓位管理**：最大仓位比例、止损百分比、止盈百分比
- **交易控制**：最小交易金额、每日最大交易次数、轮询间隔
- **风险控制**：最低收益率阈值、LLM置信度阈值
- **费用设置**：Gas费用、交易手续费率、滑点容忍度

#### 2. 策略描述性配置（文字描述性）

- **买入策略描述**：详细的买入逻辑和条件
- **卖出策略描述**：详细的卖出逻辑和条件
- **筛选策略描述**：代币筛选条件和标准
- **总结性策略描述**：策略的整体理念和适用场景

### TradingBot（交易机器人）

机器人具有以下特性：

- **灵活启动**：可以不依赖owner和strategy启动
- **状态管理**：支持未配置、已配置、停用等状态
- **策略关联**：直接关联策略实体，获取所有策略参数
- **交易执行**：基于策略参数执行买卖决策

## 机器人状态

### 状态定义

```python
# 未配置状态
UNCONFIGURED = {
    "is_active": True,
    "is_configured": False,
    "owner_id": None,
    "strategy_id": None,
    "can_trade": False
}

# 已配置状态
CONFIGURED = {
    "is_active": True,
    "is_configured": True,
    "owner_id": "uuid",
    "strategy_id": "uuid",
    "can_trade": True
}

# 停用状态
INACTIVE = {
    "is_active": False,
    "is_configured": True/False,
    "can_trade": False
}
```

### 状态转换

```
创建机器人 → 未配置状态 → 配置机器人 → 已配置状态 → 激活交易
     ↓              ↓              ↓              ↓
   基础设施      待激活状态      准备就绪      开始交易
```

## 策略管理

### 默认策略

系统提供三种默认策略：

- **Conservative Strategy**：保守策略，低风险，稳定收益
- **Moderate Strategy**：平衡策略，中等风险，平衡收益
- **Aggressive Strategy**：激进策略，高风险，高收益

### 自定义策略

用户可以创建完全自定义的策略：

```python
strategy_data = TradingStrategyCreate(
    strategy_name="My Custom Strategy",
    strategy_type="user_defined",
    risk_level="medium",
    max_position_size=Decimal("25.0"),
    stop_loss_percentage=Decimal("8.0"),
    take_profit_percentage=Decimal("30.0"),
    buy_strategy_description="详细的买入策略描述...",
    sell_strategy_description="详细的卖出策略描述...",
    filter_strategy_description="详细的筛选策略描述...",
    summary_strategy_description="策略总结描述..."
)
```

### 策略共享

策略可以设置为公开，供其他用户使用：

```python
# 创建公开策略
strategy_data = TradingStrategyCreate(
    strategy_name="Public Strategy",
    is_public=True,
    # ... 其他参数
)

# 获取公开策略
public_strategies = await owner_service.list_public_strategies(db)
```

## 使用示例

### 基础示例

```bash
# 运行基础示例
python examples/owner_strategy_example.py
```

### 灵活启动示例

```bash
# 运行灵活启动示例
python examples/flexible_bot_example.py
```

### 测试示例

```bash
# 运行测试
python test_owner_strategy.py
```

## 配置说明

### 机器人配置

```json
{
    "bot_name": "My Trading Bot",
    "account_address": "0x1234567890abcdef1234567890abcdef12345678",
    "chain": "bsc",
    "initial_balance_usd": 5000.0,
    "owner_id": "optional-owner-id",
    "strategy_id": "optional-strategy-id",
    "is_active": true
}
```

### 策略配置

```json
{
    "strategy_name": "My Strategy",
    "strategy_type": "user_defined",
    "risk_level": "medium",
    "max_position_size": 15.0,
    "stop_loss_percentage": 8.0,
    "take_profit_percentage": 20.0,
    "min_profit_threshold": 3.0,
    "max_daily_trades": 12,
    "llm_confidence_threshold": 0.7,
    "buy_strategy_description": "买入策略描述...",
    "sell_strategy_description": "卖出策略描述...",
    "filter_strategy_description": "筛选策略描述...",
    "summary_strategy_description": "策略总结..."
}
```

## API 参考

### 所有者管理

```python
# 创建所有者
owner = await owner_service.create_bot_owner(db, owner_data)

# 获取所有者
owner = await owner_service.get_bot_owner(db, owner_id)

# 更新所有者
updated_owner = await owner_service.update_bot_owner(db, owner_id, update_data)

# 列出所有者
owners = await owner_service.list_bot_owners(db)
```

### 策略管理

```python
# 创建策略
strategy = await owner_service.create_trading_strategy(db, owner_id, strategy_data)

# 获取策略
strategy = await owner_service.get_trading_strategy(db, strategy_id)

# 更新策略
updated_strategy = await owner_service.update_trading_strategy(db, strategy_id, update_data)

# 列出所有者的策略
strategies = await owner_service.list_owner_strategies(db, owner_id)

# 获取公开策略
public_strategies = await owner_service.list_public_strategies(db)
```

### 机器人管理

```python
# 创建机器人
bot = await trading_service.create_trading_bot(db, config)

# 配置机器人
configured_bot = await trading_service.configure_bot(db, bot_id, owner_id, strategy_id)

# 获取机器人状态
status = await trading_service.get_bot_status(db, bot_id)

# 获取机器人持仓
positions = await trading_service.get_bot_positions(db, bot_id)
```

## 部署指南

### 开发环境

```bash
# 1. 设置开发环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 2. 安装依赖
pip install -r requirements.txt

# 3. 初始化数据库
python -c "from models.database import init_database; init_database()"

# 4. 运行示例
python examples/flexible_bot_example.py
```

### 生产环境

```bash
# 1. 配置环境变量
export DATABASE_URL="your_database_url"
export API_KEY="your_api_key"

# 2. 运行机器人
python run_bot.py --config production_config.json
```

## 故障排除

### 常见问题

1. **数据库连接错误**
   - 检查数据库URL配置
   - 确保数据库服务正在运行

2. **机器人创建失败**
   - 检查账户地址格式
   - 确保账户地址唯一性

3. **策略配置错误**
   - 验证策略参数范围
   - 检查必需字段

4. **交易执行失败**
   - 检查账户余额
   - 验证网络连接

### 日志查看

```bash
# 查看机器人日志
tail -f trading_bot.log

# 查看错误日志
grep "ERROR" trading_bot.log
```

## 贡献指南

### 开发流程

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 创建 Pull Request

### 代码规范

- 使用 Python 3.8+
- 遵循 PEP 8 代码规范
- 添加适当的注释和文档
- 编写单元测试

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 联系方式

如有问题或建议，请通过以下方式联系：

- 邮箱：support@example.com
- GitHub Issues：[项目 Issues](https://github.com/your-repo/issues)
- 文档：[完整文档](https://docs.example.com) 