# AIP DEX Trading Bot - Owner & Strategy Management Guide

本指南介绍AIP DEX交易机器人的所有者管理和策略管理功能。

## 概述

新的系统引入了以下核心概念：

1. **BotOwner（机器人所有者）** - 管理交易机器人的用户
2. **TradingStrategy（交易策略）** - 包含参数设置和策略描述的完整策略配置
3. **TradingBot（交易机器人）** - 关联所有者和策略的交易机器人实例

## 核心概念

### BotOwner（机器人所有者）

每个交易机器人必须属于一个所有者。所有者具有以下特性：

- **基本信息**：姓名、邮箱、钱包地址、电话
- **权限控制**：订阅等级、最大机器人数量限制
- **统计信息**：创建的机器人数量、交易量等

```python
# 创建所有者示例
owner_data = BotOwnerCreate(
    owner_name="John Doe",
    email="john.doe@example.com",
    wallet_address="0x1234567890abcdef1234567890abcdef12345678",
    phone="+1234567890",
    subscription_tier="premium",  # basic/premium/enterprise
    max_bots_allowed=10
)
```

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

```python
# 创建策略示例
strategy_data = TradingStrategyCreate(
    strategy_name="My Custom Strategy",
    strategy_type="user_defined",
    risk_level="medium",
    
    # 数值参数
    max_position_size=Decimal("25.0"),
    stop_loss_percentage=Decimal("8.0"),
    take_profit_percentage=Decimal("30.0"),
    
    # 策略描述
    buy_strategy_description="买入策略：寻找具有强动量且持有人增长的代币...",
    sell_strategy_description="卖出策略：当动量减弱或达到利润目标时退出...",
    filter_strategy_description="筛选条件：市值>500万，交易量>7.5万，正价格动量...",
    summary_strategy_description="平衡策略：结合动量交易和均值回归原则..."
)
```

## 系统架构

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

## 使用流程

### 1. 创建所有者

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

### 2. 创建策略

#### 方法A：使用默认策略

```python
# 为所有者创建所有默认策略
strategies = await owner_service.create_default_strategies(db, owner.id)

# 默认策略包括：
# - Conservative (保守型)
# - Moderate (平衡型)
# - Aggressive (激进型)
```

#### 方法B：创建自定义策略

```python
from api.schemas import TradingStrategyCreate

custom_strategy = TradingStrategyCreate(
    strategy_name="My Strategy",
    strategy_type="user_defined",
    risk_level="medium",
    max_position_size=Decimal("20.0"),
    stop_loss_percentage=Decimal("10.0"),
    take_profit_percentage=Decimal("25.0"),
    buy_strategy_description="详细的买入策略描述...",
    sell_strategy_description="详细的卖出策略描述...",
    filter_strategy_description="详细的筛选策略描述...",
    summary_strategy_description="策略总结描述..."
)

strategy = await owner_service.create_trading_strategy(db, owner.id, custom_strategy)
```

### 3. 创建交易机器人

#### 方法A：立即配置（传统方式）

```python
from services.trading_service import TradingService

trading_service = TradingService()

bot_config = {
    "bot_name": "My Trading Bot",
    "account_address": "0x1234567890abcdef1234567890abcdef12345678",
    "chain": "bsc",
    "initial_balance_usd": 5000.0,
    "owner_id": owner.id,
    "strategy_id": strategy.id,  # 立即配置
    "is_active": True
}

bot = await trading_service.create_trading_bot(db, bot_config)
```

#### 方法B：灵活启动（新方式）

```python
# 1. 创建未配置的机器人
bot_config = {
    "bot_name": "My Trading Bot",
    "account_address": "0x1234567890abcdef1234567890abcdef12345678",
    "chain": "bsc",
    "initial_balance_usd": 5000.0,
    # 不提供 owner_id 和 strategy_id
    "is_active": True
}

bot = await trading_service.create_trading_bot(db, bot_config)

# 2. 稍后配置机器人
configured_bot = await trading_service.configure_bot(
    db, bot.id, owner.id, strategy.id
)
```

## 策略管理功能

### 1. 策略关联

机器人直接关联策略实体，所有策略参数都从策略中获取：

```python
bot_config = {
    # ... 基础配置
    "strategy_id": strategy.id,  # 必须提供有效的策略ID
}
```

### 2. 策略更新

可以随时更新策略，影响所有使用该策略的机器人：

```python
from api.schemas import TradingStrategyUpdate

update_data = TradingStrategyUpdate(
    max_position_size=Decimal("30.0"),
    take_profit_percentage=Decimal("35.0"),
    buy_strategy_description="更新的买入策略描述..."
)

updated_strategy = await owner_service.update_trading_strategy(
    db, strategy.id, update_data
)
```

### 3. 策略共享

