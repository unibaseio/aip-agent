# AIP DEX Trading Bot - Bot Management System

本系统提供了完整的机器人管理功能，包括MetaMask登录、机器人认领和策略配置。

## 🚀 快速开始

### 1. 启动服务器

```bash
cd examples/aip_dex
python main.py
```

服务器将在 `http://localhost:8000` 启动。

### 2. 访问登录页面

打开浏览器访问：`http://localhost:8000/login`

### 3. 连接MetaMask

1. 确保已安装MetaMask浏览器扩展
2. 点击"Connect MetaMask"按钮
3. 在MetaMask中确认连接
4. 系统会自动创建用户账户

### 4. 管理机器人

登录后访问：`http://localhost:8000/bot-management`

## 🔧 功能特性

### MetaMask登录
- ✅ 钱包连接和身份验证
- ✅ 自动创建BotOwner账户
- ✅ 安全的签名验证
- ✅ 会话状态管理

### 机器人认领
- ✅ 查看未认领的机器人
- ✅ 一键认领机器人
- ✅ 权限验证和防重复认领
- ✅ 实时状态更新

### 策略管理
- ✅ 创建自定义交易策略
- ✅ 设置风险参数和交易规则
- ✅ 策略描述和筛选条件
- ✅ 策略使用统计

### 机器人配置
- ✅ 为认领的机器人配置策略
- ✅ 分步配置流程
- ✅ 配置状态跟踪
- ✅ 准备开始交易

## 📊 系统架构

```
用户登录 → 认领机器人 → 创建策略 → 配置机器人 → 开始交易
    ↓           ↓           ↓           ↓           ↓
MetaMask   未认领机器人   策略管理   配置管理   交易执行
身份验证   认领系统      参数设置   状态跟踪   监控系统
```

## 🎯 用户流程

### 1. 首次登录
```
1. 访问登录页面
2. 连接MetaMask钱包
3. 确认连接和签名
4. 系统自动创建账户
5. 跳转到机器人管理页面
```

### 2. 认领机器人
```
1. 查看未认领机器人列表
2. 选择要认领的机器人
3. 点击"Claim Bot"按钮
4. 验证钱包地址和权限
5. 机器人被分配给用户
```

### 3. 创建策略
```
1. 点击"Create Strategy"按钮
2. 填写策略基本信息
3. 设置交易参数
4. 编写策略描述
5. 保存策略
```

### 4. 配置机器人
```
1. 选择已认领的机器人
2. 点击"Configure Bot"按钮
3. 选择交易策略
4. 确认配置
5. 机器人准备开始交易
```

## 🔌 API端点

### 认证相关
- `POST /api/v1/auth/metamask` - MetaMask身份验证

### 机器人管理
- `GET /api/v1/bots/unclaimed` - 获取未认领机器人
- `POST /api/v1/bots/{bot_id}/claim` - 认领机器人
- `GET /api/v1/bots/owner/{owner_id}` - 获取用户机器人
- `POST /api/v1/bots/{bot_id}/configure` - 配置机器人

### 策略管理
- `POST /api/v1/strategies` - 创建策略
- `GET /api/v1/strategies/owner/{owner_id}` - 获取用户策略

## 🧪 测试功能

运行测试脚本来验证所有功能：

```bash
python test_bot_management.py
```

测试包括：
- ✅ API端点测试
- ✅ MetaMask登录模拟
- ✅ 机器人认领模拟
- ✅ 策略创建模拟
- ✅ 机器人配置模拟

## 📁 文件结构

```
examples/aip_dex/
├── main.py                    # 主服务器文件
├── static/
│   ├── login.html            # 登录页面
│   ├── bot-management.html   # 机器人管理页面
│   └── js/
│       └── metamask.js       # MetaMask集成
├── services/
│   ├── trading_service.py    # 交易服务
│   └── owner_service.py      # 所有者服务
├── models/
│   └── database.py           # 数据库模型
├── api/
│   └── schemas.py            # API数据模型
├── test_bot_management.py    # 测试脚本
└── BOT_MANAGEMENT_README.md  # 本文档
```

## 🎨 界面特性

