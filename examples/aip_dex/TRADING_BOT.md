# AIP DEX Trading Bot

## 概述

AIP DEX交易机器人是一个自动化虚拟交易系统，支持在BSC和Solana链上进行USD与memecoin之间的交易。系统提供账户管理、策略执行、交易记录和收益分析功能。

### 技术架构
- **后端**：FastAPI + SQLAlchemy + PostgreSQL
- **前端**：HTML/CSS/JavaScript + Chart.js，支持定时刷新
- **AI服务**：OpenAI GPT-4.1-mini
- **LLM分析器**：智能两阶段筛选的交易决策分析器
- **数据源**：PostgreSQL数据库存储的代币信息（价格、交易量、技术指标等）
- **交易机器人**：`uv run trading_bot.py`
- **部署**：uv启动，`uv run main.py`

## 核心特性

### 智能交易决策
- **两阶段筛选机制**：LLM智能筛选 + 详细分析决策
- **策略适配**：根据机器人策略类型调整筛选标准
- **容错机制**：LLM服务异常时自动使用备用方案
- **实时分析**：基于最新市场数据进行决策

### USD计价系统
- 所有成本和价格均以USD计价
- Trading cost composition:
  - **Gas Fee**: 0.00003 native token
    - BSC Chain: gas_cost_usd = 0.00003 × current_wbnb_price_usd
    - Solana Chain: gas_cost_usd = 0.001 × current_sol_price_usd
  - **Trading Fee**: 0.1% of transaction amount
  - **Total Trading Cost**: gas_cost_usd + transaction_amount × 0.1%

### 交易类型
- **虚拟交易**：模拟链上交易，记录前后状态
- **购买**：USD → memecoin，amount是USD数目
- **卖出**：memecoin → USD，amount是memecoin数目
- **状态**：pending、executed、failed、cancelled

### 持仓管理

#### 持仓状态包含
- **可用USD余额**：用于新的买入操作
- **持有代币列表**：每个代币的详细信息
  - 代币符号和名称
  - 持有数量（内部精度10^18）
  - 平均持仓成本（USD）
  - 当前市值（USD）
  - 未实现盈亏（USD和百分比）

#### 持仓成本计算
- **买入时更新平均成本**：
  ```
  New Average Cost = (Current Quantity × Current Average Cost + Purchase Quantity × Purchase Price + Trading Cost) / (Current Quantity + Purchase Quantity)
  ```
- **卖出时更新平均成本**：
  ```
  New Average Cost = ((Current Quantity - Sell Quantity) × Current Average Cost + Trading Cost) / (Current Quantity - Sell Quantity)
  注意：当剩余数量为0时，平均成本重置为0
  ```
- **预期收益计算**：
  ```
  Expected Return Rate = (Sell Quantity × (Current Price - Current Average Cost) - Trading Cost) / (Sell Quantity × Current Average Cost)
  ```

**Cost Impact Mechanism**:
- **Buy**: Transaction cost increases the average holding cost
- **Sell**: Transaction cost also increases the average cost of remaining holdings
- **Edge Case**: When remaining quantity becomes 0, average cost resets to 0
- **Cost Accumulation**: Each transaction's cost affects subsequent average cost calculations

#### Expected Return Analysis

**Relationship between Return Rate and Sell Quantity**:
Due to transaction costs, different sell quantities produce different return rates. General patterns:
- **Smaller sell quantity, lower return rate**: Fixed transaction costs are spread over fewer tokens sold
- **Larger sell quantity, higher return rate**: Transaction cost impact is diluted

**Return Rate Calculation Example**:
Assume holding 10000 tokens, average cost $0.01, current price $0.015, transaction cost $2

| Sell Ratio | Sell Quantity | Sell Revenue | Transaction Cost | Net Profit | Input Cost | Return Rate |
|------------|---------------|-------------|------------------|------------|------------|-------------|
| 10% | 1000 | $15 | $2 | $13 | $10 | 30% |
| 20% | 2000 | $30 | $2 | $28 | $20 | 40% |
| 50% | 5000 | $75 | $2 | $73 | $50 | 46% |
| 100% | 10000 | $150 | $2 | $148 | $100 | 48% |

**LLM Decision Considerations**:
1. **Return Rate Threshold**: Small percentage sells may not meet strategy's minimum return requirements
2. **Market Judgment**: If expecting continued price increase, may choose smaller percentage sell
3. **Risk Control**: When reaching take-profit targets, may choose large percentage sell to lock in profits
4. **Transaction Cost Efficiency**: Balance return rate with trading frequency

