from datetime import datetime
import os
from openai import OpenAI
from core.trading import get_recent_tweets

# chinese or english
def generate_news_report(language: str = "chinese", days: int = 3, hours: int = 0):
    tweets, begin_time, end_time = get_recent_tweets(days=days, hours=hours)
    if len(tweets) == 0:
        return ""
    
    begin_time = datetime.strptime(begin_time, "%a %b %d %H:%M:%S %z %Y")
    end_time = datetime.strptime(end_time, "%a %b %d %H:%M:%S %z %Y")
    print(f"tweets: {len(tweets)} from {begin_time.strftime('%Y-%m-%d %H:%M:%S')} to {end_time.strftime('%Y-%m-%d %H:%M:%S')}")

    print(f"Latest tweet: {tweets[0][:100]}...")
    print(f"Oldest tweet: {tweets[-1][:100]}...")

    time_range = f"from {begin_time} to {end_time}"

    language = language.lower()
    # first letter uppercase
    language = language.capitalize()
    print(f"generate news report in {language}")

    prompt = f"""
    You are a Web3 (crypto, blockchain, NFTs, defi, meme, AI, etc.) industry analyst. Based on the following KOL recent tweets from the past 1-3 days:
    {tweets}

    Please analyze these tweets and generate a comprehensive industry report focused on the very latest developments (1-3 days). The report should follow this structure:

    # 🌐 Web3 & AI Daily Report 

    ---
    
    **📅 Analysis Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
    **📊 Data Range**: {len(tweets)} KOL tweets in {time_range}
    
    ---

    ## 📰 Brief
    * Summary of the latest news (1-3 days) in 150 words, highlighting the most significant developments in Web3 and AI
    * Include a confidence score (1-10) for major claims based on KOL consensus level

    ## 🔥 Hot Topics
    ### 1. 📈 Trending Topics
       * List of specific topics being discussed by KOLs in the last 1-3 days (focus on qualitative descriptions only)
       * Community discussions with engagement metrics (likes, retweets, replies)
       * Notable KOL(e.g. Vitalik, CZ, etc.) opinions and their context
       * Identify KOL credibility tiers (top-tier, mid-tier, emerging) when citing opinions
       * Avoid detailed price analysis here (only general sentiment)
    
    ### 2. ⚖️ Regulatory Updates
       * Very recent policy changes and announcements with jurisdictional context
       * Immediate impact analysis with short-term timeline of expected effects
       * KOL responses to regulatory developments
       * Comparative analysis with previous similar regulations

    ## 📊 Market Overview
    ### 1. 💹 Price Analysis
       * Key price movements in the last 1-3 days with exact percentages and detailed data
       * Volume and liquidity metrics with comparison to previous days
       * Notable trading patterns and anomalies
       * Short-term price predictions and technical analysis
       * MEME coins and their recent market movements
       * Correlation patterns between related assets
    
    ### 2. 🎯 Market Sentiment
       * KOL market predictions with rationale and track record context
       * Current risk indicators and metrics
       * Recent market structure changes
       * Distinguish between emotional reactions and data-driven analysis
       * Contrarian indicators and counter-narratives

    ## ⚡ Technical Frontier
    ### 1. 🔧 Technical Developments
       * Latest technology advancements and innovations with development stage indicators
       * Recent protocol-level improvements and features
       * Performance metrics and technical benchmarks
       * Focus on underlying technology, not project-specific updates
       * Technical bottlenecks and proposed solutions
    
    ### 2. 🛡️ Security & Infrastructure
       * Recent security incidents and analysis with estimated impact scope
       * Latest infrastructure improvements
       * Technical opinions from developers
       * Emerging security threats and preparedness
       * Notable GitHub activities and code updates from the past few days

    ## 🤖 AI & Web3 Convergence
    ### 1. 🔗 AI Integration in Web3
       * Latest AI applications in blockchain infrastructure
       * New AI-powered analytics and trading tools
       * Recent developments in on-chain AI models
       * KOL perspectives on AI's immediate impact on Web3
    
    ### 2. ⚙️ Technical Synergies
       * New breakthrough use cases combining AI and blockchain
       * Recently identified technical limitations and proposed solutions
       * Latest insights on data ownership and AI training
       * Recent decentralized machine learning developments

    ## 🚀 Project Updates
    ### 1. 📢 Major Announcements
       * Latest project launches and their business models
       * Recent protocol upgrades from a user/adoption perspective
       * New partnership details and business implications
       * Focus on immediate project timelines, adoption, and non-technical aspects
       * Latest user growth metrics and adoption indicators
    
    ### 2. 👥 Team & Community
       * Recent team changes and roles with background context
       * New community initiatives and engagement metrics
       * Latest roadmap updates with completion percentage estimates
       * Current community sentiment analysis
       * Active governance proposals and voting patterns

    ## ⚔️ Competitive Landscape
    ### 1. 🏆 Project Comparisons
       * Current competitor positioning for major projects
       * Latest feature and performance benchmarking
       * Recent market positioning shifts
       * Newly identified market niches and opportunities
    
    ### 2. 🤝 Industry Consolidation
       * Recent merger and acquisition activity
       * New strategic partnerships and alliances
       * Current market concentration metrics
       * Recent power shifts among key players

    ## 💰 Investment Opportunities
    ### 1. 🎲 Market Opportunities Matrix
       * Newly emerging trends with latest data and adoption metrics
       * Opportunity scoring: market size x time urgency x entry barriers
       * Immediate timeline of upcoming events with expected impact
       * Categorization by investment horizon (immediate/short/mid-term)
    
    ### 2. 💡 Strategic Insights
       * Latest KOL investment strategies
       * Short-term trend analysis based on current developments
       * Immediate risk mitigation approaches
       * Contrasting traditional finance perspectives
       * Fresh signals of paradigm shifts

    ## 📈 Adoption Analysis
    ### 1. 👨‍💻 User Growth Patterns
       * Latest user onboarding metrics by platform/project
       * Currently observed adoption barriers and emerging solutions
       * Recent regional adoption disparities
       * Current user retention indicators
    
    ### 2. 🏢 Institutional Engagement
       * Latest enterprise and institutional adoption updates
       * Recent traditional finance crossover activities
       * Current infrastructure readiness for institutional users
       * New regulatory compliance developments for institutional entry

    ---
    
    ## 🎯 Conclusion
    * Conclusion focusing on the most significant developments from the past 1-3 days (400 words)
    * Include an "immediate signals to watch" section for the next 72 hours
    * Provide weighted importance ranking of covered topics

    ### 🔮 Next 72 Hours Watch List
    * Key events and signals to monitor
    * Potential market catalysts
    * Important announcements expected

    ---
    
    > **📝 Disclaimer**: This report is based on KOL tweets analysis and should not be considered as financial advice.  
    > **🔄 Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

    Requirements:
    1. Each bullet point must include specific data, metrics, or direct quotes
    2. Attribute all opinions to specific KOLs (e.g., "According to Vitalik...")
    3. Include exact numbers and percentages where applicable
    4. Focus on actionable insights with evidence
    5. Maintain objective analysis
    6. Avoid redundancy across sections
    7. Use precise language and specific examples
    8. Include source attribution for major claims
    9. Use the most recent tweet date as report date
    10. Distinguish between verified facts, reasonable assumptions, and speculations
    11. Emphasize very recent developments rather than historical patterns
    12. Identify potential immediate inflection points for industry direction
    13. Output the entire report in {language} (keep coin names and specialized terms like eth, defi, NFTs, etc. in their original form) in Markdown format
    14. Use badges, emojis, and visual elements to make the report more engaging
    15. Add appropriate emoji icons for each section and subsection
    16. Use horizontal dividers (---) to separate major sections
    17. Include status badges and metadata in a visually appealing format

    Note: Ensure each section has quantitative data and specific examples rather than general statements. Focus heavily on the most recent 1-3 days of developments, with special emphasis on breaking news and emerging patterns. Make the markdown output visually appealing with proper formatting, icons, and structure.
    """

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))    
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


