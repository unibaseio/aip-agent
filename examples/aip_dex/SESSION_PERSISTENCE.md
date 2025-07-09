# Session Persistence Implementation

## 概述

本文档说明如何实现MetaMask登录状态的持久化，避免用户每次刷新页面或切换页面都需要重新签名。

## 问题描述

### 原始问题
- 用户每次刷新页面都需要重新连接MetaMask
- 用户每次切换页面都需要重新签名
- 用户体验不佳，操作繁琐

### 解决方案
实现基于localStorage的会话持久化机制，包括：
- 24小时会话有效期
- 自动会话恢复
- 会话状态显示
- 手动会话刷新

## 实现细节

### 1. 会话数据结构

```javascript
// 存储的会话数据
{
    'owner_id': '用户ID',
    'wallet_address': '钱包地址',
    'session_expiry': '会话过期时间戳'
}
```

### 2. 会话验证逻辑

```javascript
async tryRestoreSession() {
    const savedOwnerId = localStorage.getItem('owner_id');
    const savedWallet = localStorage.getItem('wallet_address');
    const sessionExpiry = localStorage.getItem('session_expiry');
    
    if (savedOwnerId && savedWallet) {
        // 检查会话是否仍然有效（24小时）
        const now = Date.now();
        const expiry = sessionExpiry ? parseInt(sessionExpiry) : 0;
        
        if (now < expiry) {
            // 会话有效，尝试静默重连
            try {
                const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
                if (accounts.length > 0 && accounts[0].toLowerCase() === savedWallet.toLowerCase()) {
                    // 相同钱包，恢复会话而不重新认证
                    this.currentAccount = accounts[0];
                    this.ownerId = savedOwnerId;
                    this.isConnected = true;
                    this.updateUI();
                    return true;
                }
            } catch (error) {
                console.log('静默重连失败，用户需要手动连接');
            }
        } else {
            // 会话过期，清除旧数据
            localStorage.removeItem('owner_id');
            localStorage.removeItem('wallet_address');
            localStorage.removeItem('session_expiry');
        }
    }
    return false;
}
```

### 3. 认证流程优化