**Actual Decision Logic**:
- When return rate is low, LLM may tend to sell larger percentages to improve efficiency
- When transaction costs are relatively high compared to profits, may choose to wait for better timing
- Combine market trend judgment to find balance between return rate and risk

#### Cost Calculation Examples
**Buy Example**:
- Current: 1000 tokens, average cost $0.01
- Purchase: 500 tokens, price $0.012, transaction cost $1
- New Average Cost = (1000×0.01 + 500×0.012 + 1) / 1500 = $0.0107

**Sell Example**:
- Current: 1500 tokens, average cost $0.0107
- Sell: 300 tokens, transaction cost $0.5
- New Average Cost = (1200×0.0107 + 0.5) / 1200 = $0.01112

**Full Sell Example**:
- Current: 100 tokens, average cost $0.015
- Sell: 100 tokens (all), transaction cost $0.2
- Remaining quantity is 0, average cost resets to 0

### 交易机器人

#### 核心配置
- **身份配置**：机器人名称、账户地址、交易链
- **资金配置**：初始余额、最小交易金额
- **策略配置**：策略类型、风险参数、交易限制
- **运行配置**：轮询频率、置信度阈值、开关控制

#### 启动配置参数

**轮询间隔设置示例**：
```bash
# 15分钟轮询间隔
python trading_bot.py --name "High Frequency Bot" --balance 1000 --interval 0.25

# 30分钟轮询间隔  
python trading_bot.py --name "Medium Frequency Bot" --balance 1000 --interval 0.5

# 1分钟轮询间隔（高频交易）
python trading_bot.py --name "Ultra High Frequency Bot" --balance 1000 --interval 0.0167

# 使用配置文件（config_minutes_example.json）
python trading_bot.py --config config_minutes_example.json
```

**基础配置**：
- `bot_name`: 机器人名称，例如"Conservative BSC Bot"
- `account_address`: 钱包地址，例如"0x12ea567890abcdef1234567890abcdef12345678"
- `chain`: 交易链，"bsc" 或 "solana"
- `initial_balance_usd`: 初始USD余额，≥1000.0

**交易费率**：
- `gas_fee_native`: Gas费用，默认0.00003
- `trading_fee_percentage`: 交易手续费率，默认0.1%
- `slippage_tolerance`: 滑点容忍度，默认1.0%

**策略参数（根据strategy_type自动设置，可覆盖）**：
- `strategy_type`: 策略类型，见策略表格
- `max_position_size`: 单币最大仓位比例
- `stop_loss_percentage`: 止损百分比
- `take_profit_percentage`: 止盈百分比
- `max_daily_trades`: 每日最大交易次数

**运行控制**：
- `min_trade_amount_usd`: 最小交易金额，默认10.0
- `polling_interval_hours`: 轮询间隔小时，支持小数，默认1.0
  - 支持分钟级别设置：0.25 = 15分钟，0.5 = 30分钟，0.75 = 45分钟
  - 支持秒级别设置：0.0167 = 1分钟，0.0083 = 30秒
  - 示例：`--interval 0.25` 设置15分钟轮询间隔
- `llm_confidence_threshold`: LLM决策置信度阈值，默认0.7
- `enable_stop_loss`: 启用止损，默认true
- `enable_take_profit`: 启用止盈，默认true

#### 决策逻辑详解

交易机器人采用两阶段决策模式，先卖出后买入，确保资金的合理配置。买入决策采用智能两阶段筛选机制：

**阶段一：卖出决策**
1. 获取账户当前持仓列表
2. 从数据库获取每个持仓代币的最新信息：
   - 当前价格、24h涨跌幅
   - 交易量、市值变化
   - 技术指标、市场情绪
3. LLM分析每个持仓代币：
   - 对比持仓成本与当前价格
   - 评估市场趋势和风险
   - **重点分析**：计算不同卖出比例(10%,20%,30%...100%)的预期收益率
   - 考虑交易成本对小比例卖出收益率的负面影响
   - 评估收益率是否达到策略要求的阈值
   - 考虑策略参数（止损、止盈）
   - 注意：卖出后剩余持仓的平均成本会因交易成本而上升
4. 决定卖出操作：
   - 选择：不卖出、10%、20%、30%、...、100%
   - 可以对多个代币同时做卖出决策
   - 也可以选择都不卖出

