import os
from typing import Dict, Any, Optional
from openai import AsyncOpenAI
from dotenv import load_dotenv
import json
import re

load_dotenv()

class OpenAIClient:
    """OpenAI client for LLM interactions"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.client = AsyncOpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY")
        )
    
    async def generate_signal(self, token: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate trading signal using OpenAI"""
        prompt = self._create_signal_prompt(token, metrics)
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a professional Web3 trading assistant. Analyze the given metrics and provide a clear trading signal with reasoning."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            return self._parse_signal_response(content)
            
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return self._fallback_signal(metrics)
    
    async def parse_chat_intent(self, message: str) -> Dict[str, Any]:
        """Parse user message to extract intent and token information"""
        prompt = f"""
        Parse the following user message and extract the intent and token information:
        
        Message: "{message}"
        
        Return a JSON object with:
        - intent: "token_analysis", "portfolio_check", "general_question", or "unknown"
        - token: extracted token symbol (if any)
        - action: "buy", "sell", "hold", "analyze", or null
        
        Examples:
        - "Should I buy $PEPE?" -> {{"intent": "token_analysis", "token": "PEPE", "action": "buy"}}
        - "What's the outlook on DOGE?" -> {{"intent": "token_analysis", "token": "DOGE", "action": "analyze"}}
        - "Hello" -> {{"intent": "general_question", "token": null, "action": null}}
        """
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=200
            )
            
            content = response.choices[0].message.content
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {"intent": "unknown", "token": None, "action": None}
                
        except Exception as e:
            print(f"Intent parsing error: {e}")
            return {"intent": "unknown", "token": None, "action": None}
    
    def _create_signal_prompt(self, token: str, metrics: Dict[str, Any]) -> str:
        """Create prompt for signal generation"""
        return f"""
        You are a Web3 trading assistant. Given the following token metrics, output a trading signal and explain why.

        Token: ${token}
        Price: ${metrics.get('current_price', 0):.6f}
        24H Volume: ${metrics.get('current_volume', 0):,.0f}
        RSI: {metrics.get('rsi', 50):.1f}
        MA7: ${metrics.get('ma_7d', 0):.6f}
        MA30: ${metrics.get('ma_30d', 0):.6f}
        Volume Delta: {metrics.get('volume_delta', 0):.1f}%
        Holder Delta: {metrics.get('holder_delta', 0):.1f}%
        Breakout: {metrics.get('breakout', False)}

        Based on these metrics, provide:
        1. Signal: One of (Strong Buy, Buy, Watch, Hold, Sell, Strong Sell)
        2. Reason: Explain your decision based on the technical indicators

        Format your response as:
        Signal: [YOUR_SIGNAL]
        Reason: [YOUR_EXPLANATION]
        """
    
    def _parse_signal_response(self, content: str) -> Dict[str, Any]:
        """Parse OpenAI response to extract signal and reason"""
        try:
            lines = content.strip().split('\n')
            signal = "Hold"
            reason = "Unable to determine signal from available data."
            
            for line in lines:
                if line.startswith("Signal:"):
                    signal = line.replace("Signal:", "").strip()
                elif line.startswith("Reason:"):
                    reason = line.replace("Reason:", "").strip()
            
            return {
                "signal": signal,
                "reason": reason
            }
        except Exception:
            return self._fallback_signal({})
    
    def _fallback_signal(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback signal generation when OpenAI fails"""
        rsi = metrics.get('rsi', 50)
        ma_7d = metrics.get('ma_7d', 0)
        ma_30d = metrics.get('ma_30d', 0)
        breakout = metrics.get('breakout', False)
        
        if breakout and rsi < 70:
            return {"signal": "Strong Buy", "reason": "Breakout detected with healthy RSI levels."}
        elif ma_7d > ma_30d and rsi < 60:
            return {"signal": "Buy", "reason": "Uptrend confirmed with MA7 > MA30 and RSI below overbought."}
        elif rsi > 75:
            return {"signal": "Sell", "reason": "RSI indicates overbought conditions."}
        elif rsi < 25:
            return {"signal": "Buy", "reason": "RSI indicates oversold conditions."}
        else:
            return {"signal": "Hold", "reason": "Mixed signals, no clear direction."} 