策略可以设置为公开，供其他用户使用：

```python
update_data = TradingStrategyUpdate(is_public=True)
await owner_service.update_trading_strategy(db, strategy.id, update_data)
```

## 默认策略详情

### Conservative（保守型）
- **风险等级**：低
- **最大仓位**：10%
- **止损**：5%
- **止盈**：15%
- **适用场景**：风险厌恶型投资者，追求稳定收益

### Moderate（平衡型）
- **风险等级**：中
- **最大仓位**：20%
- **止损**：10%
- **止盈**：25%
- **适用场景**：平衡风险与收益的投资者

### Aggressive（激进型）
- **风险等级**：高
- **最大仓位**：40%
- **止损**：15%
- **止盈**：50%
- **适用场景**：追求高收益，能承受高风险的投资者

### Momentum（动量型）
- **风险等级**：中
- **最大仓位**：30%
- **止损**：12%
- **止盈**：35%
- **适用场景**：趋势跟踪，动量交易

### Mean Reversion（均值回归型）
- **风险等级**：中
- **最大仓位**：25%
- **止损**：8%
- **止盈**：20%
- **适用场景**：均值回归，反转交易

## 示例脚本

运行示例脚本来体验完整的功能：

```bash
cd examples/aip_dex
python examples/owner_strategy_example.py
```

这个脚本演示了：
1. 创建所有者
2. 创建默认策略
3. 创建自定义策略
4. 创建使用不同策略的机器人
5. 更新策略
6. 列出所有者和策略信息

## 数据库结构

### BotOwner表
- `id`: 主键
- `owner_name`: 所有者姓名
- `email`: 邮箱（唯一）
- `wallet_address`: 钱包地址（唯一）
- `subscription_tier`: 订阅等级
- `max_bots_allowed`: 最大机器人数量
- `total_bots_created`: 已创建机器人数量
- `total_trading_volume_usd`: 总交易量

### TradingStrategy表
- `id`: 主键
- `owner_id`: 所有者ID
- `strategy_name`: 策略名称
- `strategy_type`: 策略类型
- `risk_level`: 风险等级
- 数值参数字段（max_position_size, stop_loss_percentage等）
- 描述性字段（buy_strategy_description等）
- `is_public`: 是否公开
- `is_default`: 是否默认策略
- `usage_count`: 使用次数
- `success_rate`: 成功率

### TradingBot表（灵活配置）
- `owner_id`: 所有者ID（可选，启动后可以设置）
- `strategy_id`: 策略ID（可选，启动后可以设置）
- `is_configured`: 是否已配置（有owner和strategy）
- 移除了所有策略参数字段，现在直接从策略实体获取
- 保留了基础配置、资金配置和统计信息

## 最佳实践

1. **策略设计**：
   - 明确策略的风险等级和目标
   - 详细描述买入、卖出和筛选逻辑
   - 定期评估和优化策略

2. **风险管理**：
   - 设置合理的止损和止盈水平
   - 控制单币最大仓位比例
   - 监控策略表现

3. **策略管理**：
   - 为不同市场环境准备不同策略
   - 定期更新策略参数
   - 记录策略变更历史

4. **性能监控**：
   - 跟踪策略成功率
   - 监控平均收益率
   - 分析策略在不同市场条件下的表现

## 故障排除

### 常见问题

1. **创建机器人时提示"owner_id is required"**
   - 确保在配置中包含有效的owner_id
   - 验证所有者是否存在

2. **策略参数无效**
   - 检查数值参数是否在有效范围内
   - 确保Decimal类型参数格式正确

3. **策略更新失败**
   - 检查策略是否被机器人使用中
   - 验证更新参数的有效性

### 调试技巧

1. 使用示例脚本测试功能
2. 检查数据库连接和权限
3. 查看详细的错误日志
4. 验证数据格式和约束条件

## 总结

灵活的所有者管理和策略管理系统提供了：

- **灵活的机器人启动**：机器人可以不依赖owner和strategy启动，启动后处于待激活状态
- **简化的策略关联**：机器人直接关联策略实体，无需复杂的参数覆盖
- **完整的策略描述**：包含数值参数和文字描述
- **策略共享机制**：支持公开策略供他人使用
- **性能跟踪**：记录策略使用情况和成功率
- **权限控制**：基于所有者的机器人数量限制

这个系统为交易机器人提供了灵活而强大的配置管理能力，同时保持了良好的可扩展性和易用性。

### 主要改进

1. **灵活的机器人创建**：可以选择立即配置或稍后配置
2. **移除了参数覆盖**：所有策略参数都从策略实体获取
3. **更清晰的数据结构**：TradingBot表只包含基础信息
4. **更容易维护**：策略变更直接影响所有关联的机器人
5. **更灵活的部署**：支持分阶段配置和部署 