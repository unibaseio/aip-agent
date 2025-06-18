"""
Example usage of TokenService for comprehensive token data management

This example demonstrates:
1. Creating/finding tokens
2. Updating all token data (pools, metrics, technical indicators)
3. Getting decision-ready data for LLM
4. Batch operations for multiple tokens
"""

import argparse
import asyncio
import sys
from sqlalchemy.orm import Session
from models.database import get_db, init_database
from services.token_service import TokenService

async def example_single_token_workflow(token_symbol: str = "beeper", chain: str = "bsc"):
    """Example: Complete workflow for a single token"""
    print("=== Single Token Workflow ===")
    
    # Initialize service
    token_service = TokenService()
    db = next(get_db())
    
    try:
        # Step 1: Create or get token
        print("Step 1: Creating/getting token...")
        token = await token_service.get_or_create_token(
            db=db,
            symbol=token_symbol,
            chain=chain,
        )
        
        if not token:
            print("Failed to create/get token")
            return
            
        print(f"Token created/found: {token.symbol} ({token.id})")
        
        # Step 2: Update token pools and pool metrics
        print("Step 2: Updating token pools...")
        pools_result = await token_service.update_token_pools(
            db=db,
            token_id=str(token.id),
            force_update=True
        )
        print(f"Pools update result: {pools_result}")
        
        # Step 3: Update token metrics, technical indicators and signals
        print("Step 3: Updating token metrics and indicators...")
        token_result = await token_service.update_token(
            db=db,
            token_id=str(token.id),
            force_update=False
        )
        print(f"Token update result: {token_result}")
        
        # Step 4: Get comprehensive decision data
        print("Step 4: Getting decision data...")
        decision_data = await token_service.get_token_decision_data(
            db=db,
            token_id=str(token.id)
        )
        
        if decision_data:
            print("Decision data retrieved successfully!")
            print(f"Token: {decision_data['token_info']['symbol']}")
            print(f"Current Price: ${decision_data['current_metrics'].get('weighted_price_usd', 0):.6f}")
            print(f"Market Cap: ${decision_data['current_metrics'].get('market_cap', 0):,.2f}")
            print(f"24h Volume: ${decision_data['current_metrics'].get('total_volume_24h', 0):,.2f}")
            print(f"RSI: {decision_data['technical_indicators'].get('rsi_14d', 'N/A')}")
            print(f"Signal Strength: {decision_data['technical_indicators'].get('signal_strength', 'N/A')}")
            
            # Handle volatility formatting safely
            volatility = decision_data['technical_indicators'].get('volatility_24h')
            volatility_str = f"{volatility:.2f}%" if volatility is not None else "N/A"
            print(f"Volatility: {volatility_str}")
            
            print(f"Risk Level: {decision_data['risk_factors'].get('volatility_level', 'N/A')}")
            
            # Data completeness check
            completeness = decision_data['data_completeness']
            print(f"\nData Completeness:")
            print(f"  Has Token Metrics: {completeness['has_token_metrics']}")
            print(f"  Has Technical Indicators: {completeness['has_technical_indicators']}")
            print(f"  Has Moralis Data: {completeness['has_moralis_data']}")
            print(f"  Has Historical Data: {completeness['has_historical_data']} ({len(decision_data['historical_data'])} records)")
            print(f"  Has Pool Data: {completeness['has_pool_data']} ({len(decision_data['pool_data'])} pools)")
            
            # Step 5: LLM Analysis for Trading Recommendations
            print("\nStep 5: LLM Analysis for Trading Recommendations...")
            try:
                from llm.token_analyzer import analyze_token_with_llm
                
                llm_analysis = await analyze_token_with_llm(decision_data)
                
                print("🤖 LLM Analysis Results:")
                print(f"  Token Symbol: {llm_analysis.get('token_symbol', 'N/A')}")
                print(f"  Analysis Timestamp: {llm_analysis.get('timestamp', 'N/A')}")
                
                # Display the LLM analysis result
                analysis_text = llm_analysis.get('result', '')
                print(f"\n📋 LLM Analysis:")
                print(f"  {analysis_text}")
               

            except Exception as e:
                print(f"❌ LLM Analysis Failed: {e}")
                print("  Note: Make sure OPENAI_API_KEY is set in your environment")
                
        else:
            print("Failed to get decision data")
            
    except Exception as e:
        print(f"Error in single token workflow: {e}")
    finally:
        await token_service.close()
        db.close()