```javascript
async authenticateUser() {
    if (!this.currentAccount) return;

    try {
        // 检查是否已有有效会话
        const savedOwnerId = localStorage.getItem('owner_id');
        const savedWallet = localStorage.getItem('wallet_address');
        const sessionExpiry = localStorage.getItem('session_expiry');
        
        if (savedOwnerId && savedWallet && sessionExpiry) {
            const now = Date.now();
            const expiry = parseInt(sessionExpiry);
            
            if (now < expiry && savedWallet.toLowerCase() === this.currentAccount.toLowerCase()) {
                // 有效会话存在，使用它而不重新签名
                this.ownerId = savedOwnerId;
                this.isConnected = true;
                this.updateUI();
                return;
            }
        }

        // 需要重新签名
        const message = `Login to AIP DEX Trading Bot\n\nWallet: ${this.currentAccount}\nTimestamp: ${Date.now()}`;
        const signature = await window.ethereum.request({
            method: 'personal_sign',
            params: [message, this.currentAccount]
        });

        // 发送认证请求
        const response = await fetch('/api/v1/auth/metamask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.getAuthToken()}`
            },
            body: JSON.stringify({
                wallet_address: this.currentAccount,
                signature: signature,
                message: message
            })
        });

        if (response.ok) {
            const data = await response.json();
            this.ownerId = data.owner_id;
            
            // 存储会话数据，24小时过期
            const expiry = Date.now() + (24 * 60 * 60 * 1000);
            localStorage.setItem('owner_id', this.ownerId);
            localStorage.setItem('wallet_address', this.currentAccount);
            localStorage.setItem('session_expiry', expiry.toString());
            
            this.showSuccess('Successfully authenticated with MetaMask');
        }
    } catch (error) {
        console.error('Authentication error:', error);
        this.showError('Authentication failed: ' + error.message);
    }
}
```

### 4. 会话状态显示

```javascript
function updateSessionStatus() {
    const sessionExpiry = localStorage.getItem('session_expiry');
    const sessionStatusElement = document.getElementById('session-status');
    
    if (sessionExpiry) {
        const now = Date.now();
        const expiry = parseInt(sessionExpiry);
        const timeLeft = expiry - now;
        
        if (timeLeft > 0) {
            const hoursLeft = Math.floor(timeLeft / (1000 * 60 * 60));
            const minutesLeft = Math.floor((timeLeft % (1000 * 60 * 60)) / (1000 * 60));
            
            if (hoursLeft > 0) {
                sessionStatusElement.textContent = `Active (${hoursLeft}h ${minutesLeft}m)`;
                sessionStatusElement.className = 'text-success';
            } else {
                sessionStatusElement.textContent = `Active (${minutesLeft}m)`;
                sessionStatusElement.className = 'text-warning';
            }
        } else {
            sessionStatusElement.textContent = 'Expired';
            sessionStatusElement.className = 'text-danger';
        }
    } else {
        sessionStatusElement.textContent = 'None';
        sessionStatusElement.className = 'text-muted';
    }
}
```

### 5. 会话刷新功能

```javascript
function refreshSession() {
    if (metamaskLogin && metamaskLogin.isConnected && metamaskLogin.currentAccount) {
        // 延长会话24小时
        const expiry = Date.now() + (24 * 60 * 60 * 1000);
        localStorage.setItem('session_expiry', expiry.toString());
        updateSessionStatus();
        showNotification('Session refreshed successfully', 'success');
    }
}
```

## 用户体验改进

### 1. 自动会话恢复
- 页面加载时自动检查有效会话
- 如果会话有效，自动恢复登录状态
- 无需用户重新签名

### 2. 会话状态显示
- 在用户信息区域显示会话状态
- 显示剩余时间（小时和分钟）
- 不同状态用不同颜色表示

### 3. 手动会话刷新
- 提供"Refresh Session"按钮
- 用户可以手动延长会话时间
- 避免会话意外过期

### 4. 自动重定向
- 如果用户已登录，访问登录页面时自动跳转到bot管理页面
- 减少不必要的页面跳转

## 安全考虑

### 1. 会话过期
- 默认24小时过期时间
- 过期后自动清除会话数据
- 强制用户重新认证

### 2. 钱包地址验证
- 确保会话中的钱包地址与当前连接的钱包地址匹配
- 防止会话被恶意使用

### 3. 数据清理
- 断开连接时清除所有会话数据
- 会话过期时自动清理
- 防止数据泄露

## 测试验证

### 1. 功能测试
```bash
# 运行会话持久化测试
python test_session_persistence.py
```

### 2. 手动测试步骤
1. 启动服务器：`python main.py`
2. 访问：`http://localhost:8000/login`
3. 连接MetaMask并签名一次
4. 刷新页面 - 应该保持登录状态
5. 导航到 `/bot-management` - 应该保持登录状态
6. 检查UI中的会话状态显示
7. 尝试手动刷新会话

### 3. 预期行为
- ✅ 首次连接需要签名
- ✅ 刷新页面后保持登录状态
- ✅ 切换页面后保持登录状态
- ✅ 显示会话剩余时间
- ✅ 24小时后会话过期
- ✅ 过期后需要重新签名

## 故障排除

### 常见问题

1. **会话不持久**
   - 检查localStorage是否被禁用
   - 检查浏览器隐私设置
   - 确认MetaMask连接状态

2. **会话状态显示错误**
   - 检查时间戳格式
   - 验证localStorage数据完整性
   - 检查JavaScript错误

3. **自动重定向不工作**
   - 检查会话验证逻辑
   - 确认钱包地址匹配
   - 验证页面加载时序

### 调试方法

```javascript
// 在浏览器控制台中检查会话状态
console.log('Session data:', {
    owner_id: localStorage.getItem('owner_id'),
    wallet_address: localStorage.getItem('wallet_address'),
    session_expiry: localStorage.getItem('session_expiry'),
    current_time: Date.now(),
    is_expired: Date.now() > parseInt(localStorage.getItem('session_expiry') || '0')
});
```

## 总结

通过实现会话持久化机制，我们显著改善了用户体验：

1. **减少重复操作**：用户只需签名一次，24小时内无需重复签名
2. **提高便利性**：页面刷新和导航不会中断用户操作
3. **增强安全性**：合理的过期机制和验证逻辑
4. **改善反馈**：清晰的会话状态显示和剩余时间

这个实现平衡了用户体验和安全性，为用户提供了更加流畅的MetaMask登录体验。 