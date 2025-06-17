# 精简版 TokenService 说明文档

## 概述

根据您的要求，我们已经将 TokenService 精简为三个核心方法，去除了冗余和复杂的功能，保持简洁高效的设计。

## 三个核心方法

### 1. `get_or_create_token()`

**功能**: 获取已存在的 token 或创建新的 token

**参数**:
- `db`: 数据库会话
- `symbol`: Token 符号 (必需)
- `contract_address`: 合约地址 (可选)
- `chain`: 区块链名称 (可选，默认 'bsc')
- `name`: Token 名称 (可选)
- `decimals`: 精度 (可选，默认 18)
- `image_url`: 图片 URL (可选)

**返回**: `Token` 对象或 `None`

**特点**:
- 智能查找现有 token
- 自动从外部数据源解析缺失信息
- 支持多种参数组合

### 2. `update_token_pools()`

**功能**: 更新 token pools、pool metrics 和 signals

**参数**:
- `db`: 数据库会话
- `token_id`: Token ID (必需)
- `force_update`: 是否强制更新 (可选，默认 False)

**返回**: 包含更新状态的字典

**执行流程**:
1. 从 DexScreener 获取池数据
2. 创建或更新池信息
3. 更新池指标
4. 计算聚合的 token metrics
5. 计算交易信号

### 3. `update_token()`

**功能**: 更新 token metrics 和 signals（不更新池）

**参数**:
- `db`: 数据库会话
- `token_id`: Token ID (必需)
- `force_update`: 是否强制更新 (可选，默认 False)

**返回**: 包含更新状态的字典

**执行流程**:
1. 从现有池数据计算 token metrics
2. 计算交易信号
3. 返回更新结果

## 使用示例

```python
import asyncio
from models.database import get_db
from services.token_service import TokenService

async def example_usage():
    token_service = TokenService()
    db = next(get_db())
    
    try:
        # 1. 获取或创建 token
        token = await token_service.get_or_create_token(
            db=db,
            symbol="BNB",
            contract_address="0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
            chain="bsc",
            name="BNB"
        )
        
        if token:
            # 2. 更新池和指标
            pools_result = await token_service.update_token_pools(
                db=db,
                token_id=str(token.id),
                force_update=True
            )
            
            # 3. 只更新 metrics 和 signals
            token_result = await token_service.update_token(
                db=db,
                token_id=str(token.id),
                force_update=False
            )
            
    finally:
        await token_service.close()
        db.close()

# 运行示例
asyncio.run(example_usage())
```

## 与原版本的主要区别

### 简化前 (原版本)
- 20+ 个方法
- 复杂的嵌套调用
- 多种数据源混合
- API 功能和核心逻辑混合
- 1200+ 行代码

### 简化后 (新版本)
- 3 个核心方法 + 辅助方法
- 清晰的职责分离
- 统一的数据处理流程
- 核心逻辑专注
- ~400 行代码

## 调度器集成

`scheduler.py` 已经更新为使用精简的 TokenService：

```python
# 获取或创建 tokens
token = await self.token_service.get_or_create_token(...)

# 更新 pools 和 metrics
result = await self.token_service.update_token_pools(...)

# 更新 signals
result = await self.token_service.update_token(...)
```

## 性能优化

1. **频率控制**: 避免 30 分钟内重复更新
2. **批量处理**: 支持批量 token 处理
3. **错误处理**: 完善的异常处理机制
4. **资源管理**: 自动连接管理和清理

## 测试

运行测试脚本：

```bash
cd examples/aip_dex
python test_simplified_service.py
```

## 注意事项

1. 新版本保持与数据库模型的完全兼容
2. 所有外部 API 调用都有错误处理
3. 支持多链（BSC、Solana等）
4. 自动处理默认报价代币 (USDT/USDC)
5. 包含完整的中文注释和文档 