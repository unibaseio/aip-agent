import os
import json
from datetime import datetime, timedelta
from openai import OpenAI
from core.common import load_usernames, load_user_tweets_within, order_tweets
from core.format import clean_text, filter_tweets
from core.generate_prompts import build_batches


def get_recent_tweets(days=3, hours=0, min_text_length=30):
    """Get recent tweets from KOLs for trading analysis"""
    recent_tweets = []
    finished_users, unfinished_users = load_usernames()
    
    for username in finished_users:
        tweets = load_user_tweets_within(username, days, hours)
        for t in tweets:
            text = clean_text(t["text"])
            # Keep shorter tweets as they might contain important signals
            if len(text) < min_text_length:
                continue
            recent_tweets.append(t)

    ordered_tweets = order_tweets(recent_tweets, reverse=True)
    filtered_tweets = filter_tweets(ordered_tweets, include_author=True)
    
    # Use larger token limit for comprehensive analysis
    batches = build_batches(filtered_tweets, max_tokens=80_000, max_batch=1)
    if len(batches) > 0 and len(batches[0]) > 0:
        return batches[0], ordered_tweets[-1]["createdAt"], ordered_tweets[0]["createdAt"]
    else:
        return [], "", ""


def extract_trading_signals(tweets, quick_mode=False):
    """Extract specific trading signals from tweets"""
    if len(tweets) == 0:
        return {}
    
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Adjust analysis scope based on mode
    if quick_mode:
        # For quick signals, analyze more tweets but focus on recent ones
        analysis_tweets = tweets[:20]  # Analyze top 20 recent tweets
        analysis_focus = "Focus on immediate trading opportunities and urgent signals from the most recent tweets."
    else:
        # For comprehensive analysis, use all tweets for detailed analysis
        analysis_tweets = tweets
        analysis_focus = "Provide detailed analysis of all signal types."
    
    signal_prompt = f"""
    You are an expert crypto trading signal analyst. Analyze the following KOL tweets to extract actionable trading signals and market intelligence.

    {analysis_focus}

    Tweets:
    {analysis_tweets}

    Extract and categorize the following trading signals in JSON format:

    {{
        "immediate_signals": [
            {{
                "signal_type": "bullish/bearish/neutral",
                "asset": "specific coin/token name",
                "kol_name": "username of the KOL",
                "confidence": "1-10 scale",
                "timeframe": "immediate/short/medium/long",
                "signal_strength": "weak/moderate/strong",
                "reasoning": "specific reason for the signal",
                "tweet_content": "relevant part of the tweet",
                "timestamp": "tweet timestamp"
            }}
        ],
        "price_predictions": [
            {{
                "asset": "coin/token name",
                "predicted_direction": "up/down/sideways",
                "target_price": "if mentioned",
                "timeframe": "prediction timeframe",
                "kol_credibility": "high/medium/low based on track record",
                "supporting_evidence": "technical/fundamental/sentiment"
            }}
        ],
        "market_events": [
            {{
                "event_type": "launch/partnership/regulation/technical_update",
                "asset_affected": "specific assets",
                "impact_assessment": "positive/negative/neutral",
                "timeline": "when the event occurs/occurred",
                "market_impact_score": "1-10"
            }}
        ],
        "sentiment_shifts": [
            {{
                "asset": "coin/token",
                "sentiment_change": "from X to Y",
                "catalyst": "what caused the change",
                "kol_consensus": "percentage of KOLs with similar sentiment",
                "contrarian_indicators": "any opposing views"
            }}
        ]
    }}
    """
    
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": signal_prompt}],
        temperature=0.1
    )
    
    try:
        return response.choices[0].message.content
    except:
        return {"error": "Failed to parse trading signals"}


