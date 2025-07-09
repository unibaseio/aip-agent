# MetaMask Login & Bot Management - AIP DEX Trading Bot

## 概述

新的MetaMask登录系统允许用户通过MetaMask钱包进行身份验证，认领未配置的交易机器人，并创建和管理交易策略。

## 主要功能

### 1. MetaMask 钱包登录

- **安全认证**：使用MetaMask钱包进行身份验证
- **自动用户创建**：首次登录时自动创建用户账户
- **持久登录**：登录状态持久化保存
- **多链支持**：支持以太坊、BSC等网络

### 2. Bot 认领系统

- **查看未认领的Bot**：显示所有没有owner的机器人
- **一键认领**：连接MetaMask后可以认领机器人
- **所有权验证**：确保只有钱包所有者可以认领

### 3. 策略管理系统

- **创建自定义策略**：用户可以创建自己的交易策略
- **策略参数配置**：设置仓位大小、止损、止盈等参数
- **策略类型选择**：支持保守型、平衡型、激进型等策略
- **策略描述**：详细的买入、卖出、筛选策略描述

### 4. Bot 配置系统

- **策略关联**：为认领的机器人配置交易策略
- **灵活配置**：支持随时更换策略
- **配置验证**：确保配置的有效性

## 页面结构

### 1. 登录页面 (`/login`)

```
┌─────────────────────────────────────┐
│           MetaMask Login            │
├─────────────────────────────────────┤
│  🤖 AIP DEX Trading Bot            │
│  Connect your MetaMask wallet      │
│                                     │
│  [Connect MetaMask]                │
│                                     │
│  Features:                         │
│  ✅ Secure wallet authentication    │
│  ✅ Claim unclaimed trading bots   │
│  ✅ Configure trading strategies   │
│  ✅ Manage your trading portfolio  │
└─────────────────────────────────────┘
```

### 2. Bot管理页面 (`/bot-management`)

```
┌─────────────────────────────────────┐
│         Bot Management              │
├─────────────────────────────────────┤
│  Unclaimed Bots                    │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐│
│  │ Bot 1   │ │ Bot 2   │ │ Bot 3   ││
│  │ [Claim] │ │ [Claim] │ │ [Claim] ││
│  └─────────┘ └─────────┘ └─────────┘│
│                                     │
│  My Strategies                      │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐│
│  │Strategy1│ │Strategy2│ │Strategy3││
│  │Type: Mod│ │Type: Agg│ │Type: Con││
│  └─────────┘ └─────────┘ └─────────┘│
│                                     │
│  My Claimed Bots                   │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐│
│  │My Bot 1 │ │My Bot 2 │ │My Bot 3 ││
│  │[Config] │ │[Config] │ │[Config] ││
│  └─────────┘ └─────────┘ └─────────┘│
└─────────────────────────────────────┘
```

## 使用流程

### 1. 用户登录流程

```mermaid
graph TD
    A[访问登录页面] --> B[点击Connect MetaMask]
    B --> C[MetaMask弹出连接请求]
    C --> D[用户确认连接]
    D --> E[获取钱包地址]
    E --> F[生成签名消息]
    F --> G[用户签名]
    G --> H[发送认证请求]
    H --> I[创建或获取用户账户]
    I --> J[登录成功]
    J --> K[跳转到主页面]
```

### 2. Bot认领流程

```mermaid
graph TD
    A[查看未认领的Bot] --> B[选择要认领的Bot]
    B --> C[点击Claim Bot]
    C --> D[验证MetaMask连接]
    D --> E[发送认领请求]
    E --> F[验证钱包地址]
    F --> G[更新Bot所有权]
    G --> H[认领成功]
    H --> I[Bot出现在My Bots列表]
```

### 3. 策略创建流程

```mermaid
graph TD
    A[点击Create Strategy] --> B[填写策略信息]
    B --> C[设置策略参数]
    C --> D[编写策略描述]
    D --> E[提交创建请求]
    E --> F[验证用户身份]
    F --> G[创建策略记录]
    G --> H[策略创建成功]
    H --> I[策略出现在My Strategies列表]
```

### 4. Bot配置流程

```mermaid
graph TD
    A[选择已认领的Bot] --> B[点击Configure Bot]
    B --> C[选择交易策略]
    C --> D[查看策略详情]
    D --> E[确认配置]
    E --> F[发送配置请求]
    F --> G[更新Bot配置]
    G --> H[配置成功]
    H --> I[Bot可以开始交易]
```

