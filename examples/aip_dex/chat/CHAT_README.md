# AIP DEX Chat Interface

## 功能特性

这是一个现代化的聊天界面，专门为AIP DEX Token分析API设计，具有以下特性：

### 🎨 用户界面
- **现代化设计**: 采用渐变色背景和毛玻璃效果  
- **响应式布局**: 支持桌面和移动设备
- **动画效果**: 消息淡入动画和打字指示器
- **状态指示**: 实时显示API连接状态

### 💬 聊天功能
- **实时对话**: 与AIP DEX Token分析助手进行实时对话
- **多行输入**: 支持多行文本输入，自动调整高度
- **选项配置**: 可选择是否包含流动性池详细信息
- **错误处理**: 优雅的错误处理和显示

### 🔧 技术特性
- **原生JavaScript**: 无框架依赖，轻量级实现
- **异步通信**: 使用Fetch API进行异步HTTP请求
- **健康检查**: 自动检测API服务状态
- **CORS支持**: 支持跨域请求

## 使用方法

### 1. 启动API服务
确保AIP DEX API服务正在运行：
```bash
cd examples/aip_dex
python main.py
```

API服务将在 `http://localhost:8000` 启动

### 2. 打开聊天界面
在浏览器中打开 `chat.html` 文件：
```bash
# 方法1: 直接打开文件
open chat.html

# 方法2: 使用本地服务器（推荐）
python -m http.server 3000
# 然后访问 http://localhost:3000/chat.html
```

### 3. 开始对话
在聊天界面中输入问题，例如：
- "分析ETH的价格趋势"
- "比较不同DEX上的BTC价格"
- "寻找套利机会"
- "分析USDT的流动性"

### 4. 配置选项
- **包含流动性池详细信息**: 勾选此选项获取更详细的池级数据

## API接口说明

### Chat Endpoint
- **URL**: `POST /api/v1/chat`
- **请求格式**:
```json
{
    "message": "用户消息",
    "include_pools": false
}
```
- **响应格式**:
```json
{
    "response": "助手回复"
}
```

### Health Check
- **URL**: `GET /api/v1/health`
- **用途**: 检查API服务状态

## 自定义配置

### 修改API地址
如果API运行在不同的地址，请修改 `chat.html` 中的 `baseUrl`：
```javascript
this.baseUrl = 'http://your-api-host:port';
```

### 样式自定义
可以修改CSS变量来调整界面样式：
- 主色调: `#4f46e5`, `#7c3aed`
- 背景渐变: `#667eea`, `#764ba2`
- 消息颜色: `#f3f4f6`, `#374151`

## 故障排除

### 常见问题

1. **API连接失败**
   - 确保API服务正在运行
   - 检查CORS设置
   - 验证API地址配置

2. **消息发送失败**
   - 检查网络连接
   - 查看浏览器控制台错误信息
   - 确认API响应格式

3. **界面显示异常**
   - 清除浏览器缓存
   - 检查JavaScript是否启用
   - 确认浏览器兼容性

### 调试模式
打开浏览器开发者工具（F12）查看详细错误信息和网络请求。

## 兼容性

- **现代浏览器**: Chrome 80+, Firefox 75+, Safari 13+
- **移动设备**: iOS Safari, Android Chrome
- **API要求**: FastAPI服务运行在Python 3.8+

## 贡献

欢迎提交Issue和Pull Request来改进这个聊天界面！ 