def generate_trading_report(language: str = "chinese", use_signals: bool = False, use_quick_mode: bool = False, days: int = 3, hours: int = 0):
    """Generate comprehensive trading analysis report"""
    tweets, begin_time, end_time = get_recent_tweets(days, hours)
    if len(tweets) == 0:
        return "No recent tweets found for analysis."
    
   
    begin_time = datetime.strptime(begin_time, "%a %b %d %H:%M:%S %z %Y")
    end_time = datetime.strptime(end_time, "%a %b %d %H:%M:%S %z %Y")
    time_range = f"from {begin_time.strftime('%Y-%m-%d %H:%M:%S')} to {end_time.strftime('%Y-%m-%d %H:%M:%S')}"

    print(f"Generating trading report using {len(tweets)} tweets in {time_range}")
    print(f"Latest tweet: {tweets[0][:100]}...")
    print(f"Oldest tweet: {tweets[-1][:100]}...")

   
    language = language.lower()
    language = language.capitalize()
    
    # Extract quick trading signals first
    trading_signals = ""
    if use_signals:
        trading_signals = extract_trading_signals(tweets, quick_mode=use_quick_mode)
    
    # Main comprehensive analysis prompt
    prompt = f"""
    You are a professional crypto trading analyst specializing in KOL sentiment analysis and market signal detection. 
    Your goal is to help traders identify profitable opportunities from KOL tweets.

    Recent KOL tweets:
    {tweets}

    """

    if use_signals:
        prompt += f"""
        Trading signals extracted from the recent KOL tweets:
        {trading_signals}
        """

    prompt += f"""
    Generate a comprehensive trading analysis report.

    Structure the report as follows:

    # 📊 KOL Trading Signal Analysis Report
    
    ---
    
    **📅 Analysis Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
    **📈 Data Range**: {len(tweets)} KOL tweets in {time_range} 
    
    ---

    ## 🎯 Core Trading Signals

    ### ⚡ Immediate Trading Opportunities
    - **🔥 High Confidence Signals**: List 3-5 strongest trading signals
    - **⏰ Entry Timing**: Specific buy/sell recommendations
    - **⚠️ Risk Assessment**: Risk level for each signal
    - **🛑 Stop Loss Recommendations**: Specific stop loss settings

    ### 🔮 Price Prediction Summary
    - **📊 Short-term Predictions** (1-7 days): Price direction based on KOL consensus
    - **📈 Medium-term Predictions** (1-4 weeks): Technical and fundamental analysis
    - **🎯 Key Price Levels**: Support and resistance levels
    - **🚀 Catalyst Events**: Upcoming events that may affect prices

    ## 💎 Focus Assets

    ### 🔥 Hot Coin Analysis
    Detailed analysis for each frequently mentioned coin:
    - **💭 Current Sentiment**: Overall KOL attitude
    - **📊 Technical Indicators**: Technical analysis from tweets
    - **🔧 Fundamental Changes**: Latest project developments
    - **💰 Trading Recommendations**: Specific operational strategies

    ### ⚠️ Risk Warnings
    - **🚨 High-Risk Assets**: Coins requiring caution
    - **📉 Market Risks**: Overall market risk factors
    - **⚖️ Regulatory Risks**: Policy-related risks

    ## 👑 KOL Influence Analysis

    ### 🌟 Top KOL Opinions
    - **🔶 Vitalik Buterin**: Latest views and impact
    - **🟡 CZ (Binance)**: Exchange-related signals
    - **🚀 Elon Musk**: Market sentiment impact
    - **👥 Other Important KOLs**: Ranked by influence

    ### 🎭 Sentiment Indicators
    - **🎯 Overall Market Sentiment**: Bull/Bear/Sideways
    - **🔥 FOMO Index**: Panic buying level
    - **😰 FUD Index**: Panic selling level
    - **🤝 Consensus Level**: KOL opinion consistency

    ## 🔍 Deep Market Insights

    ### 💸 Capital Flow Analysis
    - **🌊 Hot Money Flow**: Preferred sectors for capital
    - **🐋 Institutional Movements**: Whale and institutional actions
    - **👥 Retail Sentiment**: Retail investor behavior

    ### 🌐 Macro Factors
    - **⚖️ Regulatory Dynamics**: Latest policy impacts
    - **⚡ Technical Development**: Blockchain technology progress
    - **🏗️ Market Structure**: Exchange and infrastructure changes

    ## 🎯 Immediate Action Recommendations

    ### 📅 Today's Trading Strategy
    1. **⚡ Execute Immediately**: Trades requiring immediate action
    2. **👀 Watch and Wait**: Signals needing further confirmation
    3. **📈 Long-term Positioning**: Quality projects suitable for DCA

    ### 📆 Key Events Next 7 Days
    - **🚀 Important Releases**: Project updates and launches
    - **🎪 Conference Events**: Events that may impact the market
    - **⚡ Technical Milestones**: Important technical nodes

    ## 🛡️ Risk Management

    ### 🎯 Risk Control Recommendations
    - **⚖️ Position Management**: Recommended position allocation
    - **🛑 Stop Loss Strategy**: Specific risk control methods
    - **💰 Capital Management**: Fund usage recommendations

    ### 🔄 Dynamic Adjustments
    - **📊 Signal Changes**: How to adjust strategy based on new information
    - **🌊 Market Changes**: Strategies for different market environments

    ---

    ## 📝 Summary and Outlook

    ### 🎯 Key Points
    - Most important 3-5 trading opportunities
    - Most critical risk points to watch
    - Next important market turning point

    ### 🔮 Market Outlook
    - **📊 Short-term**: Market direction prediction
    - **📈 Medium-term**: Trend judgment
    - **🚀 Long-term**: Investment recommendations

    ### 🕐 Next Action Items
    - Priority trades to execute today
    - Signals to monitor over next 24 hours
    - Key price levels to watch

    ---
    
    > **⚠️ Risk Disclaimer**: This report is for reference only and does not constitute investment advice. Investment involves risks, please be cautious.  
    > **🔄 Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
    > **📊 Signal Confidence**: Based on {len(tweets)} KOL tweets analysis

    Requirements:
    1. All analysis must be based on specific tweet content
    2. Provide specific data and metrics
    3. Cite information sources and KOL names
    4. Distinguish between confirmed information and speculation
    5. Provide actionable trading recommendations
    6. Emphasize the importance of risk management
    7. Use professional trading terminology
    8. Maintain objective and rational analysis
    9. Focus on actionable insights with evidence
    10. Output the entire report in {language} (keep coin names and specialized terms like eth, defi, NFTs, DOGE, etc. in their original form) in Markdown format
    11. Use badges, emojis, and visual elements to make the report more engaging
    12. Add appropriate emoji icons for each section and subsection
    13. Use horizontal dividers (---) to separate major sections
    14. Include status badges and metadata in a visually appealing format
    15. Make the trading recommendations clear and actionable with proper visual hierarchy
    """

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))    
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    return response.choices[0].message.content


