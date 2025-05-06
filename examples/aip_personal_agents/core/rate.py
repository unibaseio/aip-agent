from dataclasses import dataclass
from datetime import datetime
import sys
from openai import OpenAI
import os
import json

from core.format import filter_tweets, load_tweets_within, load_tweets, order_tweets
from core.generate_prompts import build_batches

def estimate_tweet_quality_llm(tweets):
    """Calculate quality scores for a batch of tweets using LLM (0-25)"""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    prompt = f"""You are a tweet quality analyzer. Your task is to evaluate the overall quality of this collection of tweets and provide scores for each aspect.

Evaluate these aspects for the entire collection:
1. Content Quality (0-10)
   - Overall originality and uniqueness of the content
   - Collective information value
   - Topic consistency and relevance
   - Clarity of messages across tweets

2. Language & Grammar (0-3)
   - Overall writing quality
   - Consistent writing style
   - Appropriate tone throughout

3. Professionalism (0-7)
   - Professional tone across tweets
   - Content appropriateness
   - Brand consistency
   - Effective media usage

4. Value to Readers (0-5)
   - Overall educational value
   - Entertainment value
   - Actionable insights
   - Community engagement potential

Tweets to analyze:
{json.dumps(tweets, indent=2)}

Provide your analysis in this exact JSON format:
{{
    "total_score": <number between 0-25>,
    "sub_scores": {{
        "content_quality": <number between 0-10>,
        "language_grammar": <number between 0-3>,
        "professionalism": <number between 0-7>,
        "value_to_readers": <number between 0-5>
    }},
    "explanation": "<brief explanation of the overall score>"
}}

Important:
- All scores must be numbers within their specified ranges
- Total score should equal the sum of all sub-scores
- Provide a brief explanation for the overall score
- Ensure the response is valid JSON"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        print(f"Error in LLM quality scoring: {str(e)}")
        return {
            "total_score": 0,
            "sub_scores": {
                "content_quality": 0,
                "language_grammar": 0,
                "professionalism": 0,
                "value_to_readers": 0
            },
            "explanation": "Error occurred during scoring"
        }

def estimate_influence_llm(tweets):
    """Calculate influence and engagement scores for a batch of tweets using LLM (0-25 each)"""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    prompt = f"""You are a social media influence analyzer. Your task is to evaluate the influence and engagement of this collection of tweets.

Evaluate these aspects for the entire collection:
1. Influence Score (0-25)
   - Overall reach and visibility
   - Impact of content
   - Audience size and quality
   - Content virality potential
   - Brand authority

2. Engagement Score (0-25)
   - Community interaction level
   - Response quality
   - Discussion generation
   - User participation
   - Content resonance

Tweets to analyze:
{json.dumps(tweets, indent=2)}

Provide your analysis in this exact JSON format:
{{
    "influence_score": <number between 0-25>,
    "engagement_score": <number between 0-25>,
    "explanation": "<brief explanation of both scores>"
}}

Important:
- All scores must be numbers within their specified ranges
- Provide a brief explanation for both scores
- Ensure the response is valid JSON"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        print(f"Error in LLM influence scoring: {str(e)}")
        return {
            "influence_score": 0,
            "engagement_score": 0,
            "explanation": "Error occurred during scoring"
        }

