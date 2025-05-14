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
    filtered_tweets = filter_tweets(ordered_tweets)
    batches = build_batches(filtered_tweets, max_batch=1)
    if len(batches) > 0 and len(batches[0]) > 0:
        return batches[0]
    else:
        return []


def generate_news():
    tweets = get_recent_tweets()
    if len(tweets) == 0:
        return ""

    prompt = f"""
    You are a Web3 industry analyst. Based on the following KOL tweets:
    {tweets}

    Please analyze these tweets and generate a comprehensive industry report. The report should follow this structure:

    # Web3 Weekly Report
    [Date: Use the most recent date from the tweets]

    ## Hot Topics
    - Specific topics and discussions trending among KOLs (include exact numbers and metrics)
    - Key community concerns and their context
    - Detailed analysis of emerging narratives with specific examples
    - Concrete regulatory developments and their potential impact
    - When mentioning opinions, attribute them to specific KOLs (e.g., "Vitalik认为...", "CZ指出...")

    ## Market Overview
    - Detailed market trends with specific price movements and percentages
    - Volume and liquidity changes with exact numbers
    - Market structure analysis with specific metrics
    - Specific risk factors with supporting data
    - Include market predictions from specific KOLs with their reasoning

    ## Technical Frontier
    - Specific technical breakthroughs with detailed explanations
    - Infrastructure improvements with concrete metrics
    - Security incidents and their technical details
    - Developer tool updates and their specific features
    - Technical opinions from key developers and researchers

    ## Project Updates
    - Major project announcements with specific details and timelines
    - New protocol launches with their key features and metrics
    - Partnership details with specific collaboration scopes
    - Team changes with specific roles and responsibilities
    - Project team's specific comments and future plans

    ## Investment Opportunities
    - Specific market opportunities with supporting data
    - Detailed risk analysis with concrete examples
    - Long-term trends with specific indicators
    - Upcoming events with exact dates and expected impact
    - Investment insights from specific KOLs and their rationale

    Please ensure:
    1. Focus on insights from KOL perspectives with specific quotes and attributions
    2. Highlight consensus and diverging opinions with supporting evidence
    3. Include exact numbers, percentages, and specific metrics
    4. Prioritize actionable insights with concrete examples
    5. Maintain objectivity in analysis with balanced viewpoints
    6. Avoid content repetition across sections
    7. Use precise and specific language, avoid vague terms
    8. Attribute opinions to specific KOLs when possible
    9. Use the most recent date from the tweets as the report date
    10. Output the entire report in Chinese
    """

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    news = generate_news()
    print(news)