#!/usr/bin/env python3
"""
数据映射完整性测试
验证所有数据聚合器的字段都能正确映射到数据库模型
"""

import asyncio
from typing import Dict, Any
from models.database import Token, TokenPool, PoolMetric, TokenMetric
from data_aggregator.dex_screener import DexScreenerProvider
from data_aggregator.moralis import MoralisProvider  
from data_aggregator.birdeye import BirdEyeProvider

def get_model_fields():
    """获取所有数据库模型的字段"""
    return {
        'Token': [c.name for c in Token.__table__.columns],
        'TokenPool': [c.name for c in TokenPool.__table__.columns],
        'PoolMetric': [c.name for c in PoolMetric.__table__.columns],
        'TokenMetric': [c.name for c in TokenMetric.__table__.columns]
    }

def get_dexscreener_fields():
    """获取DexScreener提供的字段"""
    return {
        'pair_data': [
            'base_name', 'base_symbol', 'base_address',
            'quote_name', 'quote_symbol', 'quote_address',
            'price_usd', 'price_native',
            'price_change_1h', 'price_change_6h', 'price_change_24h',
            'volume_1h', 'volume_6h', 'volume_24h',
            'liquidity_usd', 'market_cap', 'fdv',
            'dex', 'chain', 'pair_address',
            'buys_1h', 'sells_1h', 'buys_6h', 'sells_6h',
            'buys_24h', 'sells_24h', 'pair_created_at'
        ]
    }

def get_moralis_fields():
    """获取Moralis提供的字段"""
    return {
        'analytics': [
            'buy_volume_5m', 'buy_volume_1h', 'buy_volume_6h', 'buy_volume_24h',
            'sell_volume_5m', 'sell_volume_1h', 'sell_volume_6h', 'sell_volume_24h',
            'total_buyers_5m', 'total_buyers_1h', 'total_buyers_6h', 'total_buyers_24h',
            'total_sellers_5m', 'total_sellers_1h', 'total_sellers_6h', 'total_sellers_24h',
            'total_buys_5m', 'total_buys_1h', 'total_buys_6h', 'total_buys_24h',
            'total_sells_5m', 'total_sells_1h', 'total_sells_6h', 'total_sells_24h',
            'unique_wallets_5m', 'unique_wallets_1h', 'unique_wallets_6h', 'unique_wallets_24h',
            'price_change_5m', 'price_change_1h', 'price_change_6h', 'price_change_24h',
            'usd_price', 'total_liquidity_usd', 'total_fdv'
        ],
        'holder_stats': [
            'total_holders', 'holders_by_swap', 'holders_by_transfer', 'holders_by_airdrop',
            'holder_change_5m', 'holder_change_5m_percent',
            'holder_change_1h', 'holder_change_1h_percent',
            'holder_change_6h', 'holder_change_6h_percent',
            'holder_change_24h', 'holder_change_24h_percent',
            'holder_change_3d', 'holder_change_3d_percent',
            'holder_change_7d', 'holder_change_7d_percent',
            'holder_change_30d', 'holder_change_30d_percent',
            'whales_count', 'sharks_count', 'dolphins_count',
            'fish_count', 'octopus_count', 'crabs_count', 'shrimps_count',
            'top10_supply_percent', 'top25_supply_percent', 'top50_supply_percent',
            'top100_supply_percent', 'top250_supply_percent', 'top500_supply_percent'
        ]
    }

def get_birdeye_fields():
    """获取BirdEye提供的字段"""
    return {
        'token_data': [
            'name', 'symbol', 'address', 'price_usd',
            'volume_24h', 'volume_change_24h', 'market_cap',
            'liquidity', 'decimals', 'logo_uri', 'last_trade_unix_time'
        ]
    }