**阶段二：买入决策（两阶段筛选）**
1. **第一阶段：LLM智能筛选**
   - 从数据库获取所有可用代币的基本信息：
     - 代币符号、当前价格
     - 24h涨跌幅、交易量
     - 市值、流动性、交易对数量
   - LLM基于简单信息筛选出最有潜力的5个币种
   - 考虑策略类型偏好（保守型/激进型/平衡型）
   - 返回JSON格式的5个代币符号

**循环总结报告**
每个交易循环结束后，系统自动生成详细的总结报告：

**💰 财务状况**
- 初始余额、当前余额、总资产
- 总收益、最大回撤、收益率百分比

**📈 交易统计**
- 总交易次数、盈利交易次数、胜率
- 今日交易次数

**📋 持仓摘要**
- 每个持仓的详细信息（数量、成本、当前价值、未实现盈亏）
- 持仓占总资产的比例
- 投资组合汇总（总持仓价值、总成本、总未实现盈亏）
- 最大持仓分析

**🔄 最近交易**
- 最近24小时内的交易记录
- 交易类型、金额、盈亏、状态、时间

**📊 最新收益快照**
- 总收益和收益率
- 快照时间

2. **第二阶段：详细分析决策**
   - 获取这5个币种的完整详细信息：
     - 历史价格走势、技术指标（RSI、MA、波动率等）
     - 基本面分析（交易量、流动性、持币者分析）
     - 市场情绪（买卖压力、交易者活动）
     - 风险评估、市场热度
   - LLM最终决策：
     - 选择购买哪个币种（0-1个）
     - 确定购买金额（10 USD ≤ 金额 ≤ 可用USD）
     - 考虑交易成本对投资回报的影响
     - 也可以选择都不买入

**决策约束条件**：
- 最小买入金额：10 USD
- 最大买入金额：不超过可用USD余额
- 卖出比例：10%的倍数（10%, 20%, ..., 100%）
- **收益率约束**：考虑交易成本后的净收益率必须为正
- **效率约束**：小比例卖出需要权衡收益率与交易频次
- 单日交易次数限制
- 必须符合策略风险参数

**LLM分析器特性**：
- **智能筛选**：从大量代币中快速识别最有潜力的候选者
- **策略适配**：根据机器人策略类型调整筛选标准
- **容错机制**：LLM服务异常时自动使用备用筛选方案
- **详细分析**：对筛选出的代币进行全面的技术和基本面分析

#### 配置文件示例

```json
{
  "bot_name": "Conservative BSC Bot",
  "accountaddress": "0x12ea567890abcdef1234567890abcdef12345678",
  "chain": "bsc",
  "initial_balance_usd": 10000.0,
  "strategy_type": "conservative",
  "gas_fee_native": 0.00003,
  "trading_fee_percentage": 0.1,
  "slippage_tolerance": 1.0,
  "min_trade_amount_usd": 10.0,
  "polling_interval_hours": 1,
  "llm_confidence_threshold": 0.8,
  "enable_stop_loss": true,
  "enable_take_profit": true,
  "max_position_size": 10,
  "stop_loss_percentage": 5,
  "take_profit_percentage": 15,
  "max_daily_trades": 10
}
```

## LLM分析器

### 交易决策分析器 (TradingDecisionAnalyzer)

交易决策分析器采用智能两阶段筛选机制，提供专业的买卖决策建议：

#### 买入分析（两阶段筛选）

**第一阶段：智能筛选**
- 从所有可用代币中筛选出最有潜力的5个候选者
- 基于简单市场指标：价格、市值、交易量、流动性、价格变化
- 考虑策略类型偏好，适配不同风险承受能力
- 输出JSON格式的5个代币符号

**第二阶段：详细分析**
- 对筛选出的5个代币进行深度分析
- 包含完整技术指标：RSI、移动平均线、波动率、趋势方向
- 基本面分析：交易量、流动性、持币者结构、市场情绪
- 风险评估：集中度风险、波动性、技术信号强度
- 最终决策：是否买入、买哪个、买多少

#### 卖出分析
- 分析当前持仓的技术面和基本面状况
- 计算不同卖出比例的预期收益率
- 考虑交易成本对收益率的影响
- 提供详细的卖出建议和风险评估

#### 系统提示优化
- 针对不同阶段使用专门的系统提示
- 筛选阶段：快速识别机会，注重效率
- 分析阶段：深度分析，注重准确性
- 中文输出，数据部分保持英文格式

