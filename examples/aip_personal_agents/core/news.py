import os
from openai import OpenAI
from core.common import load_usernames,load_user_tweets_within, order_tweets
from core.format import filter_tweets
from core.generate_prompts import build_batches


def get_recent_tweets():
    recent_tweets = []
    finished_users, unfinished_users = load_usernames()
    for username in finished_users:
        tweets = load_user_tweets_within(username, 7)
        if len(tweets) > 0:
            recent_tweets.extend(tweets)

    ordered_tweets = order_tweets(recent_tweets, reverse=True)
    filtered_tweets = filter_tweets(ordered_tweets, include_author=True)
    batches = build_batches(filtered_tweets, max_batch=1)
    if len(batches) > 0 and len(batches[0]) > 0:
        return batches[0]
    else:
        return []


def generate_news():
    tweets = get_recent_tweets()
    if len(tweets) == 0:
        return ""
    
    
    print(tweets[0])
    print(tweets[-1])
    print(f"tweets: {len(tweets)}")

    prompt = f"""
    You are a Web3 (crypto, blockchain, NFTs, defi, meme, AI, etc.) industry analyst. Based on the following KOL recent tweets:
    {tweets}

    Please analyze these tweets and generate a comprehensive industry report. The report should follow this structure:

    # Web3 Daily Report
    [Date: Use the most recent date from the tweets]

    ## Hot Topics
    1. Trending Topics
       * List of specific topics with quantitative data
       * Community discussions with engagement metrics
       * Notable KOL(e.g. Vitalik, CZ, etc.) opinions and their context
    
    2. Regulatory Updates
       * Recent policy changes and announcements
       * Impact analysis on the industry
       * KOL responses to regulatory developments

    ## Market Overview
    1. Price Analysis
       * Key price movements with exact percentages
       * Volume and liquidity metrics
       * Notable trading patterns
    
    2. Market Sentiment
       * KOL market predictions with rationale
       * Risk indicators and metrics
       * Market structure changes

    ## Technical Frontier
    1. Technical Developments
       * New protocol upgrades and features
       * Performance improvements with metrics
       * Developer tooling updates
    
    2. Security & Infrastructure
       * Security incidents and analysis
       * Infrastructure improvements
       * Technical opinions from developers

    ## Project Updates
    1. Major Announcements
       * New project launches with features
       * Protocol upgrades with metrics
       * Partnership details
    
    2. Team & Community
       * Team changes and roles
       * Community initiatives
       * Roadmap updates

    ## Investment Opportunities
    1. Market Opportunities
       * Emerging trends with data
       * Risk-reward analysis
       * Timeline of upcoming events
    
    2. Strategic Insights
       * KOL investment strategies
       * Long-term trend analysis
       * Risk mitigation approaches

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
    10. Output the entire report in Chinese

    Note: Ensure each section has quantitative data and specific examples rather than general statements.
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