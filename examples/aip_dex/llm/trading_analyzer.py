"""
Trading Decision Analyzer using LLM

This module provides LLM-powered analysis for trading decisions in two phases:
1. Phase 1: Sell Analysis - Analyze existing positions for selling opportunities
2. Phase 2: Buy Analysis - Analyze market for new buying opportunities
"""

import os
import json
from typing import Dict, Any, Optional, List
from openai import AsyncOpenAI
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

class TradingDecisionAnalyzer:
    """LLM analyzer for trading bot decisions"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.client = AsyncOpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY")
        )
    
    async def analyze_sell_decisions(self, positions_data: List[Dict[str, Any]], 
                                   bot_config: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 1: Analyze current positions for selling opportunities"""
        try:
            if not positions_data:
                return {
                    "phase": "sell_analysis",
                    "decisions": [],
                    "summary": "No active positions to analyze"
                }
            
            # Create comprehensive sell analysis prompt
            prompt = self._create_sell_analysis_prompt(positions_data, bot_config)

            print("sell analysis prompt: ", prompt)        

            response = await self.client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": self._get_sell_analysis_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            
            # Parse LLM response
            analysis_result = self._parse_sell_analysis_response(content)
            
            return {
                "phase": "sell_analysis",
                "timestamp": datetime.now().isoformat(),
                "analyzed_positions": len(positions_data),
                "llm_response": content,
                "decisions": analysis_result.get("decisions", []),
                "reasoning": analysis_result.get("reasoning", ""),
                "market_sentiment": analysis_result.get("market_sentiment", "neutral"),
                "risk_assessment": analysis_result.get("risk_assessment", "medium"),
                "summary": f"Analyzed {len(positions_data)} positions, found {len(analysis_result.get('decisions', []))} decisions"
            }
            
        except Exception as e:
            print(f"Error in sell analysis: {e}")
            return self._fallback_sell_analysis(positions_data)
    
    async def analyze_buy_decisions(self, available_tokens: List[Dict[str, Any]], 
                                  bot_status: Dict[str, Any], 
                                  bot_config: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 2: Analyze market for new buying opportunities - Two-stage approach"""
        try:
            if not available_tokens:
                return {
                    "phase": "buy_analysis",
                    "decision": "no_buy",
                    "reasoning": "No tokens available for analysis"
                }
            
            print(f"   🔍 Stage 1: Screening {len(available_tokens)} tokens for top 10 candidates...")
            
            # Stage 1: LLM screening to select top 5 tokens from all available tokens
            top_tokens = await self._llm_screen_tokens(available_tokens, bot_status, bot_config)
            
            if not top_tokens:
                return {
                    "phase": "buy_analysis", 
                    "decision": "no_buy",
                    "reasoning": "No suitable tokens found after LLM screening"
                }
            
            print(f"   📊 Stage 2: Analyzing {len(top_tokens)} top candidates for final decision...")
            
            # Stage 2: Detailed analysis of top 5 tokens to make final decision
            prompt = self._create_buy_analysis_prompt(top_tokens, bot_status, bot_config)
            
            print("buy analysis prompt: ", prompt)        
            
            response = await self.client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": self._get_buy_analysis_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            
            # Parse LLM response
            analysis_result = self._parse_buy_analysis_response(content)
            
            return {
                "phase": "buy_analysis",
                "timestamp": datetime.now().isoformat(),
                "total_tokens": len(available_tokens),
                "screened_tokens": len(top_tokens), 
                "llm_response": content,
                "decision": analysis_result.get("decision", "no_buy"),
                "selected_token": analysis_result.get("selected_token"),
                "buy_amount_usd": analysis_result.get("buy_amount_usd", 0),
                "confidence_score": analysis_result.get("confidence_score", 0),
                "reasoning": analysis_result.get("reasoning", ""),
                "risk_factors": analysis_result.get("risk_factors", []),
                "expected_return": analysis_result.get("expected_return", 0)
            }
            
        except Exception as e:
            print(f"Error in buy analysis: {e}")
            return self._fallback_buy_analysis(available_tokens, bot_status)
    
    def _get_sell_analysis_system_prompt(self) -> str:
        """System prompt for sell analysis"""
        return """You are a professional cryptocurrency trading analyst.
        
Your task is to analyze current trading positions and provide selling recommendations.

Please respond in Chinese but keep data and code parts in English."""
    
    def _get_token_screening_system_prompt(self) -> str:
        """System prompt for token screening (Stage 1)"""
        return """You are a cryptocurrency market analyst specializing in initial token screening and opportunity identification.

Your task is to quickly evaluate a large list of tokens and select the top 5 most promising candidates for detailed analysis.

SCREENING CRITERIA:
1. Market activity (trading volume, liquidity)
2. Price momentum and trends
3. Market sentiment indicators
4. Risk-reward potential
5. Technical signal strength

SELECTION PROCESS:
- Review basic market metrics for each token
- Identify tokens with strong fundamentals and momentum
- Consider market sentiment and trading activity
- Select diverse opportunities across different market segments
- Focus on tokens with clear bullish signals

RESPONSE FORMAT:
Return only a JSON array of exactly 5 token symbols, ordered by preference:

```json
["TOKEN1", "TOKEN2", "TOKEN3", "TOKEN4", "TOKEN5"]
```

请用中文回答，但保持数据和代码部分用英文。"""

    def _get_buy_analysis_system_prompt(self) -> str:
        """System prompt for buy analysis (Stage 2)"""
        return """You are a professional cryptocurrency trading analyst specializing in market opportunity identification and entry timing.

Your task is to analyze the top 5 pre-screened tokens and identify the best buying opportunity based on:
- Technical indicators and market momentum
- Fundamental analysis (trading volume, liquidity, holder metrics)
- Risk-reward assessment
- Portfolio allocation strategy
- Current account status and position analysis

Evaluation criteria:
1. Price trends and technical signals
2. Trading volume and liquidity health
3. Market sentiment and holder behavior
4. Risk factors and volatility
5. Potential for profitable returns
6. Portfolio diversification needs
7. Available capital allocation

ACCOUNT & PORTFOLIO ANALYSIS:
- Consider current balance vs. total assets ratio
- Evaluate portfolio diversification (avoid over-concentration)
- Check if new position would exceed maximum position size limits
- Assess if current positions are performing well or need rebalancing
- Consider correlation with existing holdings

DECISION FRAMEWORK:
- Only recommend BUY if there's a clear opportunity with good risk-reward ratio
- Consider trading costs impact on minimum viable investment amounts
- Factor in bot's available balance and position size limits
- Ensure portfolio diversification (don't over-concentrate in similar assets)
- Provide specific buy amount recommendations based on risk management
- Include expected return estimates and timeframe
- Consider market timing and entry points

You can recommend:
- "BUY" with specific token and amount
- "NO_BUY" if no suitable opportunities or portfolio constraints

Always provide detailed reasoning and confidence scores (0.0-1.0).

请用中文回答，但保持数据和代码部分用英文。"""
    
    def _create_sell_analysis_prompt(self, positions_data: List[Dict[str, Any]], 
                                   bot_config: Dict[str, Any]) -> str:
        """Create detailed sell analysis prompt"""
        
        prompt = f"""请分析以下持仓情况，提供卖出建议：

## 交易机器人配置
策略类型: {bot_config.get('strategy_type', 'unknown')}
止损百分比: {bot_config.get('stop_loss_percentage', 0)}%
止盈百分比: {bot_config.get('take_profit_percentage', 0)}%
最低收益率阈值: {bot_config.get('min_profit_threshold', 0)}%
交易手续费率: {bot_config.get('trading_fee_percentage', 0.5)}%

## 当前持仓分析

"""
        
        for i, position in enumerate(positions_data, 1):
            token_info = position.get('token_info', {})
            current_metrics = position.get('current_metrics', {})
            technical_indicators = position.get('technical_indicators', {})
            moralis_data = position.get('moralis_data', {})
            expected_returns = position.get('expected_returns', {})
            
            prompt += f"""
### 持仓 {i}: {token_info.get('symbol', 'Unknown')}

**基本信息:**
- 代币名称: {token_info.get('name', 'Unknown')} ({token_info.get('symbol', 'Unknown')})
- 持有数量: {position.get('quantity', 0):,.2f}
- 平均成本: ${position.get('average_cost_usd', 0):.6f}
- 总成本: ${position.get('total_cost_usd', 0):,.2f}

**当前市场状况:**
- 当前价格: ${current_metrics.get('weighted_price_usd', 0):.6f}
- 当前市值: ${position.get('current_value_usd', 0):,.2f}
- 未实现盈亏: ${position.get('unrealized_pnl_usd', 0):,.2f} ({position.get('unrealized_pnl_percentage', 0):.2f}%)

**市场数据:**
- 24h交易量: ${current_metrics.get('total_volume_24h', 0):,.2f}
- 流动性: ${current_metrics.get('total_liquidity_usd', 0):,.2f}
- 24h价格变化: {moralis_data.get('price_changes', {}).get('24h', 0):.2f}%
- RSI: {technical_indicators.get('rsi_14d', 50):.1f}
- 趋势方向: {technical_indicators.get('trend_direction', 'unknown')}

**不同卖出比例的预期收益率:**
"""
            
            # Add expected returns for different sell percentages
            for percentage in [10, 20, 30, 50, 75, 100]:
                if str(percentage) in expected_returns:
                    ret_data = expected_returns[str(percentage)]
                    fin_ret =  ret_data.get('financial_impact', {})
                    prompt += f"- 卖出{percentage}%: 净收益率 {fin_ret.get('net_return_rate', 0):.2f}%, 净收益 ${fin_ret.get('net_profit_usd', 0):,.2f}\n"
        
        prompt += f"""

## 分析要求

请为每个持仓提供详细分析和建议，格式如下：

```json
{{
  "decisions": [
    {{
      "token_symbol": "TOKEN_SYMBOL",
      "action": "HOLD/SELL", 
      "sell_percentage": 0,  // 0-100, 仅在action为SELL时有效
      "confidence_score": 0.8,  // 0.0-1.0
      "reasoning": "详细的分析理由，包括技术面、基本面、风险考虑",
      "risk_factors": ["具体的风险因素"],
      "expected_outcome": "预期结果说明"
    }}
  ],
  "market_sentiment": "bullish/bearish/neutral",
  "risk_assessment": "low/medium/high", 
  "reasoning": "整体市场分析和决策逻辑"
}}
```

**关键分析要点:**
1. 考虑交易成本对小比例卖出收益率的影响
2. 评估当前技术指标和市场趋势
3. 考虑风险管理和止盈止损策略
4. 分析是否达到预设的收益率阈值
5. 评估继续持有 vs 部分/全部卖出的风险收益比

"""
#**注意:**
#- 无论何种情况，至少选择一个代币卖出, 如果所有持仓都亏损，则选择亏损最小的代币卖出
#"""
        
        return prompt
    
    def _create_token_screening_prompt(self, tokens: List[Dict[str, Any]], 
                                     bot_status: Dict[str, Any], 
                                     bot_config: Dict[str, Any]) -> str:
        """Create prompt for token screening (Stage 1)"""
        
        # Get available balance from bot_status structure
        financial_status = bot_status.get('financial_status', {})
        available_balance = financial_status.get('current_balance_usd', 0)
        strategy_type = bot_config.get('strategy_type', 'unknown')
        
        prompt = f"""请从以下代币列表中筛选出最有潜力的10个代币：

## 账户信息
可用余额: ${available_balance:,.2f}
策略类型: {strategy_type}

## 代币列表 (共{len(tokens)}个)

"""
        
        for i, token in enumerate(tokens, 1):
            token_info = token.get('token_info', {})
            current_metrics = token.get('current_metrics', {})
            moralis_data = token.get('moralis_data', {})
            
            prompt += f"""
### {i}. {token_info.get('symbol', 'Unknown')} ({token_info.get('name', 'Unknown')})
- 当前价格: ${current_metrics.get('weighted_price_usd', 0):.6f}
- 市值: ${current_metrics.get('market_cap', 0):,.0f}
- 24h交易量: ${current_metrics.get('total_volume_24h', 0):,.0f}
- 流动性: ${current_metrics.get('total_liquidity_usd', 0):,.0f}
- 24h价格变化: {moralis_data.get('price_changes', {}).get('24h', 0):.2f}%
- 1h价格变化: {moralis_data.get('price_changes', {}).get('1h', 0):.2f}%
- 交易池数量: {current_metrics.get('pools_count', 0)}
"""
        
        prompt += f"""

## 策略配置参数
- 策略类型: {strategy_type}
- 最大仓位比例: {bot_config.get('max_position_size', 10)}%
- 止损百分比: {bot_config.get('stop_loss_percentage', 5)}%
- 止盈百分比: {bot_config.get('take_profit_percentage', 15)}%
- 最低收益率阈值: {bot_config.get('min_profit_threshold', 3)}%

## 筛选要求

请根据以下标准筛选出最有潜力的10个代币：

1. **市场活跃度**: 交易量、流动性、交易对数量
2. **价格动量**: 短期和中期价格趋势
3. **市场情绪**: 价格变化、交易活动
4. **风险收益比**: 市值、流动性、价格稳定性
5. **技术信号**: 价格趋势、市场表现
6. **类似代币**: 类似代币只选一个，不要重复选择，例如ETH和WETH，不要同时选择

**策略考虑**:
- {strategy_type}策略偏好: {'保守型 - 注重稳定性和低风险' if strategy_type == 'conservative' else '激进型 - 追求高收益' if strategy_type == 'aggressive' else '平衡型 - 风险收益兼顾'}
- 考虑策略的风险承受能力和收益目标
- 根据策略类型调整筛选标准

请返回JSON格式的5个代币符号，按潜力排序：

```json
["TOKEN1", "TOKEN2", "TOKEN3", "TOKEN4", "TOKEN5", "TOKEN6", "TOKEN7", "TOKEN8", "TOKEN9", "TOKEN10"]
```

**注意**: 只返回代币符号，不要其他内容。
"""
        
        return prompt
    
    def _create_buy_analysis_prompt(self, top_tokens: List[Dict[str, Any]], 
                                  bot_status: Dict[str, Any], 
                                  bot_config: Dict[str, Any]) -> str:
        """Create detailed buy analysis prompt"""
        
        # Get available balance from bot_status structure
        financial_status = bot_status.get('financial_status', {})
        available_balance = financial_status.get('current_balance_usd', 0)
        total_assets = financial_status.get('total_assets_usd', 0)
        total_profit = financial_status.get('total_profit_usd', 0)
        max_position_size = bot_config.get('max_position_size', 10)
        min_trade_amount = bot_config.get('min_trade_amount_usd', 10)
        
        # Get current positions information
        positions = bot_status.get('positions', [])
        current_positions_count = len(positions)
        total_position_value = sum(float(pos.get('current_value_usd', 0)) for pos in positions)
        total_unrealized_pnl = sum(float(pos.get('unrealized_pnl_usd', 0)) for pos in positions)
        
        # Calculate portfolio metrics
        portfolio_diversification = (total_position_value / total_assets * 100) if total_assets > 0 else 0
        max_single_position = max([float(pos.get('current_value_usd', 0)) for pos in positions]) if positions else 0
        max_position_percentage = (max_single_position / total_assets * 100) if total_assets > 0 else 0
        
        prompt = f"""请分析以下代币，寻找最佳买入机会：

## 账户状态分析
**资金状况:**
- 可用余额: ${available_balance:,.2f}
- 总资产: ${total_assets:,.2f}
- 总收益: ${total_profit:,.2f}
- 收益率: {(total_profit / (total_assets - total_profit) * 100) if (total_assets - total_profit) > 0 else 0:.2f}%

**持仓状况:**
- 当前持仓数量: {current_positions_count}
- 持仓总价值: ${total_position_value:,.2f}
- 未实现盈亏: ${total_unrealized_pnl:,.2f}
- 投资组合分散度: {portfolio_diversification:.1f}%
- 最大单币仓位: ${max_single_position:,.2f} ({max_position_percentage:.1f}% of total)

**交易限制:**
- 最大单币仓位: {max_position_size}%
- 最小交易金额: ${min_trade_amount}
- 策略类型: {bot_config.get('strategy_type', 'unknown')}

**当前持仓详情:**
"""
        
        # Add current positions information
        if positions:
            for i, pos in enumerate(positions, 1):
                token_symbol = pos.get('token_symbol', 'Unknown')
                quantity = pos.get('quantity', 0)
                avg_cost = pos.get('average_cost_usd', 0)
                current_value = pos.get('current_value_usd', 0)
                unrealized_pnl = pos.get('unrealized_pnl_usd', 0)
                unrealized_pnl_pct = pos.get('unrealized_pnl_percentage', 0)
                position_percentage = (float(current_value) / total_assets * 100) if total_assets > 0 else 0
                
                prompt += f"""
**持仓 {i}: {token_symbol}**
- 持有数量: {float(quantity):,.2f}
- 平均成本: ${float(avg_cost):.6f}
- 当前价值: ${float(current_value):,.2f} ({position_percentage:.1f}% of portfolio)
- 未实现盈亏: ${float(unrealized_pnl):+,.2f} ({float(unrealized_pnl_pct):+.2f}%)
"""
        else:
            prompt += "**当前无持仓**\n"
        
        prompt += f"""

## 候选代币分析

"""
        
        for i, token in enumerate(top_tokens, 1):
            token_info = token.get('token_info', {})
            current_metrics = token.get('current_metrics', {})
            technical_indicators = token.get('technical_indicators', {})
            moralis_data = token.get('moralis_data', {})
            
            prompt += f"""
### 代币 {i}: {token_info.get('symbol', 'Unknown')}

**基本信息:**
- 名称: {token_info.get('name', 'Unknown')} ({token_info.get('symbol', 'Unknown')})
- 链: {token_info.get('chain', 'unknown')}
- 当前价格: ${current_metrics.get('weighted_price_usd', 0):.6f}

**市场数据:**
- 市值: ${current_metrics.get('market_cap', 0):,.2f}
- 24h交易量: ${current_metrics.get('total_volume_24h', 0):,.2f}
- 流动性: ${current_metrics.get('total_liquidity_usd', 0):,.2f}
- 交易对数量: {current_metrics.get('pools_count', 0)}

**价格走势:**
- 5分钟: {moralis_data.get('price_changes', {}).get('5m', 0):.2f}%
- 1小时: {moralis_data.get('price_changes', {}).get('1h', 0):.2f}%
- 6小时: {moralis_data.get('price_changes', {}).get('6h', 0):.2f}%
- 24小时: {moralis_data.get('price_changes', {}).get('24h', 0):.2f}%

**技术指标:**
- RSI: {technical_indicators.get('rsi_14d', 50):.1f}
- 趋势方向: {technical_indicators.get('trend_direction', 'unknown')}
- 信号强度: {technical_indicators.get('signal_strength', 0):.2f}
- 波动率: {technical_indicators.get('volatility_24h', 0):.2f}%

**交易活动:**
- 24h买入量: ${moralis_data.get('volume_analysis', {}).get('buy_volume_24h', 0):,.2f}
- 24h卖出量: ${moralis_data.get('volume_analysis', {}).get('sell_volume_24h', 0):,.2f}
- 买卖比: {moralis_data.get('volume_analysis', {}).get('buy_sell_ratio', 1):.2f}
- 活跃钱包: {moralis_data.get('trader_activity', {}).get('unique_wallets_24h', 0)}

**持币者分析:**
- 总持币者: {moralis_data.get('holder_analysis', {}).get('total_holders', 0)}
- 24h持币者变化: {moralis_data.get('holder_analysis', {}).get('holder_change_24h_percent', 0):.2f}%
- 大户集中度: {moralis_data.get('distribution', {}).get('concentration_risk', 'unknown')}
"""
        
        prompt += f"""

## 策略配置参数
- 策略类型: {bot_config.get('strategy_type', 'unknown')}
- 最大仓位比例: {bot_config.get('max_position_size', 10)}%
- 止损百分比: {bot_config.get('stop_loss_percentage', 5)}%
- 止盈百分比: {bot_config.get('take_profit_percentage', 15)}%
- 最低收益率阈值: {bot_config.get('min_profit_threshold', 3)}%
- 交易手续费率: {bot_config.get('trading_fee_percentage', 0.5)}%
- LLM置信度阈值: {bot_config.get('llm_confidence_threshold', 0.7)}

## 分析要求

请基于账户状态、当前持仓和候选代币分析，选择最佳买入机会，格式如下：

```json
{{
  "decision": "BUY/NO_BUY",
  "selected_token": {{
    "symbol": "TOKEN_SYMBOL",  // 仅在decision为BUY时有效
    "name": "Token Name"
  }},
  "buy_amount_usd": 0,  // 建议买入金额，仅在decision为BUY时有效
  "confidence_score": 0.8,  // 0.0-1.0，必须达到配置的置信度阈值
  "reasoning": "详细的分析理由和选择逻辑",
  "risk_factors": ["具体的风险因素"],
  "expected_return": 15.5,  // 预期收益率百分比
  "timeframe": "预期持有时间框架",
  "market_analysis": "整体市场环境分析",
  "portfolio_impact": "对投资组合的影响分析"
}}
```

**分析要点:**
1. **账户状态评估:**
   - 可用余额是否足够进行有效投资
   - 当前收益率和风险承受能力
   - 是否需要调整投资策略

2. **持仓状况分析:**
   - 当前持仓的分散度和集中度风险
   - 现有持仓的表现和是否需要再平衡
   - 新持仓与现有持仓的相关性

3. **代币技术分析:**
   - 评估技术指标和价格趋势
   - 分析交易量和流动性健康度
   - 考虑市场情绪和持币者行为

4. **风险评估:**
   - 评估风险因素和波动性
   - 考虑市场时机和入场点
   - 分析潜在的下行风险

5. **仓位管理:**
   - 计算合理的买入金额（考虑仓位管理）
   - 确保不超过最大仓位限制
   - 保持投资组合的适当分散度

6. **收益预期:**
   - 提供预期收益和时间框架
   - 评估风险收益比
   - 考虑市场环境对收益的影响

**决策标准:**
- 只有在发现明确机会时才推荐BUY
- 考虑交易成本对最小投资金额的影响
- 遵循最大仓位限制和风险管理原则
- 确保投资组合分散度，避免过度集中
- 置信度必须达到策略要求的阈值
- 考虑当前市场环境和时机
"""
        
        return prompt
    
    async def _llm_screen_tokens(self, tokens: List[Dict[str, Any]], 
                               bot_status: Dict[str, Any], 
                               bot_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Stage 1: Use LLM to screen and select top 5 tokens from all available tokens"""
        try:
            # Create screening prompt with basic token information
            prompt = self._create_token_screening_prompt(tokens, bot_status, bot_config)
            
            response = await self.client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": self._get_token_screening_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            content = response.choices[0].message.content
            
            # Parse LLM response to get selected token symbols
            selected_symbols = self._parse_token_screening_response(content)
            
            if not selected_symbols:
                print("   ⚠️  LLM screening failed, using fallback method")
                return self._fallback_screen_tokens(tokens, limit=10)
            
            # Get the actual token objects for selected symbols
            selected_tokens = []
            for symbol in selected_symbols:
                for token in tokens:
                    if token.get('token_info', {}).get('symbol') == symbol:
                        selected_tokens.append(token)
                        break
            
            print(f"   ✅ LLM selected: {', '.join(selected_symbols)}")
            return selected_tokens
            
        except Exception as e:
            print(f"Error in LLM token screening: {e}")
            return self._fallback_screen_tokens(tokens, limit=5)
    
    def _fallback_screen_tokens(self, tokens: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
        """Fallback token screening based on basic metrics"""
        try:
            # Filter tokens with minimum requirements
            viable_tokens = []
            
            for token in tokens:
                current_metrics = token.get('current_metrics', {})
                
                # Basic filtering criteria
                volume_24h = current_metrics.get('total_volume_24h', 0)
                liquidity = current_metrics.get('total_liquidity_usd', 0)
                price = current_metrics.get('weighted_price_usd', 0)
                
                if volume_24h >= 1000 and liquidity >= 5000 and price > 0:
                    viable_tokens.append(token)
            
            # Sort by combined score (volume + liquidity)
            viable_tokens.sort(
                key=lambda x: (
                    x.get('current_metrics', {}).get('total_volume_24h', 0) + 
                    x.get('current_metrics', {}).get('total_liquidity_usd', 0)
                ),
                reverse=True
            )
            
            return viable_tokens[:limit]
            
        except Exception as e:
            print(f"Error in fallback screening: {e}")
            return tokens[:limit]
    
    def _parse_token_screening_response(self, response: str) -> List[str]:
        """Parse LLM token screening response to get selected token symbols"""
        try:
            # Extract JSON array from response
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                selected_symbols = json.loads(json_match.group(1))
                if isinstance(selected_symbols, list) and len(selected_symbols) <= 10:
                    return selected_symbols[:10]  # Ensure max 10 tokens
            
            # Fallback: try to extract symbols from text
            symbols = re.findall(r'["\']([A-Z]{2,10})["\']', response)
            return symbols[:10] if symbols else []
            
        except Exception as e:
            print(f"Error parsing token screening response: {e}")
            return []
    
    def _parse_sell_analysis_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM sell analysis response"""
        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                parsed_data = json.loads(json_match.group(1))
                
                # Validate and clean decisions
                decisions = parsed_data.get("decisions", [])
                if isinstance(decisions, list):
                    # Clean and validate each decision
                    cleaned_decisions = []
                    for decision in decisions:
                        if isinstance(decision, dict):
                            # Ensure required fields exist
                            cleaned_decision = {
                                "token_symbol": decision.get("token_symbol", ""),
                                "action": decision.get("action", "HOLD"),
                                "sell_percentage": max(0, min(100, decision.get("sell_percentage", 0))),
                                "confidence_score": max(0.0, min(1.0, decision.get("confidence_score", 0.5))),
                                "reasoning": decision.get("reasoning", ""),
                                "risk_factors": decision.get("risk_factors", []),
                                "expected_outcome": decision.get("expected_outcome", "")
                            }
                            cleaned_decisions.append(cleaned_decision)
                    
                    parsed_data["decisions"] = cleaned_decisions
                else:
                    parsed_data["decisions"] = []
                
                # Ensure other required fields exist
                parsed_data["market_sentiment"] = parsed_data.get("market_sentiment", "neutral")
                parsed_data["risk_assessment"] = parsed_data.get("risk_assessment", "medium")
                parsed_data["reasoning"] = parsed_data.get("reasoning", response)
                
                return parsed_data
            else:
                # Fallback parsing - try to extract basic information
                return {
                    "decisions": [],
                    "reasoning": response,
                    "market_sentiment": "neutral",
                    "risk_assessment": "medium"
                }
                
        except Exception as e:
            print(f"Error parsing sell analysis response: {e}")
            return {
                "decisions": [],
                "reasoning": response,
                "market_sentiment": "neutral", 
                "risk_assessment": "medium"
            }
    
    def _parse_buy_analysis_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM buy analysis response"""
        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                parsed_data = json.loads(json_match.group(1))
                
                # Validate and clean buy_amount_usd
                if parsed_data.get("decision") == "BUY":
                    buy_amount = parsed_data.get("buy_amount_usd", 0)
                    
                    # Convert to float and validate
                    try:
                        if isinstance(buy_amount, str):
                            # Remove any non-numeric characters except decimal point
                            buy_amount = re.sub(r'[^\d.]', '', buy_amount)
                            buy_amount = float(buy_amount) if buy_amount else 0
                        elif isinstance(buy_amount, (int, float)):
                            buy_amount = float(buy_amount)
                        else:
                            buy_amount = 0
                        
                        # Validate range
                        if buy_amount < 0:
                            print(f"   ⚠️  Invalid negative buy_amount_usd: {buy_amount}, setting to 0")
                            buy_amount = 0
                        elif buy_amount > 1000000:  # More than 1 million USD
                            print(f"   ⚠️  Unrealistically high buy_amount_usd: {buy_amount}, capping at 1000")
                            buy_amount = 1000
                        
                        parsed_data["buy_amount_usd"] = buy_amount
                        
                    except (ValueError, TypeError) as e:
                        print(f"   ⚠️  Error parsing buy_amount_usd: {e}, setting to 0")
                        parsed_data["buy_amount_usd"] = 0
                
                return parsed_data
            else:
                # Fallback parsing
                return {"decision": "no_buy", "reasoning": response}
        except Exception as e:
            print(f"Error parsing buy analysis response: {e}")
            return {"decision": "no_buy", "reasoning": response}
    
    def _fallback_sell_analysis(self, positions_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fallback sell analysis when LLM fails"""
        return {
            "phase": "sell_analysis",
            "timestamp": datetime.now().isoformat(),
            "analyzed_positions": len(positions_data),
            "llm_response": "",
            "decisions": [],
            "reasoning": "LLM service unavailable, using fallback analysis",
            "market_sentiment": "neutral",
            "risk_assessment": "medium",
            "summary": f"Fallback analysis for {len(positions_data)} positions"
        }
    
    def _fallback_buy_analysis(self, tokens: List[Dict[str, Any]], 
                             bot_status: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback buy analysis when LLM fails"""
        # Simple rule: no buy in fallback mode
        return {
            "phase": "buy_analysis",
            "decision": "no_buy",
            "reasoning": "LLM service unavailable, conservative approach: no buying",
            "confidence_score": 0.5
        } 