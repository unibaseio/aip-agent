# MetaMask Connection Testing Guide

## 概述

本文档说明如何测试和调试AIP DEX Trading Bot的MetaMask连接功能。

## 问题诊断

### 常见错误信息

1. **"MetaMask login not initialized. Please refresh the page."**
   - 原因：MetaMask JavaScript模块未正确加载或初始化
   - 解决方案：刷新页面，确保所有JavaScript文件正确加载

2. **"MetaMask is not installed"**
   - 原因：浏览器中未安装MetaMask扩展
   - 解决方案：安装MetaMask浏览器扩展

3. **"User rejected the connection request"**
   - 原因：用户在MetaMask弹窗中拒绝了连接请求
   - 解决方案：在MetaMask中允许网站连接

## 测试步骤

### 1. 基础连接测试

访问测试页面：`/static/metamask-test.html`

这个页面提供以下功能：
- 检查MetaMask是否可用
- 测试连接和断开连接
- 显示账户和网络信息
- 实时状态更新

### 2. 功能测试

#### 测试1：MetaMask可用性检查
```javascript
// 检查MetaMask是否安装
if (typeof window.ethereum !== 'undefined' && window.ethereum.isMetaMask) {
    console.log('MetaMask is available');
} else {
    console.log('MetaMask is not available');
}
```

#### 测试2：连接测试
```javascript
// 请求连接
const accounts = await window.ethereum.request({
    method: 'eth_requestAccounts'
});
console.log('Connected accounts:', accounts);
```

#### 测试3：网络检查
```javascript
// 获取当前网络
const chainId = await window.ethereum.request({ method: 'eth_chainId' });
console.log('Current chain ID:', chainId);
```

### 3. 调试工具

#### 浏览器控制台命令
```javascript
// 检查全局变量
console.log('metamaskLogin:', metamaskLogin);
console.log('window.ethereum:', window.ethereum);

// 检查连接状态
if (metamaskLogin) {
    console.log('Is connected:', metamaskLogin.isConnected);
    console.log('Current account:', metamaskLogin.currentAccount);
    console.log('Is MetaMask available:', metamaskLogin.isMetaMaskAvailable());
}
```

#### 网络请求监控
在浏览器开发者工具的Network标签页中监控：
- `/api/v1/auth/metamask` - 认证请求
- `/api/v1/bots/unclaimed` - 获取未认领机器人
- `/api/v1/strategies/owner/{owner_id}` - 获取用户策略

## 修复的问题

### 1. 重复变量声明
- 修复了`metamask.js`文件末尾的重复`metamaskManager`声明
- 移除了未定义的`MetaMaskManager`类引用

### 2. 初始化时序问题
- 添加了DOM加载完成后的延迟初始化
- 改进了MetaMask可用性检查

### 3. 错误处理改进
- 添加了更详细的错误信息
- 改进了连接状态检查
- 添加了网络切换支持

## 代码改进

### MetaMaskLogin类的新功能

```javascript
// 检查MetaMask是否可用
isMetaMaskAvailable() {
    return typeof window.ethereum !== 'undefined' && window.ethereum.isMetaMask;
}

// 获取当前网络
async getCurrentNetwork() {
    if (!this.isMetaMaskAvailable()) return null;
    
    try {
        const chainId = await window.ethereum.request({ method: 'eth_chainId' });
        return chainId;
    } catch (error) {
        console.error('Error getting network:', error);
        return null;
    }
}

// 切换网络
async switchNetwork(chainId) {
    if (!this.isMetaMaskAvailable()) return false;
    
    try {
        await window.ethereum.request({
            method: 'wallet_switchEthereumChain',
            params: [{ chainId: chainId }],
        });
        return true;
    } catch (error) {
        console.error('Error switching network:', error);
        return false;
    }
}
```

### 改进的初始化流程

```javascript
// 全局初始化
let metamaskLogin = null;

document.addEventListener('DOMContentLoaded', function() {
    if (typeof MetaMaskLogin !== 'undefined') {
        metamaskLogin = new MetaMaskLogin();
    }
});
```

## 故障排除

### 如果仍然出现初始化错误

1. **检查文件路径**
   ```bash
   # 确保metamask.js文件存在
   ls -la static/js/metamask.js
   ```

2. **检查浏览器控制台错误**
   - 打开浏览器开发者工具
   - 查看Console标签页的错误信息
   - 检查Network标签页的请求状态

3. **清除浏览器缓存**
   - 按Ctrl+Shift+R强制刷新
   - 清除浏览器缓存和Cookie

4. **检查MetaMask扩展**
   - 确保MetaMask扩展已启用
   - 检查MetaMask是否已解锁
   - 确认网络设置正确

### 开发环境调试

```javascript
// 在浏览器控制台中运行这些命令来调试
// 1. 检查MetaMask状态
console.log('Ethereum provider:', window.ethereum);
console.log('Is MetaMask:', window.ethereum?.isMetaMask);

// 2. 检查全局变量
console.log('metamaskLogin:', metamaskLogin);

// 3. 手动测试连接
if (window.ethereum) {
    window.ethereum.request({ method: 'eth_accounts' })
        .then(accounts => console.log('Accounts:', accounts))
        .catch(error => console.error('Error:', error));
}
```

## 支持的网络

当前支持的网络：
- Ethereum Mainnet (0x1)
- Polygon Mainnet (0x89)
- BSC Mainnet (0x38)
- Avalanche C-Chain (0xa86a)
- 各种测试网络

## 联系支持

如果问题仍然存在，请提供以下信息：
1. 浏览器类型和版本
2. MetaMask版本
3. 控制台错误信息
4. 网络请求状态
5. 测试页面显示的状态信息 