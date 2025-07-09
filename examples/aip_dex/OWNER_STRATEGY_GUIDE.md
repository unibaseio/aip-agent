# AIP DEX Trading Bot - Owner & Strategy Management Guide

本指南介绍AIP DEX交易机器人的所有者管理和策略管理功能，包括Metamask登录和机器人认领功能。

## 概述

新的系统引入了以下核心概念：

1. **Metamask登录** - 用户通过钱包地址进行身份验证
2. **BotOwner（机器人所有者）** - 管理交易机器人的用户
3. **TradingStrategy（交易策略）** - 包含参数设置和策略描述的完整策略配置
4. **TradingBot（交易机器人）** - 关联所有者和策略的交易机器人实例
5. **Bot认领** - 用户认领未配置所有者和策略的机器人

## 用户流程概览

```
1. Metamask登录 → 2. 创建BotOwner账户 → 3. 查看未认领机器人 → 4. 认领机器人 → 5. 配置策略 → 6. 开始交易
```

## 核心概念

### Metamask登录系统

系统支持通过Metamask钱包进行身份验证：

- **钱包连接**：用户连接Metamask钱包
- **签名验证**：通过钱包签名验证用户身份
- **自动账户创建**：首次登录时自动创建BotOwner账户
- **会话管理**：维护用户登录状态

```javascript
// 前端Metamask连接示例
const metamaskLogin = new MetaMaskLogin();

// 连接钱包
await metamaskLogin.connectWallet();

// 身份验证
await metamaskLogin.authenticateUser();
```

### BotOwner（机器人所有者）

每个交易机器人必须属于一个所有者。所有者具有以下特性：

- **基本信息**：姓名、邮箱、钱包地址、电话
- **权限控制**：订阅等级、最大机器人数量限制
- **统计信息**：创建的机器人数量、交易量等
- **自动创建**：通过Metamask登录时自动创建

```python
# 通过Metamask登录自动创建所有者
owner_data = BotOwnerCreate(
    owner_name=f"User_{wallet_address[:8]}",  # 自动生成用户名
    email=f"{wallet_address[:8]}@metamask.user",  # 自动生成邮箱
    wallet_address=wallet_address,  # Metamask钱包地址
    subscription_tier="basic",  # 默认基础订阅
    max_bots_allowed=5  # 默认机器人数量限制
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

### Bot认领系统

系统支持用户认领未配置的机器人：

- **未认领机器人**：没有设置owner_id和strategy_id的机器人
- **认领过程**：用户认领机器人时同时设置owner和strategy
- **权限验证**：确保只有登录用户才能认领机器人
- **状态管理**：认领后机器人状态变为已配置

## 系统架构

```
Metamask Login (身份验证)
    ↓
BotOwner (所有者)
    ├── TradingStrategy (策略1)
    │   ├── TradingBot (已认领机器人1)
    │   └── TradingBot (已认领机器人2)
    ├── TradingStrategy (策略2)
    │   └── TradingBot (已认领机器人3)
    └── TradingStrategy (策略3)
        └── TradingBot (已认领机器人4)

Unclaimed Bots (未认领机器人池)
    ├── TradingBot (未配置机器人1)
    ├── TradingBot (未配置机器人2)
    └── TradingBot (未配置机器人3)
```

## 使用流程

### 1. Metamask登录

#### 前端登录流程

```javascript
// 1. 连接Metamask钱包
async function connectWallet() {
    if (typeof window.ethereum !== 'undefined') {
        try {
            const accounts = await window.ethereum.request({
                method: 'eth_requestAccounts'
            });
            
            if (accounts.length > 0) {
                await authenticateUser(accounts[0]);
            }
        } catch (error) {
            console.error('连接失败:', error);
        }
    }
}

// 2. 身份验证
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

#### 后端验证流程

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

#### 前端认领流程

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
            // 刷新未认领机器人列表
            getUnclaimedBots();
            // 刷新我的机器人列表
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

#### 后端认领处理

```python
@app.post("/api/v1/bots/{bot_id}/claim")
async def claim_bot(bot_id: str, request: dict, db: Session = Depends(get_db)):
    """认领未配置的机器人"""
    try:
        owner_id = request.get("owner_id")
        wallet_address = request.get("wallet_address")
        
        if not owner_id or not wallet_address:
            raise HTTPException(status_code=400, detail="Missing owner_id or wallet_address")
        
        # 获取机器人
        bot = db.query(TradingBot).filter(TradingBot.id == bot_id).first()
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        if bot.owner_id:
            raise HTTPException(status_code=400, detail="Bot is already claimed")
        
        # 验证所有者
        owner = db.query(BotOwner).filter(BotOwner.id == owner_id).first()
        if not owner:
            raise HTTPException(status_code=404, detail="Owner not found")
        
        if owner.wallet_address != wallet_address:
            raise HTTPException(status_code=403, detail="Wallet address mismatch")
        
        # 认领机器人（只设置owner，不设置strategy）
        bot.owner_id = owner_id
        bot.updated_at = datetime.now(timezone.utc)
        db.commit()
        
        return {
            "success": True,
            "message": "Bot claimed successfully",
            "bot_id": str(bot.id),
            "owner_id": str(owner_id)
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
```

### 4. 配置机器人策略

#### 创建策略

```javascript
// 创建新策略
async function createStrategy(strategyData) {
    if (!metamaskLogin.isConnected || !metamaskLogin.ownerId) {
        showError('请先连接Metamask');
        return null;
    }
    
    try {
        const response = await fetch('/api/v1/strategies', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            },
            body: JSON.stringify({
                ...strategyData,
                owner_id: metamaskLogin.ownerId
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            showSuccess('策略创建成功!');
            return data;
        } else {
            const error = await response.json();
            showError('创建策略失败: ' + error.detail);
            return null;
        }
    } catch (error) {
        showError('创建策略错误: ' + error.message);
        return null;
    }
}
```

