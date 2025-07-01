# AIP DEX Trading Bot 设置和使用指南

## 概述

AIP DEX Trading Bot 是一个虚拟的加密货币交易机器人，使用 LLM 辅助决策进行自动化交易。支持 BSC 和 Solana 链，提供多种交易策略。

## 项目结构

```
aip_dex/
├── models/
│   └── database.py                 # 数据库模型
├── services/
│   ├── trading_service.py          # 交易服务（完整版）
│   ├── trading_service_clean.py    # 交易服务（简化版）
│   └── token_service.py            # 代币服务
├── llm/
│   ├── trading_analyzer.py         # 交易决策分析器
│   └── token_analyzer.py           # 代币分析器
├── bots/
│   └── conservative_bsc.json       # 保守策略配置示例
├── trading_bot.py                  # 主要交易机器人实现
├── run_bot.py                      # 简化运行脚本
└── TRADING_BOT.md                  # 详细文档
```

## 安装和配置

### 1. 环境准备

```bash
# 确保已安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装依赖
uv sync

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置 OPENAI_API_KEY 和 DATABASE_URL
```

### 2. 数据库初始化

```bash
# 初始化数据库（会自动创建表和索引）
uv run python -c "from models.database import init_database; init_database()"
```

## 启动交易机器人

### 方式一：使用简化脚本

```bash
# 使用默认配置启动
uv run run_bot.py

# 使用自定义参数
uv run run_bot.py --name "My Bot" --balance 5000 --chain bsc --strategy moderate
```

### 方式二：使用核心交易机器人

```bash
# 使用命令行参数
uv run trading_bot.py --name "Conservative Bot" --balance 10000 --strategy conservative

# 查看所有参数选项
uv run trading_bot.py --help
```

### 方式三：使用配置文件

```bash
# 使用预定义配置文件
uv run trading_bot.py --config bots/conservative_bsc.json

# 创建自定义配置文件
cp bots/conservative_bsc.json bots/my_config.json
# 编辑配置文件
uv run trading_bot.py --config bots/my_config.json
```

## 配置参数说明

### 基础配置

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| bot_name | string | 必填 | 机器人名称 |
| account_address | string | 必填 | 钱包地址 |
| chain | string | "bsc" | 区块链：bsc/solana |
| initial_balance_usd | float | 必填 | 初始USD余额 |
| strategy_type | string | "conservative" | 策略类型 |

### 交易参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| gas_fee_native | float | 0.001 | Gas费用（原生代币） |
| trading_fee_percentage | float | 0.5 | 交易手续费率(%) |
| slippage_tolerance | float | 1.0 | 滑点容忍度(%) |
| min_trade_amount_usd | float | 10.0 | 最小交易金额 |
| max_daily_trades | int | 10 | 每日最大交易次数 |

### 策略参数

| 策略类型 | 最大仓位 | 止损 | 止盈 | 最低收益 | 置信度阈值 |
|----------|----------|------|------|----------|------------|
| conservative | 10% | 5% | 15% | 5% | 0.8 |
| moderate | 20% | 10% | 25% | 3% | 0.7 |
| aggressive | 40% | 15% | 50% | 1% | 0.6 |

### 运行控制

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| polling_interval_hours | int | 1 | 轮询间隔（小时） |
| llm_confidence_threshold | float | 0.7 | LLM决策置信度阈值 |
| enable_stop_loss | bool | true | 启用止损 |
| enable_take_profit | bool | true | 启用止盈 |
| is_active | bool | true | 机器人开关 |

## 交易逻辑

### 两阶段决策模式

**阶段一：卖出决策**
1. 获取当前持仓列表
2. 分析每个持仓的技术指标和市场状况
3. 计算不同卖出比例的预期收益率
4. LLM 分析决定是否卖出及卖出比例

**阶段二：买入决策**
1. 获取可用代币列表
2. 筛选出最有潜力的候选代币
3. 分析技术指标、基本面、风险因素
4. LLM 决定是否买入及买入金额

### 成本计算机制

**买入成本影响**：
- 交易成本会增加平均持仓成本
- 新平均成本 = (原持仓成本 + 新买入成本 + 交易费用) / 总数量

**卖出成本影响**：
- 交易成本也会影响剩余持仓的平均成本
- 剩余平均成本 = (原总成本 - 卖出成本基础 + 交易费用) / 剩余数量

## 监控和管理

### 查看机器人状态

```bash
# 通过 API 查看状态（需要启动 main.py）
curl http://localhost:8000/api/bots

# 查看特定机器人
curl http://localhost:8000/api/bots/{bot_id}

# 查看交易历史
curl http://localhost:8000/api/bots/{bot_id}/transactions
```

### 日志监控

机器人运行时会输出详细日志：
- 🤖 初始化信息
- 🔄 交易周期状态
- 📊 卖出分析结果
- 🛒 买入分析结果
- ✅ 交易执行成功
- ❌ 错误信息

### 手动停止

- 使用 `Ctrl+C` 优雅停止机器人
- 机器人会完成当前交易周期后停止

## 故障排除

### 常见问题

1. **数据库连接失败**
   ```bash
   # 检查 DATABASE_URL 是否正确配置
   echo $DATABASE_URL
   
   # 测试数据库连接
   uv run python -c "from models.database import engine; print(engine.execute('SELECT 1').scalar())"
   ```

2. **LLM API 调用失败**
   ```bash
   # 检查 OpenAI API Key
   echo $OPENAI_API_KEY
   
   # 测试 API 连接
   uv run python -c "from openai import OpenAI; client = OpenAI(); print('API OK')"
   ```

3. **模块导入错误**
   ```bash
   # 确保在正确目录运行
   cd examples/aip_dex
   
   # 检查 Python 路径
   uv run python -c "import sys; print(sys.path)"
   ```

### 调试模式

在代码中添加更多调试信息：

```python
# 在 trading_bot.py 中增加调试输出
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 扩展和定制

### 添加新策略

1. 在 `_get_strategy_defaults()` 中添加新策略参数
2. 在 LLM 提示中包含策略特定的指导原则
3. 测试新策略的风险收益特性

### 集成新数据源

1. 在 `token_service.py` 中添加新的数据提供商
2. 更新数据库模型以支持新字段
3. 在 LLM 分析中包含新数据

### 自定义决策逻辑

1. 修改 `trading_analyzer.py` 中的 LLM 提示
2. 添加新的技术指标计算
3. 实现自定义风险管理规则

## 性能优化

### 数据库优化

- 使用索引加速查询
- 定期清理历史数据
- 优化数据库连接池

### LLM 调用优化

- 缓存重复查询结果
- 批量处理多个决策
- 使用更快的模型进行初步筛选

### 系统资源

- 监控内存使用情况
- 合理设置轮询间隔
- 使用异步处理提高并发性

## 安全考虑

1. **API Key 保护**：确保 OpenAI API Key 安全存储
2. **数据库安全**：使用强密码和 SSL 连接
3. **日志安全**：避免在日志中记录敏感信息
4. **权限控制**：限制文件系统访问权限

## 未来改进

- [ ] 添加更多技术指标
- [ ] 实现动态策略调整
- [ ] 集成更多数据源
- [ ] 添加回测功能
- [ ] 实现风险管理仪表板
- [ ] 支持更多区块链网络 