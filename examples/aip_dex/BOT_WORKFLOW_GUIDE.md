# AIP DEX Trading Bot 工作流程指南

## 概述

本文档描述了 AIP DEX Trading Bot 系统的完整工作流程，从用户登录到交易执行的全过程。

## 系统架构流程

### 1. 用户认证与账户创建

#### 1.1 MetaMask 登录
- 用户通过 MetaMask 钱包进行身份验证
- 系统验证用户的钱包地址和签名
- 成功登录后创建或关联 `BotOwner` 账户

#### 1.2 BotOwner 创建
```sql
BotOwner {
    id: UUID (主键)
    wallet_address: String (钱包地址)
    username: String (用户名)
    email: String (邮箱，可选)
    created_at: DateTime
    updated_at: DateTime
}
```

### 2. 策略管理

#### 2.1 创建交易策略 (TradingStrategy)
用户可以创建自定义的交易策略：

```sql
TradingStrategy {
    id: UUID (主键)
    strategy_name: String (策略名称)
    strategy_type: String (策略类型)
    polling_interval_hours: Float (轮询间隔，默认1小时)
    max_position_size_usd: Float (最大仓位)
    stop_loss_percentage: Float (止损百分比)
    take_profit_percentage: Float (止盈百分比)
    // ... 其他策略参数
}
```

#### 2.2 策略配置参数
- **轮询间隔**: 控制bot执行交易的时间间隔（默认1小时）
- **风险管理**: 止损、止盈、最大仓位等参数
- **交易逻辑**: 买入/卖出条件和算法

### 3. 交易机器人管理

#### 3.1 创建交易机器人 (TradingBot)
用户创建交易机器人并进行配置：

```sql
TradingBot {
    id: UUID (主键)
    bot_name: String (机器人名称)
    owner_id: UUID (关联到BotOwner)
    strategy_id: UUID (关联到TradingStrategy)
    account_address: String (交易账户地址，来自BotOwner的wallet_address)
    chain: String (区块链网络)
    initial_balance_usd: Decimal (初始余额)
    current_balance_usd: Decimal (当前余额)
    is_active: Boolean (是否激活)
    is_configured: Boolean (是否已配置)
    last_activity_at: DateTime (最后活动时间)
    // ... 其他字段
}
```

#### 3.2 机器人配置流程
1. **创建机器人**: 设置基本信息（名称、账户地址、初始余额等）
2. **关联策略**: 将机器人与已创建的交易策略关联
3. **配置验证**: 确保机器人有有效的 owner_id 和 strategy_id
4. **激活机器人**: 设置 `is_active = true` 启动交易

### 4. 后台执行机制

#### 4.1 轮询调度器
系统运行一个后台调度器，负责管理所有活跃的交易机器人：

```python
# 调度器配置
SCHEDULER_POLLING_INTERVAL = 5分钟  # 系统轮询间隔
DEFAULT_BOT_INTERVAL = 1小时        # 默认机器人交易间隔
```

#### 4.2 执行条件
机器人满足以下条件时会执行交易：
- `is_active = true` (机器人已激活)
- `is_configured = true` (机器人已正确配置)
- `owner_id` 和 `strategy_id` 不为空
- 距离上次执行时间超过策略设定的 `polling_interval_hours`

#### 4.3 执行流程
```
每5分钟执行一次:
├── 查询所有 active && configured 的机器人
├── 检查每个机器人的执行条件
│   ├── 检查时间间隔 (last_activity_at + polling_interval_hours)
│   └── 验证配置完整性
├── 符合条件的机器人执行交易周期
│   ├── 初始化交易机器人实例
│   ├── 执行 _trading_cycle()
│   └── 更新 last_activity_at
└── 记录执行日志和错误处理
```

### 5. 交易执行逻辑

#### 5.1 交易周期 (_trading_cycle)
每个交易周期包含以下步骤：
1. **市场数据获取**: 获取当前市场价格和技术指标
2. **持仓分析**: 分析当前持仓状态
3. **LLM决策**: 基于策略和市场数据进行AI决策
4. **交易执行**: 执行买入/卖出操作
5. **记录更新**: 更新交易记录和机器人状态

#### 5.2 决策记录
所有交易决策都会记录在 `LLMDecision` 表中：
```sql
LLMDecision {
    id: UUID
    bot_id: UUID (关联机器人)
    decision_type: String (BUY/SELL/HOLD)
    recommended_action: String (推荐操作)
    reasoning: Text (决策理由)
    confidence_score: Float (置信度)
    market_analysis: JSON (市场分析数据)
    created_at: DateTime
}
```

### 6. 监控和管理

#### 6.1 实时状态监控
- 机器人运行状态
- 交易执行情况
- 盈亏统计
- 错误日志

#### 6.2 用户控制
用户可以通过 API 或 Web 界面：
- 启动/停止机器人
- 修改策略参数
- 查看交易历史
- 监控实时状态

## 关键文件说明

### `/run_bot.py`
主要的机器人运行脚本，包含：
- `run_bot_polling()`: 后台轮询机制
- `should_run_bot()`: 判断机器人是否应该执行
- `update_bot_trading_time()`: 更新机器人活动时间
- 机器人管理功能（创建、更新、状态控制）

### 使用示例

```bash
# 运行后台轮询（默认5分钟间隔）
python run_bot.py poll

# 自定义轮询间隔（10分钟）
python run_bot.py poll --interval 10

# 创建新机器人
python run_bot.py create --name "MyBot" --address "0x123..." --chain "ethereum" --balance 1000

# 设置机器人策略
python run_bot.py set-strategy --bot-id "bot-uuid" --strategy-id "strategy-uuid"

# 激活机器人
python run_bot.py set-status --bot-id "bot-uuid" --active
```

## 安全考虑

1. **钱包安全**: MetaMask 私钥不存储在服务器
2. **权限控制**: 用户只能管理自己的机器人
3. **资金安全**: 设置最大交易限额和风险控制
4. **错误处理**: 完善的异常处理和日志记录

## 扩展性

系统设计支持：
- 多种交易策略算法
- 不同区块链网络
- 自定义轮询间隔
- 灵活的风险管理参数
- 可扩展的决策引擎

---

*本文档描述了 AIP DEX Trading Bot 系统的完整工作流程，为开发者和用户提供了系统架构和使用指南。*