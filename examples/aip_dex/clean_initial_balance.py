from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
from models.database import init_database

def clean_trading_bots():
    # 加载环境变量
    load_dotenv()
    
    # 获取数据库连接URL
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        raise ValueError("未设置DATABASE_URL环境变量")

    print("正在确保数据库表已创建...")
    if not init_database():
        raise Exception("初始化数据库表失败")

    # 创建数据库引擎
    engine = create_engine(DATABASE_URL)

    try:
        # 连接数据库
        with engine.connect() as connection:
            # 首先获取符合条件的trading_bots记录数量
            count_query = text("""
                SELECT COUNT(*) 
                FROM trading_bots 
                WHERE initial_balance_usd = 1000
            """)
            result = connection.execute(count_query)
            count = result.scalar()
            
            print(f"找到 {count} 个initial_balance_usd为1000的trading_bots记录")

            if count > 0:
                # 删除符合条件的记录
                delete_query = text("""
                    DELETE FROM trading_bots 
                    WHERE initial_balance_usd = 1000
                """)
                result = connection.execute(delete_query)
                connection.commit()
                print(f"已成功删除 {result.rowcount} 条记录")
            else:
                print("没有找到需要清理的记录")

    except Exception as e:
        print(f"清理过程中发生错误: {str(e)}")
        raise

if __name__ == "__main__":
    print("开始清理initial_balance_usd为1000的trading_bot记录...")
    clean_trading_bots()
    print("清理完成")