### 现代化设计
- 🎨 响应式布局
- 🌙 深色/浅色主题支持
- 📱 移动设备友好
- ⚡ 流畅的动画效果

### 用户体验
- 🔔 实时通知系统
- 📊 数据可视化
- 🎯 直观的操作流程
- 📈 实时状态更新

### 交互功能
- 🔄 自动刷新数据
- ⚡ 快速操作按钮
- 📋 详细状态显示
- 🎛️ 参数配置界面

## 🔒 安全特性

### 身份验证
- 🔐 MetaMask钱包验证
- ✍️ 数字签名验证
- 🛡️ 会话管理
- 🔑 权限控制

### 数据安全
- 🛡️ API令牌验证
- 🔒 数据库访问控制
- 📝 操作日志记录
- 🚫 防重复操作

## 📈 监控和统计

### 机器人状态
- 📊 总机器人数量
- 🎯 已认领机器人
- ⚙️ 已配置机器人
- 📈 策略使用统计

### 用户统计
- 👤 活跃用户数量
- 🤖 用户机器人数量
- 📊 策略创建统计
- 💰 交易量统计

## 🚀 部署指南

### 本地开发
```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 设置环境变量
cp env.example .env
# 编辑 .env 文件

# 3. 启动服务器
python main.py

# 4. 访问应用
open http://localhost:8000
```

### 生产部署
```bash
# 1. 使用Docker
docker build -t aip-dex-bot .
docker run -p 8000:8000 aip-dex-bot

# 2. 使用Gunicorn
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## 🔧 配置选项

### 环境变量
```bash
# 数据库配置
DATABASE_URL=postgresql://user:pass@localhost/dbname

# API配置
API_TOKEN=aip-dex-default-token-2025

# 服务器配置
HOST=0.0.0.0
PORT=8000
```

### 机器人配置
```json
{
  "bot_name": "My Trading Bot",
  "account_address": "0x...",
  "chain": "bsc",
  "initial_balance_usd": 1000.0,
  "is_active": true
}
```

## 📚 开发指南

### 添加新功能
1. 在 `main.py` 中添加API端点
2. 在 `static/` 中添加前端页面
3. 在 `services/` 中添加业务逻辑
4. 在 `models/` 中添加数据模型
5. 更新测试脚本

### 自定义样式
- 修改 `static/` 中的CSS文件
- 使用Bootstrap 5组件
- 添加自定义动画效果
- 支持主题切换

### 扩展功能
- 添加更多策略类型
- 实现机器人监控面板
- 添加交易历史记录
- 实现收益分析功能

## 🐛 故障排除

### 常见问题

1. **MetaMask连接失败**
   - 确保已安装MetaMask扩展
   - 检查网络连接
   - 验证钱包是否已解锁

2. **API请求失败**
   - 检查服务器是否运行
   - 验证API令牌
   - 查看服务器日志

3. **数据库错误**
   - 检查数据库连接
   - 验证表结构
   - 查看错误日志

### 调试技巧
- 使用浏览器开发者工具
- 查看服务器控制台输出
- 检查网络请求状态
- 验证数据库查询

## 📞 支持

### 文档
- 📖 [完整API文档](http://localhost:8000/docs)
- 📋 [数据模型说明](DATA_STRUCTURE_DESIGN.md)
- 🎯 [用户指南](OWNER_STRATEGY_GUIDE.md)

### 测试
- 🧪 运行测试脚本
- 📊 检查API响应
- 🔍 验证数据完整性

### 反馈
- 🐛 报告问题
- 💡 提出建议
- 📈 功能请求

## 🎉 总结

AIP DEX Trading Bot管理系统提供了：

- ✅ **完整的用户认证系统** - MetaMask集成
- ✅ **灵活的机器人管理** - 认领和配置功能
- ✅ **强大的策略系统** - 自定义交易策略
- ✅ **现代化的用户界面** - 响应式设计
- ✅ **安全的API系统** - 权限控制和验证
- ✅ **完整的测试覆盖** - 功能验证和测试

这个系统为交易机器人提供了灵活而强大的配置管理能力，同时保持了良好的可扩展性和易用性。 