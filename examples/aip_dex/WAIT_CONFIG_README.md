# AIP DEX Trading Bot - 等待配置启动逻辑

## 概述

新的启动逻辑允许机器人在没有配置 owner 和 strategy 的情况下启动，然后等待配置完成后再开始交易。

## 主要功能

### 1. 灵活的机器人启动

机器人可以在以下两种模式下启动：

#### 模式A：立即配置（传统方式）
```python
bot_config = {
    "bot_name": "My Bot",
    "account_address": "0x1234567890abcdef1234567890abcdef12345678",
    "chain": "bsc",
    "initial_balance_usd": 5000.0,
    "owner_id": owner.id,        # 立即配置
    "strategy_id": strategy.id,   # 立即配置
    "is_active": True
}
```

#### 模式B：灵活启动（新方式）
```python
bot_config = {
    "bot_name": "My Bot",
    "account_address": "0x1234567890abcdef1234567890abcdef12345678",
    "chain": "bsc",
    "initial_balance_usd": 5000.0,
    # 不提供 owner_id 和 strategy_id
    "is_active": True
}
```

### 2. 等待配置完成

当机器人没有配置 owner 和 strategy 时，系统会：

1. **检查配置状态**：每5分钟检查一次机器人是否已配置
2. **显示状态信息**：显示当前的 owner_id、strategy_id 和配置状态
3. **等待配置**：直到机器人被配置后才开始交易
4. **优雅退出**：支持 Ctrl+C 中断等待

## 使用方法

### 命令行参数

```bash
# 使用默认配置并等待配置完成
python run_bot.py --default --wait-config

# 使用自定义配置文件并等待配置完成
python run_bot.py --config my_config.json --wait-config

# 自定义检查间隔（默认5分钟）
python run_bot.py --default --wait-config --check-interval 10

# 不使用等待模式（传统方式）
python run_bot.py --default
```

### 参数说明

- `--wait-config`: 启用等待配置模式
- `--check-interval`: 设置检查间隔（分钟），默认5分钟
- `--config`: 指定配置文件路径
- `--default`: 使用默认配置

## 配置检查逻辑

### 检查条件

机器人被认为已配置当且仅当：
- `is_configured = True`
- `owner_id` 不为空
- `strategy_id` 不为空

### 检查流程

1. **初始化检查**：启动时检查机器人配置状态
2. **循环等待**：如果未配置，每5分钟检查一次
3. **状态显示**：每次检查都显示详细的配置状态
4. **开始交易**：一旦配置完成，立即开始交易循环

## 示例输出

### 未配置状态
```
🔄 Configuration check #1 at 2024-01-15 10:30:00
⏳ Bot is not configured:
   Owner ID: None
   Strategy ID: None
   Is Configured: False
⏳ Next check in 5 minutes...
```

### 已配置状态
```
🔄 Configuration check #3 at 2024-01-15 10:40:00
✅ Bot is configured:
   Owner ID: 550e8400-e29b-41d4-a716-446655440000
   Strategy ID: 550e8400-e29b-41d4-a716-446655440001
   Strategy Type: moderate
✅ Bot is ready to start trading!
```

## 配置机器人

### 方法1：使用 TradingService.configure_bot()

```python
from services.trading_service import TradingService

trading_service = TradingService()
configured_bot = await trading_service.configure_bot(
    db, bot.id, owner.id, strategy.id
)
```

### 方法2：直接更新数据库

```python
bot = db.query(TradingBot).filter(TradingBot.id == bot_id).first()
bot.owner_id = owner_id
bot.strategy_id = strategy_id
bot.is_configured = True
db.commit()
```

## 演示脚本

运行演示脚本来体验完整的功能：

```bash
python example_wait_config.py
```

这个脚本会：
1. 创建一个 owner 和 strategy
2. 创建一个未配置的机器人
3. 模拟等待过程
4. 配置机器人
5. 显示配置结果

## 错误处理

### 常见错误

1. **机器人未找到**
   ```
   ❌ Bot with ID xxx not found
   ```

2. **配置检查失败**
   ```
   ❌ Error checking bot configuration: xxx
   ```

3. **数据库连接错误**
   ```
   ❌ Failed to initialize database
   ```

### 调试技巧

1. 检查数据库连接
2. 验证机器人ID是否正确
3. 确认 owner 和 strategy 是否存在
4. 查看详细的错误日志

## 最佳实践

### 1. 启动顺序

1. 先创建 owner 和 strategy
2. 启动机器人（可选配置）
3. 配置机器人（如果未立即配置）
4. 机器人自动开始交易

### 2. 监控配置

- 使用 `--check-interval` 调整检查频率
- 监控日志文件了解配置状态
- 设置适当的告警机制

### 3. 错误恢复

- 机器人会自动重试配置检查
- 支持优雅的中断和重启
- 保持数据库连接的健康状态

## 技术细节

### 检查间隔

- 默认：5分钟
- 可配置：1-60分钟
- 支持秒级精度

### 数据库查询

```sql
SELECT id, owner_id, strategy_id, is_configured 
FROM trading_bots 
WHERE id = ?
```

### 配置验证

```python
is_configured = bot.is_configured and bot.owner_id and bot.strategy_id
```

## 总结

新的等待配置启动逻辑提供了：

- **灵活的部署**：支持分阶段配置和部署
- **自动检测**：自动检测配置状态变化
- **用户友好**：清晰的状态显示和进度提示
- **可配置性**：可调整检查间隔和等待行为
- **错误恢复**：健壮的错误处理和恢复机制

这个系统为交易机器人提供了更灵活和用户友好的启动体验。 