def generate_news_report_for_user(user_id: str, language: str = "chinese", days: int = 3, hours: int = 0):
    """Generate personalized news report based on user profile and interests using LLM for content filtering"""
    from core.common import load_user_profile
    
    # Load user profile
    user_profile = load_user_profile(user_id)
    
    if not user_profile:
        print(f"No user profile found for {user_id}, generating generic report")
        return ""
    
    # Get recent tweets
    tweets, begin_time, end_time = get_recent_tweets(days=days, hours=hours)
    if len(tweets) == 0:
        return ""
    
    begin_time_dt = datetime.strptime(begin_time, "%a %b %d %H:%M:%S %z %Y")
    end_time_dt = datetime.strptime(end_time, "%a %b %d %H:%M:%S %z %Y")
    print(f"tweets: {len(tweets)} from {begin_time_dt.strftime('%Y-%m-%d %H:%M:%S')} to {end_time_dt.strftime('%Y-%m-%d %H:%M:%S')}")

    # Prepare user profile information for LLM
    user_context = {
        "user_id": user_id,
        "profile": user_profile,
    }
    
    time_range = f"from {begin_time_dt} to {end_time_dt}"
    language = language.lower().capitalize()
    
    print(f"Total tweets to analyze: {len(tweets)}")
    print(f"User profile loaded: {'Yes' if user_profile else 'No'}")

    # Generate personalized prompt - let LLM do the filtering and analysis
    prompt = f"""
    You are an expert Web3 and crypto industry analyst. You have been provided with:
    
    1. **USER PROFILE DATA**: {user_context}
    2. **RAW KOL RECENT TWEETS**: {tweets}
    
    Your task is to:
    1. **ANALYZE** the user's profile, interests, and communication style from the provided data
    2. **INTELLIGENTLY FILTER** the tweets to identify content most relevant to this specific user
    3. **GENERATE** a comprehensive personalized report that matches the user's preferred communication style
    
    Based on the user profile, identify their:
    - Primary interests and focus areas
    - Technical sophistication level
    - Investment/trading style
    - Preferred content types
    - Risk tolerance and preferences
    - **Communication style and language preferences**
    - **Tone and expression habits (formal/casual, technical/simple, data-driven/narrative, etc.)**
    - **Cultural context and meme preferences**
    - **Preferred depth of analysis (brief/detailed)**
    
    **CRITICAL**: Analyze the user's communication patterns and adapt your writing style to match their preferences:
    - If user uses technical jargon → Use professional technical language
    - If user prefers casual tone → Write in a more relaxed, conversational style
    - If user is data-focused → Include more charts, numbers, and quantitative analysis
    - If user likes memes/humor → Include appropriate crypto memes and lighter tone where suitable
    - If user is risk-averse → Use cautious, balanced language
    - If user is aggressive trader → Use more direct, action-oriented language
    - If user prefers brief content → Keep sections concise
    - If user likes detailed analysis → Provide in-depth explanations
    
    Then analyze the tweets and create a highly personalized report that matches both the user's interests AND their preferred communication style:

    # 🌐 Personalized Web3 & AI Daily Report

    ---
    
    **📅 Analysis Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
    **📊 Data Range**: {len(tweets)} KOL tweets ({time_range})
    **👤 User ID**: {user_id}
    **🎯 Personalization Level**: AI-filtered based on user profile + communication style
    **🗣️ Writing Style**: Adapted to user's preferred communication patterns
    
    ---

    ## 👤 User Profile Summary
    * Key characteristics derived from user data analysis
    * Main interest areas and professional background
    * Content preferences and engagement style
    * Technical level and investment preferences
    * **Communication style and tone preferences**

    ## 📰 Personalized News Brief
    * Most important developments filtered for user interests (adapt length to user preference)
    * Only include content highly relevant to this user
    * Include confidence score (1-10) based on user matching degree
    * Explain why these news items matter to this specific user
    * **Written in the user's preferred style and tone**

    ## 🔥 User-Focused Hot Topics
    ### 1. 📈 Trending Topics in Your Interest Areas
       * Relevant discussions filtered based on user profile
       * Only include KOL opinions matching user interests
       * Community engagement data (adapt detail level to user preference)
       * Authoritative KOL viewpoints in user's focus areas
       * **Express using terminology and tone user prefers**
    
    ### 2. ⚖️ Regulatory Updates Affecting You
       * Only include policy changes that may impact user's focus areas
       * Direct impact analysis on user's investment/interest domains
       * Relevant KOL reactions and interpretations to these changes
       * **Frame analysis according to user's risk perspective and communication style**

    ## 📊 Personalized Market Analysis
    ### 1. 💹 Price Movements in Your Focus Areas
       * Only analyze asset price changes relevant to user interests
       * Specific data for tokens/projects user may follow
       * Short-term predictions tailored to user's risk preference
       * **Present data in format user prefers (detailed charts vs. simple summaries)**
    
    ### 2. 🎯 Market Sentiment in Your Investment Areas
       * Market sentiment analysis specifically for user's focus sectors
       * Risk indicators based on user's investment style
       * Contrarian indicators and signals user might find interesting
       * **Use language that matches user's trading style and risk tolerance**

    ## ⚡ Relevant Technology Frontiers
    ### 1. 🔧 Tech Developments You Care About
       * Only include developments matching user's tech level and interests
       * Protocol improvements and features user might care about
       * Performance metrics and test data suitable for user's tech background
       * **Explain in technical depth appropriate for user's sophistication level**
    
    ### 2. 🛡️ Relevant Security & Infrastructure
       * Security incidents affecting user's focus areas
       * Infrastructure improvements for platforms/protocols user uses
       * **Frame security discussions according to user's risk awareness level**

    ## 🤖 AI & Web3 Convergence (If Relevant)
    * Only include this section if user shows interest in AI/technology
    * Focus on AI+Web3 use cases user might actually apply
    * Relevant developments based on user's technical level
    * **Adapt technical complexity to user's AI knowledge level**

    ## 🚀 Project Updates You Might Care About
    ### 1. 📢 Relevant Project Major Announcements
       * Only include project launches and upgrades matching user interests
       * Partnership announcements user might participate in
       * User growth data for projects in user's focus sectors
       * **Present updates in format user prefers (brief bullets vs. detailed analysis)**

    ## 💰 Personalized Investment Opportunities
    ### 1. 🎲 Opportunity Matrix Suited for You
       * Emerging trends based on user's risk preference and interests
       * Opportunity scoring tailored to user's investment style
       * Upcoming events suited to user's time preferences
       * **Frame opportunities using user's preferred risk/reward language**
    
    ### 2. 💡 Strategic Insights Customized for Your Profile
       * Investment strategy recommendations based on user profile
       * Risk mitigation approaches suited to user's risk tolerance
       * Paradigm shift signals in user's focus sectors
       * **Provide advice in tone matching user's decision-making style**

    ## 📈 Relevant Adoption Analysis
    ### 1. 👨‍💻 User Growth in Your Interest Areas
       * Adoption metrics for platforms user might use
       * Adoption barriers and solutions in user's focus areas
       * **Present adoption data in format user finds most useful**
    
    ### 2. 🏢 Relevant Institutional Activity
       * Enterprise adoption affecting user's interest areas
       * Traditional finance activity in user's focus sectors
       * **Frame institutional news according to user's perspective on tradfi**

    ---
    
    ## 🎯 Personalized Conclusions & Recommendations
    * Summary of past 1-3 days key developments specifically for this user
    * Actionable insights based on user profile
    * Immediate attention signals customized for user
    * Suggested actions considering user's risk preference
    * **Written in user's preferred decision-making style and tone**

    ### 🔮 Your 72-Hour Watch List
    * Key events and signals to monitor based on user interests
    * Potential catalysts specifically affecting user's focus areas
    * Important announcements and events user should watch
    * **Prioritized according to user's attention span and detail preference**

    ### 📋 Personalized Action Items
    * Immediate action items (based on user preferences and capabilities)
    * Further research suggestions (suited to user's technical level)
    * Networking opportunities (based on user's engagement style)
    * **Phrased in language that matches user's action-orientation level**

    ---
    
    > **📝 Disclaimer**: This personalized report is based on user profile analysis and KOL tweet filtering, not financial advice.  
    > **🔄 Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    > **👤 Customized for User**: {user_id}
    > **🎨 Style**: Adapted to user's communication preferences

    ## 🔍 Filtering & Analysis Methodology
    * **Tweet Filtering Criteria**: Relevance scoring based on user profile
    * **Content Priority**: User interest matching > General importance
    * **Personalization Degree**: Highly customized content + communication style
    * **Style Adaptation**: Language, tone, and depth matched to user preferences
    * **Confidence Assessment**: Based on user characteristic matching and KOL authority

    **CRITICAL REQUIREMENTS**:
    1. **Smart Filtering**: Only include content highly relevant to user, ignore unrelated information
    2. **Deep Personalization**: Every section should target this specific user, avoid generic templates
    3. **User Profile Driven**: All analysis and recommendations based on user's actual characteristics and preferences
    4. **Style Matching**: Adapt writing style, tone, and complexity to match user's communication patterns
    5. **Cultural Sensitivity**: Consider user's cultural context and meme preferences
    6. **Appropriate Depth**: Match analysis depth to user's preference for brief vs. detailed content
    7. **Language Requirement**: Output entirely in **{language}** (keep professional terms in original form)
    8. **Tone Adaptation**: Match formality level, technical complexity, and humor to user's style
    9. **Risk Language**: Use risk-related language that matches user's risk tolerance and trading style
    10. **Actionability**: Provide recommendations in language and format user prefers for decision-making

    **STYLE ADAPTATION EXAMPLES**:
    - **Technical User**: "The protocol's TVL increased 15.7% due to yield optimization mechanisms"
    - **Casual User**: "More money flowing into this platform because better rewards"
    - **Meme Lover**: "Number go up! 🚀 Platform basically printing money for users"
    - **Conservative**: "Moderate growth observed with careful risk management recommended"
    - **Aggressive Trader**: "Strong momentum, consider position sizing for breakout"

    **IMPORTANT**: This is a 100% personalized report in both CONTENT and STYLE. Analyze the user's communication patterns from their profile and match your writing style accordingly. Make the user feel like this report was written specifically for them, not just filtered for them.

    **OUTPUT LANGUAGE**: Write the entire report in **{language}**, adapting the style and tone to match how this specific user prefers to communicate and receive information.
    """

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))    
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3 
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    #news = generate_news_report(days=1, hours=0)
    #print(news)
    default_user_id = "cz_binance"
    import sys
    if len(sys.argv) > 1:
        default_user_id = sys.argv[1]
    news = generate_news_report_for_user(user_id=default_user_id, days=1, hours=0)
    print(news)