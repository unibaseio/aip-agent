import os
import json
from typing import Dict, Any, Optional, List
from openai import AsyncOpenAI
from dotenv import load_dotenv
import asyncio
from datetime import datetime

load_dotenv()

class TokenDecisionAnalyzer:
    """LLM analyzer specialized for token decision data analysis"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.client = AsyncOpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY")
        )
    
    async def analyze_token_decision(self, decision_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze token based on comprehensive decision data and provide trading recommendations"""
        try:
            # Create analysis prompt
            prompt = self._create_comprehensive_analysis_prompt(decision_data)
            
            response = await self.client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            print(f"LLM analysis response: \n {content}")
            
            # Return simple analysis result
            return {
                "timestamp": datetime.now().isoformat(),
                "token_symbol": decision_data.get("token_info", {}).get("symbol", "N/A"),
                "result": content
            }
            
        except Exception as e:
            print(f"LLM analysis error: {e}")
            return self._fallback_analysis(decision_data)
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for LLM analysis"""
        return """
        You are a professional DeFi and Web3 token trading analyst with extensive experience in technical analysis and fundamental analysis.

        Your tasks are:
        1. Analyze the provided token data, including technical indicators, trading volume, token distribution, historical performance, etc.
        2. Provide objective trading recommendations based on multi-dimensional data
        3. Assess risk levels and provide risk management advice
        4. Explain your analysis logic and reasoning process

        Analysis dimensions include:
        - Technical Analysis: RSI, moving averages, breakout signals, trend direction
        - Fundamental Analysis: trading volume, liquidity, market cap, token distribution
        - Market Sentiment: buy/sell ratios, holder changes, whale behavior
        - Risk Assessment: volatility, concentration risk, liquidity risk

        Please always remain objective and professional, and do not give overly optimistic or pessimistic advice.
        
        IMPORTANT: Please respond in Chinese (中文) for all analysis and recommendations.
        """
    
    def _create_comprehensive_analysis_prompt(self, decision_data: Dict[str, Any], user_intent: str = None) -> str:
        """Create comprehensive analysis prompt"""
        token_info = decision_data.get("token_info", {})
        current_metrics = decision_data.get("current_metrics", {})
        technical_indicators = decision_data.get("technical_indicators", {})
        moralis_data = decision_data.get("moralis_data", {})
        risk_factors = decision_data.get("risk_factors", {})
        pool_data = decision_data.get("pool_data", [])
        historical_data = decision_data.get("historical_data", [])
        data_completeness = decision_data.get("data_completeness", {})
        
        # Calculate key ratios and trends
        buy_sell_ratio = moralis_data.get("volume_analysis", {}).get("buy_sell_ratio", 1)
        trader_ratio = moralis_data.get("trader_activity", {}).get("trader_ratio", 1)
        concentration_risk = moralis_data.get("distribution", {}).get("concentration_risk", "UNKNOWN")
        
        # Extract data sources and latest update time
        data_sources = []
        latest_update_time = None
        
        # Check data completeness to determine available sources
        if data_completeness.get("has_moralis_data"):
            data_sources.append("Moralis (Trading Analytics & Holder Stats)")
        if data_completeness.get("has_pool_data"):
            data_sources.append("DexScreener (Pool Data & Market Metrics)")
        if data_completeness.get("has_technical_indicators"):
            data_sources.append("Technical Indicators (RSI, MA, Volatility)")
        if data_completeness.get("has_historical_data"):
            data_sources.append("Historical Data (30-day Trends)")
        
        # Get latest update time from current metrics
        if current_metrics.get("last_updated"):
            latest_update_time = current_metrics.get("last_updated")
        
        # Format data sources string
        data_sources_str = ", ".join(data_sources) if data_sources else "Database Records"
        
        if user_intent:
            prompt = f"""
            Please analyze the complete token data below and provide trading recommendations according to the user's intent: {user_intent}:
            """
        else:
            prompt = f"""
            Please analyze the complete token data below and provide trading recommendations:
            """

        prompt += f"""
        ## Basic Information
        Token Name: {token_info.get('name', 'N/A')}
        Token Symbol: ${token_info.get('symbol', 'N/A')}
        Blockchain: {token_info.get('chain', 'N/A')}
        Contract Address: {token_info.get('contract_address', 'N/A')}

        ## Current Market Data
        Current Price: ${current_metrics.get('weighted_price_usd', 0):.8f}
        24h Trading Volume: ${current_metrics.get('total_volume_24h', 0):,.2f}
        Market Cap: ${current_metrics.get('market_cap', 0):,.2f}
        Total Liquidity: ${current_metrics.get('total_liquidity_usd', 0):,.2f}
        Active Trading Pairs: {current_metrics.get('pools_count', 0)}

        ## Technical Indicators
        RSI (14-day): {technical_indicators.get('rsi_14d', 'N/A')}
        7-day Moving Average: ${technical_indicators.get('ma_7d', 0):.8f}
        30-day Moving Average: ${technical_indicators.get('ma_30d', 0):.8f}
        24h Volatility: {technical_indicators.get('volatility_24h', 0):.2f}%
        Breakout Signal: {technical_indicators.get('breakout_signal', 'N/A')}
        Trend Direction: {technical_indicators.get('trend_direction', 'N/A')}
        Signal Strength: {technical_indicators.get('signal_strength', 'N/A')}

        ## Price Changes
        5 minutes: {moralis_data.get('price_changes', {}).get('5m', 0):.2f}%
        1 hour: {moralis_data.get('price_changes', {}).get('1h', 0):.2f}%
        6 hours: {moralis_data.get('price_changes', {}).get('6h', 0):.2f}%
        24 hours: {moralis_data.get('price_changes', {}).get('24h', 0):.2f}%

        ## Trading Activity Analysis
        24h Buy Volume: ${moralis_data.get('volume_analysis', {}).get('buy_volume_24h', 0):,.2f}
        24h Sell Volume: ${moralis_data.get('volume_analysis', {}).get('sell_volume_24h', 0):,.2f}
        Buy/Sell Ratio: {buy_sell_ratio:.2f}
        Net Buy Volume: ${moralis_data.get('volume_analysis', {}).get('net_volume', 0):,.2f}

        ## Trader Activity
        24h Buyers Count: {moralis_data.get('trader_activity', {}).get('total_buyers_24h', 0)}
        24h Sellers Count: {moralis_data.get('trader_activity', {}).get('total_sellers_24h', 0)}
        Trader Ratio (Buyers/Sellers): {trader_ratio:.2f}
        24h Active Wallets: {moralis_data.get('trader_activity', {}).get('unique_wallets_24h', 0)}

        ## Holder Analysis
        Total Holders: {moralis_data.get('holder_analysis', {}).get('total_holders', 0)}
        24h Holder Change: {moralis_data.get('holder_analysis', {}).get('holder_change_24h', 0)}
        24h Holder Change Percentage: {moralis_data.get('holder_analysis', {}).get('holder_change_24h_percent', 0):.2f}%
        7d Holder Change: {moralis_data.get('holder_analysis', {}).get('holder_change_7d', 0)}
        7d Holder Change Percentage: {moralis_data.get('holder_analysis', {}).get('holder_change_7d_percent', 0):.2f}%

        ## Token Distribution Risk
        Whale Count: {moralis_data.get('distribution', {}).get('whales_count', 0)}
        Top 10 Holders Supply Percentage: {moralis_data.get('distribution', {}).get('top10_supply_percent', 0):.2f}%
        Top 25 Holders Supply Percentage: {moralis_data.get('distribution', {}).get('top25_supply_percent', 0):.2f}%
        Concentration Risk: {concentration_risk}

        ## Risk Factors
        Volatility Level: {risk_factors.get('volatility_level', 'N/A')}
        RSI Overbought: {risk_factors.get('rsi_overbought', False)}
        RSI Oversold: {risk_factors.get('rsi_oversold', False)}
        Concentration Risk: {risk_factors.get('concentration_risk', False)}
        Holder Decline: {risk_factors.get('holder_decline', False)}
        Low Liquidity: {risk_factors.get('low_liquidity', False)}

        ## Trading Pool Information
        Active Pool Count: {len(pool_data)}
        """
        
        if pool_data:
            prompt += "\n### Pool Details:\n"
            for i, pool in enumerate(pool_data[:3]):  # Show only first 3 pools
                prompt += f"Pool {i+1} ({pool.get('dex', 'N/A')}): Price ${pool.get('price_usd', 0):.8f}, 24h Volume ${pool.get('volume_24h', 0):,.2f}, Liquidity ${pool.get('liquidity_usd', 0):,.2f}\n"
        
        if historical_data:
            prompt += f"\n## Historical Data\nTotal of {len(historical_data)} historical data points covering the past 30 days performance.\n"
        
        conclusion = ""
        if user_intent:
            conclusion = f"Please provide a short conclusion according to the user's intent: {user_intent}."
        else:
            conclusion = "Please provide a short conclusion for trading advice."

        prompt += f"""

        ## Analysis Requirements
        Please conduct in-depth analysis based on all the above data from the following aspects:
        
        **IMPORTANT: Please format your response using markdown with icons before each section title.**
        
        1. **🎯 Overall Conclusion**
           - {conclusion}

        2. **📊 Technical Analysis Summary**
           - RSI and moving average indicators interpretation
           - Price trend and breakout signal analysis
           - Volatility and technical pattern assessment

        3. **🏛️ Fundamental Analysis**
           - Trading volume and liquidity health
           - Market participation and activity level
           - Holder structure and stability

        4. **🌡️ Market Sentiment Analysis**
           - Buy/sell pressure comparison
           - Trader behavior patterns
           - Short-term and medium-term sentiment changes

        5. **⚠️ Risk Assessment**
           - Major risk factors identification
           - Risk level rating
           - Risk management recommendations

        6. **💰 Trading Recommendations**
           - Clear trading signals (STRONG BUY/BUY/WATCH/HOLD/SELL/STRONG SELL)
           - Suggested entry/exit price levels
           - Stop-loss and take-profit recommendations
           - Position size management suggestions

        7. **📝 Summary**
           - Overall score (1-10 scale)
           - Investment timeframe recommendations
           - Key monitoring indicators

        ## Data Sources & Last Update Time
        **📊 Data Sources:** This analysis is based on comprehensive data from multiple sources: {data_sources_str}
        
        **🕒 Latest Data Update:** {latest_update_time or 'N/A'}
        
        **📈 Data Completeness:** 
        - Token Metrics: {'✅ Available' if data_completeness.get('has_token_metrics') else '❌ Not Available'}
        - Technical Indicators: {'✅ Available' if data_completeness.get('has_technical_indicators') else '❌ Not Available'}
        - Moralis Analytics: {'✅ Available' if data_completeness.get('has_moralis_data') else '❌ Not Available'}
        - Historical Data: {'✅ Available' if data_completeness.get('has_historical_data') else '❌ Not Available'} ({len(historical_data)} records)
        - Pool Data: {'✅ Available' if data_completeness.get('has_pool_data') else '❌ Not Available'} ({len(pool_data)} pools)

        Please provide detailed and professional analysis using proper markdown formatting with icons, ensuring recommendations are based on data and logic.
        """
        
        return prompt
    
    def _fallback_analysis(self, decision_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback analysis when LLM call fails"""
        current_metrics = decision_data.get("current_metrics", {})
        technical_indicators = decision_data.get("technical_indicators", {})
        risk_factors = decision_data.get("risk_factors", {})
        
        # Simple rule-based analysis
        signal = "HOLD"
        reasoning = "Based on technical indicators analysis"
        
        rsi = technical_indicators.get("rsi_14d", 50)
        signal_strength = technical_indicators.get("signal_strength", 0.5)
        volatility_level = risk_factors.get("volatility_level", "MEDIUM")
        
        if signal_strength and signal_strength > 0.7 and rsi < 70:
            signal = "BUY"
            reasoning = "High signal strength and RSI not overbought"
        elif signal_strength and signal_strength < 0.3 or rsi > 80:
            signal = "SELL"
            reasoning = "Low signal strength or RSI overbought"
        elif rsi < 30:
            signal = "BUY"
            reasoning = "RSI oversold, potential rebound"
        
        return {
            "timestamp": datetime.now().isoformat(),
            "token_symbol": decision_data.get("token_info", {}).get("symbol", "N/A"),
            "llm_analysis": "LLM service unavailable, using rule-based analysis",
            "trading_signal": signal,
            "confidence_score": 5.0,
            "risk_level": volatility_level,
            "recommendation": {
                "action": signal,
                "reasoning": reasoning,
                "entry_price": current_metrics.get("weighted_price_usd"),
                "stop_loss": None,
                "take_profit": None,
                "position_size": "SMALL"
            },
            "fallback_mode": True
        }
    
    def get_prompt_for_identify_target_token(self, message: str, available_tokens: List[Dict[str, Any]])-> str:
        # Format available tokens for display
        token_list = [f"{token['symbol']} ({token['name']})" for token in available_tokens]
        token_display = ', '.join(token_list)
        
        prompt = f"""
            Analyze the user's message and determine which cryptocurrency token they are asking about.
            
            User message: "{message}"
            
            Available tokens in our database: {token_display}
            
            **IMPORTANT RULES:**
            1. If the token mentioned in the user message EXACTLY matches any token symbol in the available list, set "token_found" to true, and "token_symbol" to the exact token symbol from the list
            2. If the token is NOT found in the list, set "token_found" to false and look for similar tokens based on:
               - Similar spelling (e.g., "PEPE" vs "PEPE2", "BTC" vs "BTCC")
               - Similar names (e.g., "Bitcoin" vs "Bitcoin Cash", "Ethereum" vs "Ethereum Classic")
               - Common variations (e.g., "USDT" vs "USDC", "ETH" vs "WETH")
            3. Only include tokens that are actually in the available list in "similar_tokens"
            
            Please respond with a JSON object containing:
            - "token_found": true/false (whether you identified a specific token that exists in the available list)
            - "token_symbol": the exact token symbol from the available list (if found)
            - "similar_tokens": a list of token symbols from the available list that are similar to what the user mentioned (if not found or for additional suggestions)
            - "user_intent": "price_analysis", "signal_analysis", "general_analysis", or "trading_advice"
            - "confidence": confidence score from 0.0 to 1.0
            
            Examples:
            - User asks "What's the price of BTC?" and BTC is in the list -> {{"token_found": true, "token_symbol": "BTC", "similar_tokens": [], "user_intent": "price_analysis", "confidence": 0.9}}
            - User asks "Should I buy PEPE?" and PEPE is in the list -> {{"token_found": true, "token_symbol": "PEPE", "similar_tokens": [], "user_intent": "trading_advice", "confidence": 0.8}}
            - User asks "How is PEPE2 doing?" but only PEPE is in the list -> {{"token_found": false, "token_symbol": null, "similar_tokens": ["PEPE"], "user_intent": "price_analysis", "confidence": 0.7}}
            - User asks "Hello" -> {{"token_found": false, "token_symbol": null, "similar_tokens": [], "user_intent": "general", "confidence": 0.1}}
        """

        return prompt

    def get_sys_prompt_for_identify_target_token(self)-> str:
        return """You are a cryptocurrency analysis assistant specialized in token identification. 

Your task is to analyze user messages and identify which cryptocurrency token they are asking about by comparing against an available token list.

Key responsibilities:
1. Check if the mentioned token exists in the available token list
2. If found, return the exact token symbol from the list
3. If not found, suggest similar tokens from the available list
4. Determine user intent (price analysis, trading advice, etc.)
5. Provide confidence scores based on clarity of the request

Always be precise and only suggest tokens that actually exist in the provided list."""

    async def llm_identify_target_token(self, message: str, available_tokens: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Use LLM to identify which token the user is asking about"""
        try:
            # Create token list for LLM context
            # only include symbol and name, json format
            token_symbols = [{"symbol": token['symbol'], "name": token['name']} for token in available_tokens]
            
            user_prompt =  self.get_prompt_for_identify_target_token(message, token_symbols)
            
            response = await self.client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": self.get_sys_prompt_for_identify_target_token() },
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=300
            )
            
            content = response.choices[0].message.content
            
            # Extract JSON from response
            import json
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {"token_found": False, "token_symbol": None, "token_info": None, "user_intent": "general", "confidence": 0.0}
                
        except Exception as e:
            print(f"Error in LLM token identification: {e}")
            return {"token_found": False, "token_symbol": None, "token_info": None, "user_intent": "general", "confidence": 0.0}
    
    
    async def analyze_token_data_for_user_intent(self, decision_data: Dict[str, Any], user_intent: str) -> Dict[str, Any]:
        system_prompt = self._get_system_prompt()
        user_prompt = self._create_comprehensive_analysis_prompt(decision_data)

        response = await self.client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=2000
        )

        content = response.choices[0].message.content
        content = content.replace("```markdown", "").replace("```", "")
        print(f"LLM analysis response: \n {content}")

        return content

# Helper functions
async def analyze_token_with_llm(decision_data: Dict[str, Any], api_key: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function: analyze single token"""
    analyzer = TokenDecisionAnalyzer(api_key)
    return await analyzer.analyze_token_decision(decision_data)