#### 配置机器人

```javascript
// 配置机器人（设置strategy）
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
            const data = await response.json();
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

#### 后端配置处理

```python
@app.post("/api/v1/bots/{bot_id}/configure")
async def configure_bot(bot_id: str, request: dict, db: Session = Depends(get_db)):
    """配置机器人（设置owner和strategy）"""
    try:
        owner_id = request.get("owner_id")
        strategy_id = request.get("strategy_id")
        
        if not owner_id or not strategy_id:
            raise HTTPException(status_code=400, detail="Missing owner_id or strategy_id")
        
        # 使用trading service配置机器人
        configured_bot = await trading_service.configure_bot(db, bot_id, owner_id, strategy_id)
        
        if not configured_bot:
            raise HTTPException(status_code=500, detail="Failed to configure bot")
        
        return {
            "success": True,
            "message": "Bot configured successfully",
            "bot_id": str(bot_id),
            "owner_id": str(owner_id),
            "strategy_id": str(strategy_id)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
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

## 完整用户流程示例

### 步骤1：Metamask登录

1. 用户访问登录页面
2. 点击"Connect MetaMask"按钮
3. 在Metamask中确认连接
4. 系统自动创建BotOwner账户
5. 用户成功登录

### 步骤2：查看未认领机器人

1. 登录后进入机器人管理页面
2. 系统显示所有未认领的机器人
3. 用户可以查看每个机器人的详细信息
4. 包括机器人名称、钱包地址、当前余额、链类型等

### 步骤3：认领机器人

1. 用户选择要认领的机器人
2. 点击"认领机器人"按钮
3. 系统验证用户身份和权限
4. 机器人被分配给当前用户（设置owner_id）
5. 机器人状态变为"已认领但未配置"

### 步骤4：创建或选择策略

1. 用户可以选择使用默认策略
2. 或者创建自定义策略
3. 设置策略参数和描述
4. 保存策略

### 步骤5：配置机器人

1. 为已认领的机器人选择策略
2. 点击"配置机器人"按钮
3. 系统设置机器人的strategy_id
4. 机器人状态变为"已配置"
5. 机器人可以开始交易

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

## API端点

### 认证相关
- `POST /api/v1/auth/metamask` - Metamask身份验证

### 机器人管理
- `GET /api/v1/bots/unclaimed` - 获取未认领机器人列表
- `POST /api/v1/bots/{bot_id}/claim` - 认领机器人
- `POST /api/v1/bots/{bot_id}/configure` - 配置机器人

### 策略管理
- `GET /api/v1/strategies/owner/{owner_id}` - 获取用户策略列表
- `POST /api/v1/strategies` - 创建新策略
- `PUT /api/v1/strategies/{strategy_id}` - 更新策略

## 最佳实践

1. **Metamask集成**：
   - 确保用户安装了Metamask扩展
   - 处理钱包连接失败的情况
   - 验证签名以确保安全性

2. **机器人认领**：
   - 验证用户权限和钱包地址
   - 防止重复认领
   - 记录认领历史

3. **策略设计**：
   - 明确策略的风险等级和目标
   - 详细描述买入、卖出和筛选逻辑
   - 定期评估和优化策略

4. **风险管理**：
   - 设置合理的止损和止盈水平
   - 控制单币最大仓位比例
   - 监控策略表现

5. **策略管理**：
   - 为不同市场环境准备不同策略
   - 定期更新策略参数
   - 记录策略变更历史

6. **性能监控**：
   - 跟踪策略成功率
   - 监控平均收益率
   - 分析策略在不同市场条件下的表现

## 故障排除

### 常见问题

1. **Metamask连接失败**
   - 确保用户已安装Metamask扩展
   - 检查网络连接
   - 验证钱包是否已解锁

2. **身份验证失败**
   - 检查签名是否正确
   - 验证时间戳是否有效
   - 确认钱包地址格式

3. **认领机器人失败**
   - 确保机器人未被其他用户认领
   - 验证用户权限和钱包地址
   - 检查机器人是否存在

4. **策略配置失败**
   - 确保策略参数在有效范围内
   - 验证策略是否属于当前用户
   - 检查机器人状态

### 调试技巧

1. 使用浏览器开发者工具查看网络请求
2. 检查Metamask控制台日志
3. 验证API响应格式
4. 确认数据库连接和权限

## 安全考虑

1. **签名验证**：在生产环境中实现proper的签名验证
2. **权限控制**：确保用户只能操作自己的资源
3. **钱包验证**：验证钱包地址的真实性
4. **会话管理**：安全地管理用户会话状态

## 总结

完整的Metamask登录和机器人认领系统提供了：

- **无缝的用户体验**：通过Metamask快速登录
- **灵活的机器人管理**：支持认领和配置未使用的机器人
- **安全的身份验证**：基于钱包签名的身份验证
- **完整的策略管理**：创建、配置和更新交易策略
- **权限控制**：基于所有者的机器人数量限制
- **状态跟踪**：清晰跟踪机器人的配置状态

这个系统为交易机器人提供了灵活而强大的配置管理能力，同时保持了良好的可扩展性和易用性。

### 主要改进

1. **Metamask集成**：支持钱包登录和身份验证
2. **机器人认领**：用户可以认领未配置的机器人
3. **分步配置**：支持先认领后配置的灵活流程
4. **权限验证**：确保用户只能操作自己的资源
5. **状态管理**：清晰跟踪机器人的配置状态
6. **用户体验**：直观的Web界面和操作流程 