async def example_batch_workflow():
    """Example: Batch processing multiple tokens"""
    print("\n=== Batch Workflow ===")
    
    token_service = TokenService()
    db = next(get_db())
    
    try:
        # Create multiple tokens
        tokens_to_process = [
            ("beeper", "0x238950013FA29A3575EB7a3D99C00304047a77b5", "bsc", "Beeper"),
        ]
        
        token_ids = []
        
        # Step 1: Create all tokens
        print("Step 1: Creating tokens...")
        for symbol, address, chain, name in tokens_to_process:
            token = await token_service.get_or_create_token(
                db=db,
                symbol=symbol,
                contract_address=address,
                chain=chain,
                name=name
            )
            if token:
                token_ids.append(str(token.id))
                print(f"  {symbol}: {token.id}")
        
        # Step 2: Batch update all tokens
        print("Step 2: Batch updating tokens...")
        batch_result = await token_service.batch_update_tokens(
            db=db,
            token_ids=token_ids,
            force_update=True
        )
        
        print(f"Batch update completed:")
        print(f"  Total tokens: {batch_result['total_tokens']}")
        print(f"  Successfully updated: {batch_result['updated_tokens']}")
        print(f"  Failed: {batch_result['failed_tokens']}")
        
        # Step 3: Get comparative analysis
        print("Step 3: Getting comparative analysis...")
        comparison_data = await token_service.get_multiple_tokens_decision_data(
            db=db,
            token_ids=token_ids
        )
        
        if comparison_data.get('comparative_analysis'):
            analysis = comparison_data['comparative_analysis']
            print(f"\nComparative Analysis:")
            print(f"  Total tokens analyzed: {analysis['summary']['total_tokens']}")
            print(f"  Tokens with buy signals: {analysis['summary']['tokens_with_buy_signal']}")
            print(f"  Tokens with sell signals: {analysis['summary']['tokens_with_sell_signal']}")
            print(f"  High risk tokens: {analysis['summary']['high_risk_tokens']}")
            
            # Show rankings
            print(f"\nTop tokens by signal strength:")
            for i, (symbol, data) in enumerate(analysis['rankings']['by_signal_strength'][:3]):
                signal_strength = data.get('signal_strength')
                signal_str = f"{signal_strength:.3f}" if signal_strength is not None else "N/A"
                print(f"  {i+1}. {symbol}: {signal_str}")
                
    except Exception as e:
        print(f"Error in batch workflow: {e}")
    finally:
        await token_service.close()
        db.close()

async def example_maintenance_workflow():
    """Example: Maintenance and data freshness workflow"""
    print("\n=== Maintenance Workflow ===")
    
    token_service = TokenService()
    db = next(get_db())
    
    try:
        # Step 1: Find tokens that need updates
        print("Step 1: Finding tokens that need updates...")
        tokens_needing_update = await token_service.get_tokens_requiring_update(
            db=db,
            max_age_hours=2  # Tokens not updated in last 2 hours
        )
        
        print(f"Found {len(tokens_needing_update)} tokens requiring updates")
        
        if tokens_needing_update:
            # Step 2: Update stale tokens
            print("Step 2: Updating stale tokens...")
            update_result = await token_service.batch_update_tokens(
                db=db,
                token_ids=tokens_needing_update[:5],  # Update first 5 only for demo
                force_update=True
            )
            
            print(f"Maintenance update completed:")
            print(f"  Updated: {update_result['updated_tokens']}")
            print(f"  Failed: {update_result['failed_tokens']}")
            
    except Exception as e:
        print(f"Error in maintenance workflow: {e}")
    finally:
        await token_service.close()
        db.close()

async def main():
    """Run all example workflows"""
    parser = argparse.ArgumentParser(description="Run AIP DEX Token Data Scheduler")
    parser.add_argument("--token-symbol", type=str, default="beeper", help="Token symbol")
    parser.add_argument("--chain", type=str, default="bsc", help="Chain")
    args = parser.parse_args()

    print("TokenService Complete Data Management Examples")
    print("=" * 50)
    
    # Initialize database first
    print("Initializing database...")
    if not init_database():
        print("❌ Failed to initialize database. Exiting.")
        return
    print("✓ Database initialized successfully")
    print()
    
    # Run single token workflow
    await example_single_token_workflow(args.token_symbol, args.chain)
    
    # Run batch workflow
    await example_batch_workflow()
    
    # Run maintenance workflow
    await example_maintenance_workflow()
    
    print("\n" + "=" * 50)
    print("All examples completed!")

if __name__ == "__main__":
    asyncio.run(main()) 