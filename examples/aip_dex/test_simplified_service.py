#!/usr/bin/env python3
"""
测试精简版 TokenService 的示例脚本
"""

import asyncio
import logging
from models.database import get_db, create_tables, create_indexes
from services.token_service import TokenService

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_simplified_token_service():
    """测试精简版 TokenService 的三个核心方法"""
    
    # 初始化数据库
    try:
        create_tables()
        create_indexes()
        logger.info("数据库初始化成功")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        return
    
    # 创建 TokenService 实例
    token_service = TokenService()
    
    try:
        # 获取数据库会话
        db_gen = get_db()
        db = next(db_gen)
        
        # 测试 1: get_or_create_token
        logger.info("测试 1: get_or_create_token")
        token = await token_service.get_or_create_token(
            db=db,
            symbol="BNB",
            contract_address="0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
            chain="bsc",
            name="BNB"
        )
        
        if token:
            logger.info(f"成功创建/获取 token: {token.symbol} (ID: {token.id})")
            
            # 测试 2: update_token_pools
            logger.info("测试 2: update_token_pools")
            pools_result = await token_service.update_token_pools(
                db=db,
                token_id=str(token.id),
                force_update=True
            )
            
            logger.info(f"更新池结果: {pools_result}")
            
            # 测试 3: update_token
            logger.info("测试 3: update_token")
            token_result = await token_service.update_token(
                db=db,
                token_id=str(token.id),
                force_update=True
            )
            
            logger.info(f"更新 token 结果: {token_result}")
            
        else:
            logger.error("无法创建/获取 token")
            
        db.close()
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
    finally:
        # 关闭连接
        await token_service.close()

async def main():
    """主函数"""
    await test_simplified_token_service()

if __name__ == "__main__":
    asyncio.run(main()) 