## API 端点

### 认证相关

- `POST /api/v1/auth/metamask` - MetaMask身份验证
- `GET /api/v1/bots/unclaimed` - 获取未认领的Bot
- `POST /api/v1/bots/{bot_id}/claim` - 认领Bot
- `POST /api/v1/bots/{bot_id}/configure` - 配置Bot

### 策略管理

- `POST /api/v1/strategies` - 创建策略
- `GET /api/v1/strategies/owner/{owner_id}` - 获取用户的策略

## 数据库结构

### BotOwner 表
```sql
CREATE TABLE bot_owners (
    id UUID PRIMARY KEY,
    owner_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    wallet_address VARCHAR(100) UNIQUE NOT NULL,
    subscription_tier VARCHAR(20) DEFAULT 'basic',
    max_bots_allowed INTEGER DEFAULT 5,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### TradingStrategy 表
```sql
CREATE TABLE trading_strategies (
    id UUID PRIMARY KEY,
    owner_id UUID REFERENCES bot_owners(id),
    strategy_name VARCHAR(100) NOT NULL,
    strategy_type VARCHAR(30) NOT NULL,
    risk_level VARCHAR(20) NOT NULL,
    max_position_size DECIMAL(5,2) NOT NULL,
    stop_loss_percentage DECIMAL(5,2) NOT NULL,
    take_profit_percentage DECIMAL(5,2) NOT NULL,
    buy_strategy_description TEXT,
    sell_strategy_description TEXT,
    filter_strategy_description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### TradingBot 表（更新）
```sql
ALTER TABLE trading_bots ADD COLUMN owner_id UUID REFERENCES bot_owners(id);
ALTER TABLE trading_bots ADD COLUMN is_configured BOOLEAN DEFAULT FALSE;
```

## 安全特性

### 1. 钱包验证
- 验证MetaMask钱包地址的有效性
- 使用签名验证用户身份
- 防止地址伪造和重放攻击

### 2. 权限控制
- 只有Bot所有者可以配置Bot
- 策略只能被创建者使用
- 防止未授权访问

### 3. 数据验证
- 输入参数验证
- 策略参数范围检查
- 防止恶意数据注入

## 错误处理

### 常见错误

1. **MetaMask未安装**
   ```
   MetaMask is not installed. Please install MetaMask to continue.
   ```

2. **用户拒绝连接**
   ```
   User rejected the connection request.
   ```

3. **Bot已被认领**
   ```
   Bot is already claimed by another user.
   ```

4. **策略创建失败**
   ```
   Failed to create strategy: Invalid parameters
   ```

### 调试技巧

1. 检查MetaMask连接状态
2. 验证钱包地址格式
3. 确认网络连接正常
4. 查看浏览器控制台错误

## 最佳实践

### 1. 用户体验

- 提供清晰的操作指引
- 显示操作进度和状态
- 友好的错误提示信息
- 响应式设计适配移动端

### 2. 安全性

- 定期更新依赖包
- 实施速率限制
- 记录安全事件日志
- 定期安全审计

### 3. 性能优化

- 使用缓存减少数据库查询
- 异步处理耗时操作
- 压缩静态资源
- 实施CDN加速

## 部署说明

### 1. 环境要求

- Node.js 16+
- MetaMask浏览器扩展
- 支持Web3的现代浏览器

### 2. 配置项

```env
# MetaMask配置
METAMASK_NETWORK_ID=1  # 主网
METAMASK_CHAIN_ID=0x1  # 十六进制链ID

# 安全配置
JWT_SECRET=your-jwt-secret
SESSION_SECRET=your-session-secret

# 数据库配置
DATABASE_URL=postgresql://user:pass@localhost/db
```

### 3. 启动命令

```bash
# 安装依赖
pip install -r requirements.txt

# 初始化数据库
python reset_trading_bot_tables.py

# 启动服务
python main.py --port 8000
```

## 总结

MetaMask登录和Bot管理系统提供了：

- **安全的身份验证**：基于MetaMask钱包的可靠身份验证
- **灵活的Bot管理**：支持Bot认领和配置
- **强大的策略系统**：用户可以创建和管理自定义策略
- **用户友好的界面**：直观的操作界面和清晰的状态反馈
- **完整的错误处理**：全面的错误处理和用户提示

这个系统为AIP DEX交易机器人提供了完整的用户管理和配置功能，让用户可以轻松地管理自己的交易机器人和策略。 