### 代币分析器 (TokenDecisionAnalyzer)
- 提供单个代币的全面分析报告
- 支持用户查询和聊天交互
- 包含技术指标、基本面、风险评估等

## 交易策略

| 策略类型 | 风险等级 | 单币最大仓位 | 止损 | 止盈 | 每日交易 | 置信度阈值 | 最低收益率阈值 |
|---------|---------|-------------|------|------|---------|-----------|-------------|
| Conservative | 低 | 10% | 5% | 15% | 10次 | 0.8 | 5% |
| Moderate | 中 | 20% | 10% | 25% | 15次 | 0.7 | 3% |
| Aggressive | 高 | 40% | 15% | 50% | 25次 | 0.6 | 1% |
| Momentum | 中高 | 30% | 12% | 35% | 20次 | 0.65 | 2% |
| Mean Reversion | 中 | 25% | 8% | 20% | 12次 | 0.75 | 4% |

## 用户界面

### 主页面
- 机器人列表：名称、账户、状态、收益
- 快速统计：总资产、今日收益
- 定时刷新：30秒/1分钟/5分钟

### 详情页
- 收益曲线图：基于历史交易数据
- 持仓状态表格：当前持仓和盈亏情况
- 交易历史时间轴：LLM决策记录和执行结果
- 决策分析：显示LLM的卖出/买入分析过程

## API接口

所有接口均为GET请求，只用于数据展示。所有代币价格、交易量、技术指标等数据均来自PostgreSQL数据库。

### 机器人管理
```http
GET /api/bots                    # 获取所有机器人
GET /api/bots/{bot_id}          # 获取机器人详情
GET /api/bots/{bot_id}/transactions  # 获取交易历史
GET /api/bots/{bot_id}/revenue       # 获取收益数据
```

### 市场数据（来源：数据库）


### 系统状态
```http
GET /api/system/overview        # 系统概览
GET /health                     # 健康检查
```

## 部署运行

### 安装配置
```bash
# 安装uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装依赖
uv sync

# 配置环境
cp .env.example .env
# 编辑.env文件，配置OPENAI_API_KEY和DATABASE_URL

# 初始化数据库
uv run python -m database.migrations.init_db
```

### 启动应用

#### 1. 启动展示页面 (main.py)
```bash
# 开发环境
uv run main.py

# 生产环境
uv run --host 0.0.0.0 --port 8000 main.py
```

#### 2. 启动交易机器人 (trading_bot.py)
```bash
# 使用配置文件启动
uv run trading_bot.py --config bots/conservative_bsc.json

# 使用命令行参数启动
uv run trading_bot.py \
  --name "My Trading Bot" \
  --chain bsc \
  --balance 5000 \
  --strategy moderate

# 启动多个机器人
uv run trading_bot.py --config bots/conservative_bsc.json &
uv run trading_bot.py --config bots/aggressive_sol.json &
uv run trading_bot.py --config bots/momentum_bsc.json &
```

#### 3. 完整部署示例
```bash
# 1. 启动展示页面
uv run main.py &

# 2. 启动多个交易机器人
uv run trading_bot.py --config bots/conservative_bsc.json &
uv run trading_bot.py --config bots/moderate_sol.json &

# 3. 查看运行状态
ps aux | grep "uv run"
```

### 配置文件管理

创建配置文件目录：
```bash
mkdir -p bots/
```

### 访问地址
- 展示页面：http://localhost:8000
- API文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

## 项目结构
```
aip_dex/
├── main.py                 # 主应用入口(展示页面)
├── trading_bot.py          # 交易机器人入口
├── static/                 # 前端文件
├── api/                    # API路由
├── models/                 # 数据模型
├── services/               # 业务逻辑
├── database/               # 数据库相关
├── llm/                    # LLM分析器
│   ├── trading_analyzer.py # 交易决策分析器（两阶段筛选）
│   └── token_analyzer.py   # 代币分析器
├── bots/                   # 机器人配置文件
│   ├── conservative_bsc.json
│   ├── moderate_sol.json
│   └── aggressive_bsc.json
└── .env                    # 环境变量配置
```

## 错误处理

常见HTTP状态码：
- `200 OK`：成功
- `400 Bad Request`：参数错误
- `404 Not Found`：资源不存在
- `500 Internal Server Error`：服务器错误

错误响应格式：
```json
{
  "error": {
    "code": "BOT_NOT_FOUND",
    "message": "Bot not found",
    "details": {"bot_id": "bot_001"}
  }
}
```