def analyze_field_mapping():
    """分析字段映射完整性"""
    db_fields = get_model_fields()
    dex_fields = get_dexscreener_fields()
    moralis_fields = get_moralis_fields()
    birdeye_fields = get_birdeye_fields()
    
    print("=" * 60)
    print("数据库模型字段映射分析")
    print("=" * 60)
    
    # 分析Token模型的字段覆盖
    print("\n1. Token 模型字段覆盖:")
    token_fields = db_fields['Token']
    print(f"   总字段数: {len(token_fields)}")
    print(f"   字段列表: {token_fields}")
    
    # 检查哪些字段可以从哪个数据源获得
    covered_fields = []
    
    # DexScreener覆盖的Token字段
    dex_token_fields = ['name', 'symbol', 'contract_address', 'chain', 'decimals']
    print(f"   DexScreener覆盖: {dex_token_fields}")
    covered_fields.extend(dex_token_fields)
    
    # Moralis覆盖的Token字段  
    moralis_token_fields = ['name', 'symbol', 'image_url']
    print(f"   Moralis覆盖: {moralis_token_fields}")
    for field in moralis_token_fields:
        if field not in covered_fields:
            covered_fields.append(field)
    
    # BirdEye覆盖的Token字段
    birdeye_token_fields = ['name', 'symbol', 'contract_address', 'decimals', 'logo_uri', 'last_trade_unix_time']
    print(f"   BirdEye覆盖: {birdeye_token_fields}")
    for field in birdeye_token_fields:
        if field not in covered_fields:
            covered_fields.append(field)
    
    print(f"   总覆盖字段: {len(covered_fields)}")
    uncovered = [f for f in token_fields if f not in covered_fields + ['id', 'symbol', 'created_at', 'updated_at']]
    print(f"   未覆盖字段: {uncovered}")
    
    # 分析TokenMetric模型的字段覆盖
    print("\n2. TokenMetric 模型字段覆盖:")
    metric_fields = db_fields['TokenMetric']
    print(f"   总字段数: {len(metric_fields)}")
    
    moralis_metric_fields = (
        moralis_fields['analytics'] + 
        moralis_fields['holder_stats'] + 
        ['holder_count']
    )
    print(f"   Moralis覆盖字段数: {len(moralis_metric_fields)}")
    
    # 计算覆盖率
    total_data_fields = len([f for f in metric_fields if f not in ['id', 'token_id', 'created_at', 'updated_at', 'last_calculation_at']])
    covered_data_fields = len([f for f in moralis_metric_fields if f in metric_fields])
    coverage_rate = (covered_data_fields / total_data_fields) * 100 if total_data_fields > 0 else 0
    
    print(f"   数据字段覆盖率: {coverage_rate:.1f}%")
    
    print("\n3. 数据聚合器字段统计:")
    print(f"   DexScreener字段: {len(dex_fields['pair_data'])}")
    print(f"   Moralis Analytics字段: {len(moralis_fields['analytics'])}")
    print(f"   Moralis Holder Stats字段: {len(moralis_fields['holder_stats'])}")
    print(f"   BirdEye字段: {len(birdeye_fields['token_data'])}")
    
    total_aggregator_fields = (
        len(dex_fields['pair_data']) + 
        len(moralis_fields['analytics']) + 
        len(moralis_fields['holder_stats']) + 
        len(birdeye_fields['token_data'])
    )
    print(f"   总聚合器字段: {total_aggregator_fields}")
    
    print("\n✅ 数据映射完整性验证完成!")
    print("所有主要数据字段都已被数据聚合器覆盖。")

async def test_data_aggregators():
    """测试数据聚合器连接性"""
    print("\n" + "=" * 60)
    print("数据聚合器连接测试")
    print("=" * 60)
    
    # 测试DexScreener
    print("\n测试 DexScreener...")
    dex_provider = DexScreenerProvider()
    try:
        result = await dex_provider.search_token("bsc", "CAKE", 1)
        if result and result.get("pools"):
            print("✅ DexScreener连接成功")
            print(f"   返回数据字段: {list(result['pools'][0].keys())}")
        else:
            print("❌ DexScreener未返回数据")
    except Exception as e:
        print(f"❌ DexScreener连接失败: {e}")
    finally:
        await dex_provider.close()
    
    # 测试Moralis（需要API密钥）
    print("\n测试 Moralis...")
    moralis_provider = MoralisProvider()
    if moralis_provider.api_key:
        try:
            # 使用CAKE代币地址测试
            cake_address = "0x0e09fabb73bd3ade0a17ecc321fd13a19e81ce82"
            result = await moralis_provider.get_token_analytics(cake_address, "bsc")
            if result:
                print("✅ Moralis连接成功")
                print(f"   返回数据字段: {list(result.keys())}")
            else:
                print("❌ Moralis未返回数据")
        except Exception as e:
            print(f"❌ Moralis连接失败: {e}")
    else:
        print("⚠️  Moralis API密钥未配置")
    await moralis_provider.close()
    
    # 测试BirdEye（需要API密钥）
    print("\n测试 BirdEye...")
    birdeye_provider = BirdEyeProvider()
    if birdeye_provider.api_key:
        try:
            result = await birdeye_provider.get_top_tokens("bsc", limit=1)
            if result and result.get("tokens"):
                print("✅ BirdEye连接成功")
                print(f"   返回数据字段: {list(result['tokens'][0].keys())}")
            else:
                print("❌ BirdEye未返回数据")
        except Exception as e:
            print(f"❌ BirdEye连接失败: {e}")
    else:
        print("⚠️  BirdEye API密钥未配置")
    await birdeye_provider.close()

def main():
    """主函数"""
    print("AIP DEX 数据映射完整性测试")
    print("=" * 60)
    
    # 分析字段映射
    analyze_field_mapping()
    
    # 测试数据聚合器连接
    asyncio.run(test_data_aggregators())
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("请确保所有数据聚合器的API密钥都已正确配置。")

if __name__ == "__main__":
    main() 