# AIP DEX Token Data Scheduler

这个调度器系统会定期从BirdEye API获取top tokens，并使用DexScreener获取对应的pool信息，计算metrics和signals，然后保存到数据库中。

## 功能特性

- 🔄 **定时获取**: 每小时自动获取top 50 tokens
- 💾 **数据存储**: 自动保存和更新token信息到数据库
- 🏊 **Pool数据**: 获取每个token对应的交易池信息
- 📊 **指标计算**: 计算技术指标和交易信号
- 🚨 **错误处理**: 完善的错误处理和重试机制
- 📝 **日志记录**: 详细的日志记录和监控
- 🎯 **灵活更新**: 支持更新所有数据库tokens或仅新获取的tokens
- 🔍 **专用工具**: 专门的脚本用于更新已有数据库tokens

## 系统架构

```
BirdEye API → Top Tokens → Database (Token)
     ↓
DexScreener API → Pool Data → Database (TokenPool + PoolMetric)
     ↓
Indicators Calculator → Signals → Database (TokenMetric)
```

## 环境配置

### 1. 复制环境配置文件

```bash
cp env.scheduler.example .env
```

### 2. 配置环境变量

编辑 `.env` 文件：

```bash
# 必需配置
DATABASE_URL=postgresql://username:password@localhost:5432/aip_dex
BIRDEYE_API_KEY=your_birdeye_api_key_here

# 可选配置
DEFAULT_CHAIN=bsc
DEFAULT_FETCH_LIMIT=50
DEFAULT_INTERVAL_HOURS=1
```

### 3. 数据库设置

确保PostgreSQL已启动并创建数据库：

```sql
CREATE DATABASE aip_dex;
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 基本使用

```bash
# 运行连续调度器（每小时更新）
python run_scheduler.py

# 指定链和限制
python run_scheduler.py --chain bsc --limit 50

# 自定义更新间隔（2小时）
python run_scheduler.py --interval 2
```

### 更新已有数据库中的Tokens

如果你已经有tokens在数据库中，可以专门更新它们的pool信息：

```bash
# 查看数据库中的tokens（不执行更新）
python update_database_pools.py --dry-run

# 更新数据库中所有tokens的pool数据
python update_database_pools.py --chain bsc

# 更新其他链的tokens
python update_database_pools.py --chain solana
```

### 测试运行

```bash
# 运行一次后退出（用于测试）
python run_scheduler.py --single-run

# 仅更新新获取的tokens（而非数据库中所有tokens）
python run_scheduler.py --single-run --update-new-only
```

### 命令行参数

| 参数 | 默认值 | 描述 |
|------|--------|------|
| `--chain` | `bsc` | 区块链网络 (bsc, solana, etc.) |
| `--limit` | `50` | 获取的top tokens数量 |
| `--interval` | `1` | 更新间隔（小时） |
| `--single-run` | `False` | 运行一次后退出 |
| `--update-new-only` | `False` | 仅更新新获取的tokens的pools（默认：更新所有） |

## 数据结构

### Token表
- 基本token信息（名称、符号、合约地址等）

### TokenPool表
- Token交易池信息（DEX、配对、池地址等）

### PoolMetric表
- 池的实时指标（价格、交易量、流动性等）

### TokenMetric表
- Token的聚合指标和信号

## 监控和日志

### 日志文件

日志会保存到 `scheduler.log` 文件中，包含：
- 获取的tokens数量
- 更新的pools数量  
- 计算的signals数量
- 错误和警告信息

### 日志级别

```python
# 在.env文件中设置
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

### 示例日志输出

```
2024-01-01 12:00:00 - scheduler - INFO - Starting scheduled update
2024-01-01 12:00:05 - scheduler - INFO - Successfully fetched 50 tokens
2024-01-01 12:00:30 - scheduler - INFO - Pool update stats: {'updated_pools': 45, 'new_pools': 5, 'errors': 0}
2024-01-01 12:01:00 - scheduler - INFO - Signal calculation stats: {'calculated': 50, 'errors': 0}
2024-01-01 12:01:05 - scheduler - INFO - Update completed successfully!
```

## 错误处理

### 常见错误和解决方案

1. **Database Connection Error**
   ```
   Error: failed to connect to database
   ```
   - 检查DATABASE_URL是否正确
   - 确保PostgreSQL服务正在运行
   - 检查数据库权限

2. **API Key Error**
   ```
   Error: invalid API key
   ```
   - 检查BIRDEYE_API_KEY是否设置
   - 验证API key是否有效

3. **Rate Limiting**
   ```
   Error: too many requests
   ```
   - 调度器会自动重试
   - 可以增加REQUEST_DELAY_SECONDS

## 性能优化

### 数据库优化

```sql
-- 创建索引以提升查询性能
CREATE INDEX idx_tokens_symbol_chain ON tokens(symbol, chain);
CREATE INDEX idx_pool_metrics_updated ON pool_metrics(updated_at);
CREATE INDEX idx_token_metrics_calculated ON token_metrics(last_calculation_at);
```

### 内存使用

- 调度器会自动清理HTTP连接
- 数据库连接会在每次更新后关闭
- 建议监控内存使用情况

## 扩展功能

### 支持更多链

在 `scheduler.py` 中修改：

```python
# 支持多链同时获取
chains = ["bsc", "ethereum", "polygon"]
for chain in chains:
    scheduler = TokenDataScheduler(chain=chain)
    await scheduler.run_single_update()
```

### 自定义指标

在 `indicators/calculator.py` 中添加新的技术指标：

```python
def calculate_custom_indicator(self, data):
    # 实现自定义指标逻辑
    pass
```

## 故障排除

### 检查系统状态

```bash
# 检查数据库连接
python -c "from models.database import engine; print(engine.execute('SELECT 1').scalar())"

# 检查API连接
python -c "from data_aggregator.birdeye import BirdEyeProvider; import asyncio; asyncio.run(BirdEyeProvider().get_top_tokens())"
```

### 重置数据库

```python
from models.database import Base, engine
Base.metadata.drop_all(engine)  # 删除所有表
Base.metadata.create_all(engine)  # 重新创建表
```

## 贡献

如需添加新功能或修复bug，请：

1. Fork项目
2. 创建特性分支
3. 提交更改
4. 创建Pull Request

## 许可证

MIT License 