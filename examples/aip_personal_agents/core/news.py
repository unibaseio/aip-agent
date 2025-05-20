import os
from openai import OpenAI
from core.common import load_usernames,load_user_tweets_within, order_tweets
from core.format import clean_text, filter_tweets
from core.generate_prompts import build_batches


def get_recent_tweets():
    recent_tweets = []
    finished_users, unfinished_users = load_usernames()
    for username in finished_users:
        tweets = load_user_tweets_within(username, 7)
        for t in tweets:
            text = clean_text(t["text"])
            if len(text) < 30:
                continue
            recent_tweets.append(t)

    ordered_tweets = order_tweets(recent_tweets, reverse=True)
    filtered_tweets = filter_tweets(ordered_tweets, include_author=True)
    batches = build_batches(filtered_tweets, max_tokens=60_000, max_batch=1)
    if len(batches) > 0 and len(batches[0]) > 0:
        return batches[0]
    else:
        return []


# chinese or english
def generate_news(language: str = "chinese"):
    tweets = get_recent_tweets()
    if len(tweets) == 0:
        return ""
    
    print(tweets[0])
    print(tweets[-1])
    print(f"tweets: {len(tweets)}")

    language = language.lower()
    # first letter uppercase
    language = language.capitalize()
    print(f"generate news report in {language}")

    prompt = f"""
    You are a Web3 (crypto, blockchain, NFTs, defi, meme, AI, etc.) industry analyst. Based on the following KOL recent tweets from the past 1-3 days:
    {tweets}

    Please analyze these tweets and generate a comprehensive industry report focused on the very latest developments (1-3 days). The report should follow this structure:

    # Web3 & AI Daily Report
    [Date: Use the most recent date from the tweets]

    ## Brief
    * Summary of the latest news (1-3 days) in 150 words, highlighting the most significant developments in Web3 and AI
    * Include a confidence score (1-10) for major claims based on KOL consensus level

    ## Hot Topics
    1. Trending Topics
       * List of specific topics being discussed by KOLs in the last 1-3 days (focus on qualitative descriptions only)
       * Community discussions with engagement metrics (likes, retweets, replies)
       * Notable KOL(e.g. Vitalik, CZ, etc.) opinions and their context
       * Identify KOL credibility tiers (top-tier, mid-tier, emerging) when citing opinions
       * Avoid detailed price analysis here (only general sentiment)
    
    2. Regulatory Updates
       * Very recent policy changes and announcements with jurisdictional context
       * Immediate impact analysis with short-term timeline of expected effects
       * KOL responses to regulatory developments
       * Comparative analysis with previous similar regulations

    ## Market Overview
    1. Price Analysis
       * Key price movements in the last 1-3 days with exact percentages and detailed data
       * Volume and liquidity metrics with comparison to previous days
       * Notable trading patterns and anomalies
       * Short-term price predictions and technical analysis
       * MEME coins and their recent market movements
       * Correlation patterns between related assets
    
    2. Market Sentiment
       * KOL market predictions with rationale and track record context
       * Current risk indicators and metrics
       * Recent market structure changes
       * Distinguish between emotional reactions and data-driven analysis
       * Contrarian indicators and counter-narratives

    ## Technical Frontier
    1. Technical Developments
       * Latest technology advancements and innovations with development stage indicators
       * Recent protocol-level improvements and features
       * Performance metrics and technical benchmarks
       * Focus on underlying technology, not project-specific updates
       * Technical bottlenecks and proposed solutions
    
    2. Security & Infrastructure
       * Recent security incidents and analysis with estimated impact scope
       * Latest infrastructure improvements
       * Technical opinions from developers
       * Emerging security threats and preparedness
       * Notable GitHub activities and code updates from the past few days

    ## AI & Web3 Convergence
    1. AI Integration in Web3
       * Latest AI applications in blockchain infrastructure
       * New AI-powered analytics and trading tools
       * Recent developments in on-chain AI models
       * KOL perspectives on AI's immediate impact on Web3
    
    2. Technical Synergies
       * New breakthrough use cases combining AI and blockchain
       * Recently identified technical limitations and proposed solutions
       * Latest insights on data ownership and AI training
       * Recent decentralized machine learning developments

    ## Project Updates
    1. Major Announcements
       * Latest project launches and their business models
       * Recent protocol upgrades from a user/adoption perspective
       * New partnership details and business implications
       * Focus on immediate project timelines, adoption, and non-technical aspects
       * Latest user growth metrics and adoption indicators
    
    2. Team & Community
       * Recent team changes and roles with background context
       * New community initiatives and engagement metrics
       * Latest roadmap updates with completion percentage estimates
       * Current community sentiment analysis
       * Active governance proposals and voting patterns

    ## Competitive Landscape
    1. Project Comparisons
       * Current competitor positioning for major projects
       * Latest feature and performance benchmarking
       * Recent market positioning shifts
       * Newly identified market niches and opportunities
    
    2. Industry Consolidation
       * Recent merger and acquisition activity
       * New strategic partnerships and alliances
       * Current market concentration metrics
       * Recent power shifts among key players

    ## Investment Opportunities
    1. Market Opportunities Matrix
       * Newly emerging trends with latest data and adoption metrics
       * Opportunity scoring: market size x time urgency x entry barriers
       * Immediate timeline of upcoming events with expected impact
       * Categorization by investment horizon (immediate/short/mid-term)
    
    2. Strategic Insights
       * Latest KOL investment strategies
       * Short-term trend analysis based on current developments
       * Immediate risk mitigation approaches
       * Contrasting traditional finance perspectives
       * Fresh signals of paradigm shifts

    ## Adoption Analysis
    1. User Growth Patterns
       * Latest user onboarding metrics by platform/project
       * Currently observed adoption barriers and emerging solutions
       * Recent regional adoption disparities
       * Current user retention indicators
    
    2. Institutional Engagement
       * Latest enterprise and institutional adoption updates
       * Recent traditional finance crossover activities
       * Current infrastructure readiness for institutional users
       * New regulatory compliance developments for institutional entry

    ## Conclusion
    * Conclusion focusing on the most significant developments from the past 1-3 days (400 words)
    * Include an "immediate signals to watch" section for the next 72 hours
    * Provide weighted importance ranking of covered topics

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

    Note: Ensure each section has quantitative data and specific examples rather than general statements. Focus heavily on the most recent 1-3 days of developments, with special emphasis on breaking news and emerging patterns.
    """

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))    
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    news = generate_news()
    print(news)