def generate_quick_signals(language: str = "chinese", days: int = 0, hours: int = 6):
    """
    Generate quick trading signals for immediate action
    
    Args:
        language: Output language (chinese/english)
        days: Time range in days for analysis (default: 0 days)
        hours: Time range in hours for analysis (default: 6 hours for better signal quality)
    """
    # Use more data for better signal quality - 6 hours to 2 days depending on data availability
    tweets, begin_time, end_time = get_recent_tweets(days=days, hours=hours) 
    begin_time = datetime.strptime(begin_time, "%a %b %d %H:%M:%S %z %Y")
    end_time = datetime.strptime(end_time, "%a %b %d %H:%M:%S %z %Y")
    time_range = f"from {begin_time.strftime('%Y-%m-%d %H:%M:%S')} to {end_time.strftime('%Y-%m-%d %H:%M:%S')}"
    
    if len(tweets) == 0:
        return "No recent tweets for quick signal analysis."
    
    print(f"Quick signals analysis using {len(tweets)} tweets in {time_range}")
    print(f"Latest tweet: {tweets[0][:100]}...")
    print(f"Oldest tweet: {tweets[-1][:100]}...")

    # Extract signals with quick mode for more comprehensive analysis
    trading_signals = extract_trading_signals(tweets, quick_mode=True)

    language = language.lower()
    language = language.capitalize()

    prompt = f"""
    Based on the following trading signals extracted from the recent KOL tweets:
    {trading_signals}

    Generate a quick trading alert focused on immediate opportunities.

    Structure as follows:

    # ⚡ Quick Trading Signals
    
    **📅 Analysis Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
    **📊 Data**: {len(tweets)} KOL tweets in {time_range}  
    **⏱️ Validity**: Next 4-12 hours
    
    ---
    
    ## 🚨 Urgent Signals (1-4 Hours)
    - [Most time-sensitive signals with entry points and confidence levels]
    - [Mark urgency: 🔴 Critical | 🟡 Important | 🟢 Monitor]
    
    ## 📈 Buy Signals
    - [Specific buy recommendations with entry ranges and stop-loss]
    - [Confidence: ⭐⭐⭐ High | ⭐⭐ Medium | ⭐ Low]
    
    ## 📉 Sell Signals
    - [Specific sell recommendations with exit strategies]
    - [Timing: 🚨 Immediate | ⚠️ Soon | 👀 Watch]
    
    ## ⚠️ Key Risks
    - [Critical risks for next 24 hours]
    - [Risk level: 🔴 High | 🟠 Medium | 🟡 Low]
    
    ---
    
    ## 📊 Signal Summary
    - **Total Signals**: [Number] | **High Confidence**: [Number]
    - **Market Sentiment**: [Bull/Bear/Neutral] | **Trend**: [Direction]
    - **Top KOL**: [Most influential recent opinion]
    
    ## ⏰ Action Items
    - [ ] Execute high-confidence signals within 2 hours
    - [ ] Set stop losses for all new positions
    - [ ] Monitor key price levels and news
    
    ---
    
    > **⚠️ Warning**: High-risk signals for experienced traders only. Use proper risk management.  
    > **🔄 Next Update**: {(datetime.now() + timedelta(hours=6)).strftime('%Y-%m-%d %H:%M:%S')}

    Requirements:
    1. Keep each section concise with only essential information
    2. Include specific price levels and percentages where mentioned
    3. Provide clear reasoning for top 3-5 signals only
    4. Focus on actionable insights for next 4-12 hours
    5. Use visual indicators for urgency and confidence
    6. Include only the most critical risks and opportunities
    7. Prioritize brevity while maintaining professional quality
    8. Use horizontal dividers (---) to separate major sections
    9. Add appropriate emoji icons for each section and subsection
    10. Include status badges and metadata in a visually appealing format
    11. Output in {language} (keep coin names like eth, defi, NFTs, DOGE, BTC in original form) in Markdown format
    """
    
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )
    return response.choices[0].message.content


if __name__ == "__main__":
   print(generate_quick_signals(language="chinese", days=1, hours=2))

   exit()
   # test  generate_trading_report 
   print(generate_trading_report(language="chinese", use_signals=True, use_quick_mode=True, days=1, hours=12))
   
   exit()

   # Run tests first
   test_functionality()
    
   print("\n" + "="*50 + "\n")
    
   # Start interactive demo
   interactive_demo()