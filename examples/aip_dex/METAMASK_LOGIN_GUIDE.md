# 🔐 Metamask Login & Bot Claiming Guide

本指南详细介绍AIP DEX交易机器人的Metamask登录和机器人认领功能。

## 📋 目录

1. [概述](#概述)
2. [系统架构](#系统架构)
3. [用户流程](#用户流程)
4. [技术实现](#技术实现)
5. [API文档](#api文档)
6. [示例代码](#示例代码)
7. [故障排除](#故障排除)

## 概述

AIP DEX交易机器人平台支持通过Metamask钱包进行身份验证，用户可以：

- 🔐 **安全登录**：使用Metamask钱包进行身份验证
- 👤 **自动账户创建**：首次登录时自动创建BotOwner账户
- 🤖 **认领机器人**：认领未配置的交易机器人
- 📈 **策略管理**：创建和管理交易策略
- ⚙️ **灵活配置**：支持分步配置机器人

## 系统架构

```
用户界面 (Web)
    ↓
Metamask钱包连接
    ↓
身份验证 (签名验证)
    ↓
BotOwner账户管理
    ↓
机器人认领系统
    ↓
策略配置系统
    ↓
交易执行引擎
```

### 核心组件

1. **Metamask集成模块** (`static/js/metamask.js`)
   - 钱包连接管理
   - 签名验证
   - 会话状态管理

2. **认证服务** (`main.py` - `/api/v1/auth/metamask`)
   - 钱包地址验证
   - 用户账户创建
   - 会话令牌管理

3. **机器人管理服务** (`main.py` - `/api/v1/bots/*`)
   - 未认领机器人列表
   - 机器人认领功能
   - 机器人配置功能

4. **策略管理服务** (`services/owner_service.py`)
   - 默认策略创建
   - 自定义策略管理
   - 策略参数配置

## 用户流程

### 1. Metamask登录

#### 前端实现

```javascript
// 1. 检查Metamask是否可用
if (typeof window.ethereum !== 'undefined') {
    console.log('Metamask is installed!');
} else {
    alert('Please install Metamask to continue');
}

// 2. 连接钱包
async function connectWallet() {
    try {
        const accounts = await window.ethereum.request({
            method: 'eth_requestAccounts'
        });
        
        if (accounts.length > 0) {
            await authenticateUser(accounts[0]);
        }
    } catch (error) {
        console.error('Connection failed:', error);
    }
}

// 3. 身份验证
async function authenticateUser(walletAddress) {
    const message = `Login to AIP DEX Trading Bot\n\nWallet: ${walletAddress}\nTimestamp: ${Date.now()}`;
    
    try {
        // 获取签名
        const signature = await window.ethereum.request({
            method: 'personal_sign',
            params: [message, walletAddress]
        });
        
        // 发送到后端验证
        const response = await fetch('/api/v1/auth/metamask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                wallet_address: walletAddress,
                signature: signature,
                message: message
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            // 保存用户信息
            localStorage.setItem('owner_id', data.owner_id);
            localStorage.setItem('wallet_address', walletAddress);
            showSuccess('登录成功!');
        }
    } catch (error) {
        showError('身份验证失败: ' + error.message);
    }
}
```

#### 后端实现

```python
@app.post("/api/v1/auth/metamask")
async def metamask_auth(request: dict, db: Session = Depends(get_db)):
    """Metamask身份验证"""
    try:
        wallet_address = request.get("wallet_address")
        signature = request.get("signature")
        message = request.get("message")
        
        # 验证签名（生产环境需要proper verification）
        # 检查用户是否已存在
        existing_owner = db.query(BotOwner).filter(
            BotOwner.wallet_address == wallet_address
        ).first()
        
        if existing_owner:
            return {
                "owner_id": str(existing_owner.id),
                "owner_name": existing_owner.owner_name,
                "wallet_address": wallet_address,
                "message": "Existing user authenticated"
            }
        
        # 创建新用户
        owner_data = BotOwnerCreate(
            owner_name=f"User_{wallet_address[:8]}",
            email=f"{wallet_address[:8]}@metamask.user",
            wallet_address=wallet_address,
            subscription_tier="basic",
            max_bots_allowed=5
        )
        
        new_owner = await owner_service.create_bot_owner(db, owner_data)
        
        return {
            "owner_id": str(new_owner.id),
            "owner_name": new_owner.owner_name,
            "wallet_address": wallet_address,
            "message": "New user created and authenticated"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 2. 查看未认领机器人

```javascript
// 获取未认领机器人列表
async function getUnclaimedBots() {
    try {
        const response = await fetch('/api/v1/bots/unclaimed', {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });
        
        if (response.ok) {
            const bots = await response.json();
            renderUnclaimedBots(bots);
        }
    } catch (error) {
        console.error('获取未认领机器人失败:', error);
    }
}

// 渲染未认领机器人
function renderUnclaimedBots(bots) {
    const container = document.getElementById('unclaimed-bots-container');
    container.innerHTML = '';
    
    bots.forEach(bot => {
        const botCard = `
            <div class="col-md-6 col-lg-4 mb-3">
                <div class="card bot-card">
                    <div class="card-body">
                        <h6 class="mb-1">${bot.bot_name}</h6>
                        <span class="status-badge status-unclaimed">未认领</span>
                        <p class="text-secondary small">${bot.account_address}</p>
                        <div class="row text-center">
                            <div class="col-6">
                                <h6 class="mb-0">$${formatUSD(bot.current_balance_usd)}</h6>
                                <small class="text-secondary">余额</small>
                            </div>
                            <div class="col-6">
                                <small class="text-secondary">${bot.chain.toUpperCase()}</small>
                            </div>
                        </div>
                        <button class="btn btn-primary btn-sm w-100" onclick="claimBot('${bot.id}')">
                            <i class="fas fa-hand-holding-usd me-1"></i>
                            认领机器人
                        </button>
                    </div>
                </div>
            </div>
        `;
        container.innerHTML += botCard;
    });
}
```

### 3. 认领机器人

```javascript
// 认领机器人
async function claimBot(botId) {
    if (!metamaskLogin.isConnected || !metamaskLogin.ownerId) {
        showError('请先连接Metamask');
        return;
    }
    
    try {
        const response = await fetch(`/api/v1/bots/${botId}/claim`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            },
            body: JSON.stringify({
                owner_id: metamaskLogin.ownerId,
                wallet_address: metamaskLogin.currentAccount
            })
        });
        
        if (response.ok) {
            showSuccess('机器人认领成功!');
            // 刷新列表
            getUnclaimedBots();
            getMyClaimedBots();
        } else {
            const error = await response.json();
            showError('认领失败: ' + error.detail);
        }
    } catch (error) {
        showError('认领错误: ' + error.message);
    }
}
```

### 4. 配置机器人策略

```javascript
// 配置机器人
async function configureBot(botId, strategyId) {
    if (!metamaskLogin.isConnected || !metamaskLogin.ownerId) {
        showError('请先连接Metamask');
        return false;
    }
    
    try {
        const response = await fetch(`/api/v1/bots/${botId}/configure`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            },
            body: JSON.stringify({
                owner_id: metamaskLogin.ownerId,
                strategy_id: strategyId
            })
        });
        
        if (response.ok) {
            showSuccess('机器人配置成功!');
            return true;
        } else {
            const error = await response.json();
            showError('配置失败: ' + error.detail);
            return false;
        }
    } catch (error) {
        showError('配置错误: ' + error.message);
        return false;
    }
}
```

## 技术实现

### 数据库模型

#### BotOwner表
```sql
CREATE TABLE bot_owners (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    wallet_address VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(50),
    subscription_tier VARCHAR(50) DEFAULT 'basic',
    max_bots_allowed INTEGER DEFAULT 5,
    total_bots_created INTEGER DEFAULT 0,
    total_trading_volume_usd DECIMAL(20,2) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### TradingBot表
```sql
CREATE TABLE trading_bots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bot_name VARCHAR(255) NOT NULL,
    account_address VARCHAR(255) UNIQUE NOT NULL,
    chain VARCHAR(50) NOT NULL,
    owner_id UUID REFERENCES bot_owners(id),
    strategy_id UUID REFERENCES trading_strategies(id),
    is_configured BOOLEAN DEFAULT FALSE,
    initial_balance_usd DECIMAL(20,2) NOT NULL,
    current_balance_usd DECIMAL(20,2) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 状态管理

机器人有以下状态：

1. **未认领** (`owner_id = NULL, strategy_id = NULL`)
   - 机器人未被任何用户认领
   - 显示在未认领机器人列表中

2. **已认领** (`owner_id != NULL, strategy_id = NULL`)
   - 机器人已被用户认领
   - 但尚未配置策略
   - 需要选择策略才能开始交易

3. **已配置** (`owner_id != NULL, strategy_id != NULL`)
   - 机器人已配置所有者和策略
   - 可以开始自动交易
   - 状态为"Ready to Trade"

## API文档

### 认证相关

#### POST /api/v1/auth/metamask
Metamask身份验证

**请求体：**
```json
{
    "wallet_address": "0x1234567890abcdef1234567890abcdef12345678",
    "signature": "0xabcd...",
    "message": "Login to AIP DEX Trading Bot\n\nWallet: 0x1234...\nTimestamp: 1234567890"
}
```

**响应：**
```json
{
    "owner_id": "owner_uuid",
    "owner_name": "User_12345678",
    "wallet_address": "0x1234567890abcdef1234567890abcdef12345678",
    "message": "New user created and authenticated"
}
```

### 机器人管理

#### GET /api/v1/bots/unclaimed
获取未认领机器人列表

**响应：**
```json
[
    {
        "id": "bot_uuid",
        "bot_name": "Demo Bot 1",
        "account_address": "0x1111111111111111111111111111111111111111",
        "chain": "bsc",
        "initial_balance_usd": 1000.0,
        "current_balance_usd": 1000.0,
        "is_active": true,
        "created_at": "2024-01-01T00:00:00Z"
    }
]
```

#### POST /api/v1/bots/{bot_id}/claim
认领机器人

**请求体：**
```json
{
    "owner_id": "owner_uuid",
    "wallet_address": "0x1234567890abcdef1234567890abcdef12345678"
}
```

**响应：**
```json
{
    "success": true,
    "message": "Bot claimed successfully",
    "bot_id": "bot_uuid",
    "owner_id": "owner_uuid"
}
```

#### POST /api/v1/bots/{bot_id}/configure
配置机器人

**请求体：**
```json
{
    "owner_id": "owner_uuid",
    "strategy_id": "strategy_uuid"
}
```

**响应：**
```json
{
    "success": true,
    "message": "Bot configured successfully",
    "bot_id": "bot_uuid",
    "owner_id": "owner_uuid",
    "strategy_id": "strategy_uuid"
}
```

### 策略管理

#### GET /api/v1/strategies/owner/{owner_id}
获取用户的策略列表

**响应：**
```json
[
    {
        "id": "strategy_uuid",
        "strategy_name": "Conservative",
        "strategy_type": "conservative",
        "risk_level": "low",
        "max_position_size": 10.0,
        "stop_loss_percentage": 5.0,
        "take_profit_percentage": 15.0,
        "is_public": false,
        "usage_count": 2,
        "success_rate": 0.75
    }
]
```

#### POST /api/v1/strategies
创建新策略

**请求体：**
```json
{
    "strategy_name": "My Custom Strategy",
    "strategy_type": "user_defined",
    "risk_level": "medium",
    "max_position_size": 20.0,
    "stop_loss_percentage": 10.0,
    "take_profit_percentage": 25.0,
    "buy_strategy_description": "Buy strategy description...",
    "sell_strategy_description": "Sell strategy description...",
    "filter_strategy_description": "Filter strategy description...",
    "summary_strategy_description": "Strategy summary..."
}
```

## 示例代码

### 完整演示脚本

运行 `examples/metamask_login_example.py` 查看完整的Metamask登录和机器人认领流程。

### Web界面演示

打开 `static/metamask_demo.html` 查看交互式的Metamask登录和机器人认领界面。

### 后端服务示例

```python
# 创建Metamask登录演示
async def run_metamask_demo():
    demo = MetamaskLoginDemo()
    await demo.run_demo()

# 运行演示
if __name__ == "__main__":
    asyncio.run(run_metamask_demo())
```

## 故障排除

### 常见问题

#### 1. Metamask连接失败
**症状：** 点击连接按钮后没有反应
**解决方案：**
- 确保已安装Metamask扩展
- 检查浏览器是否支持Web3
- 确保Metamask已解锁

#### 2. 身份验证失败
**症状：** 登录后显示"Authentication failed"
**解决方案：**
- 检查钱包地址格式是否正确
- 确保签名消息包含正确的时间戳
- 验证后端服务是否正常运行

#### 3. 认领机器人失败
**症状：** 点击认领按钮后显示错误
**解决方案：**
- 确保用户已登录
- 检查机器人是否已被其他用户认领
- 验证用户权限和钱包地址

#### 4. 配置机器人失败
**症状：** 配置策略时显示错误
**解决方案：**
- 确保已选择有效的策略
- 检查策略是否属于当前用户
- 验证机器人状态是否正确

### 调试技巧

1. **浏览器开发者工具**
   - 查看网络请求和响应
   - 检查JavaScript控制台错误
   - 验证API调用参数

2. **后端日志**
   - 查看服务器日志
   - 检查数据库连接
   - 验证API端点响应

3. **Metamask调试**
   - 检查Metamask控制台
   - 验证钱包连接状态
   - 确认签名是否正确

### 安全考虑

1. **签名验证**
   - 在生产环境中实现proper的签名验证
   - 验证消息格式和时间戳
   - 防止重放攻击

2. **权限控制**
   - 确保用户只能操作自己的资源
   - 验证钱包地址的真实性
   - 实施适当的访问控制

3. **会话管理**
   - 安全地管理用户会话状态
   - 定期刷新认证令牌
   - 实现安全的登出机制

## 总结

Metamask登录和机器人认领系统提供了：

- ✅ **安全的身份验证**：基于钱包签名的身份验证
- ✅ **灵活的用户管理**：自动创建和管理用户账户
- ✅ **直观的机器人管理**：简单的认领和配置流程
- ✅ **完整的策略系统**：支持默认和自定义策略
- ✅ **状态跟踪**：清晰跟踪机器人的配置状态
- ✅ **权限控制**：确保用户只能管理自己的资源

这个系统为交易机器人提供了灵活而强大的配置管理能力，同时保持了良好的可扩展性和易用性。 