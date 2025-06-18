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
        
        # Calculate key ratios and trends
        buy_sell_ratio = moralis_data.get("volume_analysis", {}).get("buy_sell_ratio", 1)
        trader_ratio = moralis_data.get("trader_activity", {}).get("trader_ratio", 1)
        concentration_risk = moralis_data.get("distribution", {}).get("concentration_risk", "UNKNOWN")
        
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
        
        1. **Overall Conclusion**
           - {conclusion}

        2. **Technical Analysis Summary**
           - RSI and moving average indicators interpretation
           - Price trend and breakout signal analysis
           - Volatility and technical pattern assessment

        2. **Fundamental Analysis**
           - Trading volume and liquidity health
           - Market participation and activity level
           - Holder structure and stability

        3. **Market Sentiment Analysis**
           - Buy/sell pressure comparison
           - Trader behavior patterns
           - Short-term and medium-term sentiment changes

        4. **Risk Assessment**
           - Major risk factors identification
           - Risk level rating
           - Risk management recommendations

        5. **Trading Recommendations**
           - Clear trading signals (STRONG BUY/BUY/WATCH/HOLD/SELL/STRONG SELL)
           - Suggested entry/exit price levels
           - Stop-loss and take-profit recommendations
           - Position size management suggestions

        6. **Summary**
           - Overall score (1-10 scale)
           - Investment timeframe recommendations
           - Key monitoring indicators

        Please provide detailed and professional analysis, ensuring recommendations are based on data and logic.
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
    
    async def llm_identify_target_token(self, message: str, available_tokens: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Use LLM to identify which token the user is asking about"""
        try:
            # Create token list for LLM context
            token_symbols = [token['symbol'] for token in available_tokens]
            
            prompt = f"""
            Analyze the user's message and determine which cryptocurrency token they are asking about.
            
            User message: "{message}"
            
            Available tokens in our database: {', '.join(token_symbols)}
            
            Please respond with a JSON object containing:
            - "token_found": true/false (whether you identified a specific token)
            - "token_symbol": the token symbol (if found)
            - "user_intent": "price_analysis", "signal_analysis", "general_analysis", or "trading_advice"
            - "confidence": confidence score from 0.0 to 1.0
            
            Examples:
            - "What's the price of BTC?" -> {{"token_found": true, "token_symbol": "BTC", "token_info": "Bitcoin", "user_intent": "price_analysis", "confidence": 0.9}}
            - "Should I buy PEPE?" -> {{"token_found": true, "token_symbol": "PEPE", "token_info": "Pepe token", "user_intent": "trading_advice", "confidence": 0.8}}
            - "Hello" -> {{"token_found": false, "token_symbol": null, "token_info": null, "user_intent": "general", "confidence": 0.1}}
            """
            
            response = await self.client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": "You are a cryptocurrency analysis assistant. Analyze user messages to identify which token they're asking about."},
                    {"role": "user", "content": prompt}
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
        print(f"LLM analysis response: \n {content}")

        return content

# Helper functions
async def analyze_token_with_llm(decision_data: Dict[str, Any], api_key: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function: analyze single token"""
    analyzer = TokenDecisionAnalyzer(api_key)
    return await analyzer.analyze_token_decision(decision_data)