def estimate_tweets(user_name):
    recent_tweets = load_tweets_within(user_name, 90)
    
    if not recent_tweets or len(recent_tweets) == 0:
        return {
            "engagement_score": 0,
            "influence_score": 0,
            "project_score": 0,
            "quality_score": 0,
            "total_score": 0
        }
    
    # statistics
    total_retweets = sum(tweet["retweetCount"] for tweet in recent_tweets)
    total_replies = sum(tweet["replyCount"] for tweet in recent_tweets)
    total_likes = sum(tweet["likeCount"] for tweet in recent_tweets)
    total_views = sum(tweet.get("viewCount", 0) for tweet in recent_tweets)
    total_quotes = sum(tweet.get("quoteCount", 0) for tweet in recent_tweets)
    tweet_count = len(recent_tweets)
    
    # Calculate tweet quality score (0-25)
    quality_score = 0
    influence_score = 0
    engagement_score = 0

    ordered_tweets = order_tweets(recent_tweets, reverse=True)
    filtered_tweets = filter_tweets(ordered_tweets)
    batches = build_batches(filtered_tweets)
    if len(batches) > 0:
        quality_scores = estimate_tweet_quality_llm(batches[0])
        print(quality_scores)
        quality_score = quality_scores["total_score"]

        result = estimate_influence_llm(batches[0])
        print(result)
        influence_score = result["influence_score"]
        engagement_score = result["engagement_score"]

    else:
        # Calculate influence score (0-25)
        # Based on likes, retweets and views
        avg_likes = total_likes / tweet_count
        avg_retweets = total_retweets / tweet_count
        avg_views = total_views / tweet_count
    
    
        if avg_likes > 1000:
            influence_score += 10
        elif avg_likes > 500:
            influence_score += 7
        elif avg_likes > 100:
            influence_score += 5
        elif avg_likes > 50:
            influence_score += 3
    
        if avg_retweets > 500:
            influence_score += 10
        elif avg_retweets > 200:
            influence_score += 7
        elif avg_retweets > 50:
            influence_score += 5
        elif avg_retweets > 20:
            influence_score += 3
    
        if avg_views > 10000:
            influence_score += 5
        elif avg_views > 5000:
            influence_score += 3
        elif avg_views > 1000:
            influence_score += 2
        elif avg_views > 500:
            influence_score += 1
    
        # Calculate engagement score (0-25)
        # Based on quotes and replies
        avg_quotes = total_quotes / tweet_count
        avg_replies = total_replies / tweet_count
    
    
        if avg_quotes > 100:
            engagement_score += 15
        elif avg_quotes > 50:
            engagement_score += 10
        elif avg_quotes > 20:
            engagement_score += 7
        elif avg_quotes > 10:
            engagement_score += 5
    
        if avg_replies > 50:
            engagement_score += 10
        elif avg_replies > 20:
            engagement_score += 7
        elif avg_replies > 10:
            engagement_score += 5
        elif avg_replies > 5:
            engagement_score += 3
    
    # Calculate project participation score (0-25)
    # Based on interactions with dedicated users
    mention_count = 0
    retweet_count = 0
    reply_count = 0
    dedicated_users = {"beeperfun", "beeper_agent"}
    
    for tweet in recent_tweets:
        if tweet.get("inReplyToUsername"):
            replied_user = tweet.get("inReplyToUsername")
            for username in dedicated_users:
                if username == replied_user:
                    reply_count += 1
                    break
        if tweet.get("quoted_tweet"):
            quoted_user = tweet["quoted_tweet"].get("author", {}).get("userName", "unknown")
            for username in dedicated_users:
                if username == quoted_user:
                    retweet_count += 1
                    break
        text = tweet["text"]
        for username in dedicated_users:
            username = "@" + username
            if username in text:
                mention_count += 1
                break
    
    project_score = 0
    if mention_count > 10:
        project_score += 10
    elif mention_count > 5:
        project_score += 7
    elif mention_count > 3:
        project_score += 5
    elif mention_count > 1:
        project_score += 3
    
    if retweet_count > 5:
        project_score += 8
    elif retweet_count > 3:
        project_score += 5
    elif retweet_count > 1:
        project_score += 3
    
    if reply_count > 5:
        project_score += 7
    elif reply_count > 3:
        project_score += 5
    elif reply_count > 1:
        project_score += 3
    
    total_score = engagement_score + influence_score + project_score + quality_score

    return {
        "engagement_score": round(engagement_score, 2),
        "influence_score": round(influence_score, 2),
        "project_score": round(project_score, 2),
        "quality_score": round(quality_score, 2),
        "total_score": round(total_score, 2)
    }


def real_factor(user_name):
    tweets = load_tweets(user_name)
    if not tweets or len(tweets) == 0:
        return 0
    
    tweet_count = len(tweets)
    user_info = tweets[-1].get("author", {})
    if user_info["isBlueVerified"] == True:
        print(f"{user_name} is blue verified")
        return 1
    if int(user_info["followers"]) > 10000:
        print(f"{user_name} has followes: {user_info['followers']}")
        return 1
    
    create_at = datetime.strptime(user_info["createdAt"], "%a %b %d %H:%M:%S %z %Y")
    # Calculate register duration: now-create_at
    now = datetime.now().astimezone()
    duration = now - create_at
    days = duration.days
    print(f"{user_name} register duration: {days} days")
    
    # Calculate authenticity factor
    factor = 0.05
    
    # Score based on registration duration
    if days > 365*5:
        factor += 0.4
    elif days > 365 * 2:  
        factor += 0.25
    elif days > 365:  
        factor += 0.15
    
    # Score based on total tweets
    if tweet_count > 1000:
        factor += 0.55
    elif tweet_count > 500:
        factor += 0.4
    elif tweet_count > 200:
        factor += 0.3
    elif tweet_count > 100:
        factor += 0.2
    elif tweet_count > 50:
        factor += 0.1
    
    print(f"{user_name} real factor: {factor}")
    return factor

def estimate(user_name):
    scores = estimate_tweets(user_name)
    print(scores)
    fac = real_factor(user_name)
    print(fac)
    scores["factor"] = fac
    scores["total_score"] = round(scores["total_score"]*fac,2)

    print(f"Score {user_name} is {scores}")

    # Create outputs directory if it doesn't exist
    os.makedirs("outputs", exist_ok=True)
    
    # Convert dictionary to JSON string before writing
    with open(f"outputs/{user_name}_airdrop_score.json", "w", encoding='utf-8') as f:
        json.dump(scores, f, indent=2)

if __name__ == "__main__":
    default_x_name = "cz_binance"
    args = sys.argv[1:]
    if len(args) > 0:
        default_x_name = args[0] 
    estimate(default_x_name)