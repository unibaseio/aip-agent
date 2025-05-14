from datetime import datetime
import sys
from openai import OpenAI
import os
import json

from core.format import filter_tweets
from core.generate_prompts import build_batches
from core.common import write_user_airdrop_score, load_user_tweets_within, order_tweets

def estimate_by_llm(tweets: list, userinfo: dict, project_accounts: list):
    """Calculate quality, influence, engagement and authenticity scores for a batch of tweets using LLM"""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    try:
        userinfo_json = json.dumps(userinfo, indent=2)
        project_accounts_json = json.dumps(project_accounts, indent=2)
        tweets_json = json.dumps(tweets, indent=2)
        print(f"Input data serialization check:")
        print(f"userinfo length: {len(userinfo_json)}")
        print(f"project_accounts length: {len(project_accounts_json)}")
        print(f"tweets length: {len(tweets_json)}")
    except Exception as e:
        print(f"Error serializing input data: {str(e)}")
        raise e
    
    prompt = f"""You are a professional social media analyst specializing in Twitter/X platform analysis. Your task is to evaluate a user's Twitter activity and provide comprehensive scoring across multiple dimensions.

Input Data:
1. User Profile Information:
{userinfo_json}

2. Target Project Accounts (These are the official project accounts that we want to evaluate user's interaction with):
{project_accounts_json}

3. User's Tweets Collection:
{tweets_json}

Evaluation Criteria:

1. Quality Score (0-25)
   A. Content Quality (0-12)
      - Originality and uniqueness of content
      - Information value and depth
      - Topic consistency and relevance
      - Message clarity and effectiveness
      - Tweet quantity and consistency:
        * 0-2 points: < 10 tweets
        * 2-4 points: 10-30 tweets
        * 4-7 points: 30-60 tweets
        * 7-10 points: 60-100 tweets
        * 10-12 points: > 100 tweets

   B. Language & Grammar (0-3)
      - Writing quality and style
      - Language consistency
      - Tone appropriateness

   C. Professionalism (0-5)
      - Professional tone and presentation
      - Content appropriateness
      - Brand consistency
      - Media usage effectiveness

   D. Value to Readers (0-5)
      - Educational content value
      - Entertainment value
      - Actionable insights
      - Community engagement potential

2. Influence Score (0-25)
   Evaluation Factors:
   - Engagement metrics (likes, retweets, quotes, replies)
   - Content reach and visibility
   - Audience interaction quality
   - Viral potential
   - Tweet consistency
   - Account verification status
   - Follower metrics

   Scoring Guidelines:
   * 0-3: Very poor engagement 
      - < 10 interactions/tweet
      - < 10 tweets
      - Inconsistent posting
      - Low follower count
   
   * 4-8: Poor engagement
      - 10-50 interactions/tweet
      - 10-30 tweets
      - Irregular posting
      - Moderate followers
   
   * 9-13: Average engagement
      - 50-100 interactions/tweet
      - 30-60 tweets
      - Regular posting
      - Good follower count
   
   * 14-20: Good engagement
      - 100-500 interactions/tweet
      - 60-100 tweets
      - Consistent posting
      - High follower count
   
   * 21-25: Excellent engagement
      - >500 interactions/tweet
      - >100 tweets
      - Very consistent posting
      - Verified with large following

3. Engagement Score (0-25)
   Evaluation Factors:
   - Conversation quality and depth
   - Community building effectiveness
   - Content relevance
   - Interaction patterns
   - Posting consistency
   - Account history

   Scoring Guidelines:
   * 0-3: Very poor engagement
      - One-way communication
      - < 10 tweets
      - No posting pattern
      - New account
   
   * 4-8: Poor engagement
      - Limited interactions
      - 10-30 tweets
      - Irregular posting
      - Young account
   
   * 9-13: Average engagement
      - Moderate interactions
      - 30-60 tweets
      - Regular posting
      - Established account
   
   * 14-20: Good engagement
      - Active participation
      - 60-100 tweets
      - Consistent posting
      - Long-standing account
   
   * 21-25: Excellent engagement
      - Exceptional community building
      - >100 tweets
      - Very consistent posting
      - Veteran account

4. Authenticity Score (0-1)
   A. Content Authenticity (0-0.4)
      - Original vs reposted content
      - Personal experiences
      - Natural language patterns
      - Topic consistency
      - Account verification
      - Account history

   B. Engagement Patterns (0-0.2)
      - Natural interactions
      - Conversation flow
      - Response quality
      - Follower ratio
      - Growth patterns

   C. Account Behavior (0-0.4)
      - Posting patterns
      - Content diversity
      - Spam indicators
      - Verification status
      - Account history
      - Profile completeness
    
5. Project Score (0-25)
   Focus: Evaluate ONLY the user's interaction with and relevance to target project accounts
   - Direct interactions with target project accounts:
     * Mentions of target project accounts
     * Replies to target project accounts' tweets
     * Retweets/quotes of target project accounts' tweets
   - Content relevance to target project:
     * Project-related discussions
     * Project-specific terminology usage
     * Project topic consistency

   Scoring Guidelines:
   * 0-8: Low project relevance
      - Few or no direct interactions with target project accounts
      - Minimal project-related content
      - No consistent project discussion
   
   * 9-16: Medium project relevance
      - Regular direct interactions with target project accounts
      - Some project-related content
      - Basic project discussion consistency
   
   * 17-25: High project relevance
      - Frequent and meaningful direct interactions with target project accounts
      - Rich project-related content
      - Strong project discussion consistency

Output Format:
Provide your analysis in this exact JSON format:
{{
    "quality_score": <number between 0-25>,
    "quality_sub_scores": {{
        "content_quality": <number between 0-12>,
        "language_grammar": <number between 0-3>,
        "professionalism": <number between 0-5>,
        "value_to_readers": <number between 0-5>
    }},
    "influence_score": <number between 0-25>,
    "engagement_score": <number between 0-25>,
    "project_score": <number between 0-25>,
    "authenticity_score": <number between 0-1>,
    "authenticity_sub_scores": {{
        "content_authenticity": <number between 0-0.4>,
        "engagement_patterns": <number between 0-0.3>,
        "account_behavior": <number between 0-0.3>
    }},
    "explanation": "<brief explanation of all scores>"
}}

Important Guidelines:
- All scores must be numbers within their specified ranges
- Use precise decimal points (e.g., 12.37, 8.92, 0.14) for more accurate evaluation
- Consider all metrics holistically
- Be generous with high scores (14-25) for good accounts
- Be strict with low scores (0-8) for poor accounts
- Consider both quality and quantity
- Account for age, verification, and follower count
- Provide clear score explanations
- Ensure valid JSON output
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error in LLM scoring: {str(e)}")
        raise e

def estimate_legacy(recent_tweets, dedicated_accounts):
    # statistics
    total_retweets = sum(tweet["retweetCount"] for tweet in recent_tweets)
    total_replies = sum(tweet["replyCount"] for tweet in recent_tweets)
    total_likes = sum(tweet["likeCount"] for tweet in recent_tweets)
    total_quotes = sum(tweet.get("quoteCount", 0) for tweet in recent_tweets)
    tweet_count = len(recent_tweets)

    # Get user info from the most recent tweet
    user_info = recent_tweets[-1].get("author", {})
    
    # Calculate authenticity factor
    authenticity_factor = 1.0
    if user_info.get("isBlueVerified", False):
        print(f"User is blue verified")
        authenticity_factor = 1.0
    elif int(user_info.get("followers", 0)) > 10000:
        print(f"User has followers: {user_info['followers']}")
        authenticity_factor = 1.0
    else:
        # Calculate register duration
        create_at = datetime.strptime(user_info["createdAt"], "%a %b %d %H:%M:%S %z %Y")
        now = datetime.now().astimezone()
        duration = now - create_at
        days = duration.days
        print(f"User register duration: {days} days")
        
        # Calculate authenticity factor based on registration duration
        factor = 0.05
        if days > 365*3:
            factor += 0.35
        elif days > 365 * 2:  
            factor += 0.25
        elif days > 365:  
            factor += 0.15
        elif days > 180:
            factor += 0.05

        # Add points based on total tweets
        if tweet_count > 500:
            factor += 0.6
        elif tweet_count > 200:
            factor += 0.45
        elif tweet_count > 100:
            factor += 0.3
        elif tweet_count > 50:
            factor += 0.2
        elif tweet_count > 20:
            factor += 0.1
        elif tweet_count > 10:
            factor += 0.05
        
        authenticity_factor = factor
        print(f"User authenticity factor: {factor}")

    # Initialize scores
    influence_score = 0
    engagement_score = 0
    project_score = 0
    quality_score = 0

    # Calculate influence score (0-25)
    # Based on likes, retweets and views
    avg_interaction = (total_likes + total_retweets + total_quotes) / tweet_count

    if avg_interaction > 1000:
        influence_score += 25
    elif avg_interaction > 500:
        influence_score += 20
    elif avg_interaction > 100:
        influence_score += 15
    elif avg_interaction > 50:
        influence_score += 10
    elif avg_interaction > 10:
        influence_score += 5
    elif avg_interaction > 3:
        influence_score += 2

    # Calculate project participation score (0-25)
    # Based on interactions with dedicated users
    mention_count = 0
    retweet_count = 0
    reply_count = 0

    engagement_count = 0
    for tweet in recent_tweets:
        if tweet.get("quoted_tweet"):
            engagement_count += 1

        if tweet.get("inReplyToUsername"):
            engagement_count += 1
            replied_user = tweet.get("inReplyToUsername")
            for username in dedicated_accounts:
                if username == replied_user:
                    reply_count += 1
                    break
        if tweet.get("quoted_tweet"):
            quoted_user = tweet["quoted_tweet"].get("author", {}).get("userName", "unknown")
            for username in dedicated_accounts:
                if username == quoted_user:
                    retweet_count += 1
                    break
        text = tweet["text"]
        for username in dedicated_accounts:
            username = "@" + username
            if username in text:
                mention_count += 1
                break

    # Calculate engagement score (0-25)
    if engagement_count > 100:
        engagement_score += 25
    elif engagement_count > 50:
        engagement_score += 15
    elif engagement_count > 20:
        engagement_score += 10
    elif engagement_count > 5:
        engagement_score += 5          

    if mention_count > 5:
        project_score += 8
    elif mention_count > 3:
        project_score += 5
    elif mention_count >= 1:
        project_score += 3

    if retweet_count > 5:
        project_score += 10
    elif retweet_count > 3:
        project_score += 5
    elif retweet_count >= 1:
        project_score += 3

    if reply_count > 5:
        project_score += 7
    elif reply_count > 3:
        project_score += 5
    elif reply_count >= 1:
        project_score += 3

    # Calculate quality score (0-25)
    # Based on tweet count and engagement
    if tweet_count > 100:
        quality_score += 10
    elif tweet_count > 60:
        quality_score += 7
    elif tweet_count > 30:
        quality_score += 5
    elif tweet_count > 10:
        quality_score += 3

    # Add quality points based on engagement
    if avg_interaction > 100:
        quality_score += 15
    elif avg_interaction > 50:
        quality_score += 10
    elif avg_interaction > 20:
        quality_score += 5

    total_score = engagement_score + influence_score + project_score + quality_score
    total_score = round(total_score * authenticity_factor, 2)

    return {
        "engagement_score": round(engagement_score, 2),
        "influence_score": round(influence_score, 2),
        "project_score": round(project_score, 2),
        "quality_score": round(quality_score, 2),
        "total_score": total_score,
        "authenticity_factor": round(authenticity_factor, 2),
        "detail": {
            "explanation": "Calculated using legacy scoring system",
            "quality_sub_scores": {
                "content_quality": quality_score,
                "language_grammar": 0,
                "professionalism": 0,
                "value_to_readers": 0
            },
            "authenticity_sub_scores": {
                "content_authenticity": authenticity_factor,
                "engagement_patterns": 1.0,
                "account_behavior": 1.0
            }
        }
    }

def estimate_tweets(user_name):
    recent_tweets = load_user_tweets_within(user_name, 90)
    
    if not recent_tweets or len(recent_tweets) == 0:
        return {
            "total_score": 0,
            "engagement_score": 0,
            "influence_score": 0,
            "project_score": 0,
            "quality_score": 0,    
            "project_score": 0,
            "authenticity_factor": 0,
            "detail": {}
        }
    
    # Calculate tweet quality score (0-25)
    quality_score = 0
    influence_score = 0
    engagement_score = 0
    project_score = 0
    authenticity_factor = 0
    detail = {}

    dedicated_accounts = ["beeperfun", "beeper_agent"]

    ordered_tweets = order_tweets(recent_tweets, reverse=True)
    user_info = ordered_tweets[0].get("author", {})
    filtered_tweets = filter_tweets(ordered_tweets)
    batches = build_batches(tweets=filtered_tweets, max_tokens=40960+10240, max_batch=1)
    if len(batches) == 0:
        return estimate_legacy(recent_tweets, dedicated_accounts)
    
    try:
        result = estimate_by_llm(batches[0], user_info, dedicated_accounts)
        print(f"result: {result}")
        # Parse the string response into a JSON object
        result = result.replace("```json", "").replace("```", "")
        result = json.loads(result)
        quality_score = result["quality_score"]
        influence_score = result["influence_score"]
        engagement_score = result["engagement_score"]
        project_score = result["project_score"]
        authenticity_factor = result["authenticity_score"]
        detail["explanation"] = result["explanation"]
        detail["quality_sub_scores"] = result["quality_sub_scores"]
        detail["authenticity_sub_scores"] = result["authenticity_sub_scores"]
    except Exception as e:
        print(f"Error estimating {user_name} score: {e}")
        return estimate_legacy(recent_tweets, dedicated_accounts)

    if user_info.get("isBlueVerified", False):
        print(f"User is blue verified")
        authenticity_factor = 1.0
    elif int(user_info.get("followers", 0)) > 10000:
        print(f"User has followers: {user_info['followers']}")
        authenticity_factor = 1.0

    total_score = engagement_score + influence_score + project_score + quality_score
    total_score = round(total_score*authenticity_factor, 2)

    return {
        "engagement_score": round(engagement_score, 2),
        "influence_score": round(influence_score, 2),
        "project_score": round(project_score, 2),
        "quality_score": round(quality_score, 2),
        "total_score": round(total_score, 2),
        "authenticity_factor": round(authenticity_factor,2),
        "detail": detail
    }

def estimate(user_name):
    print(f"Estimating {user_name} score")
    scores = estimate_tweets(user_name)
    print(f"{user_name} score is {scores}")

    write_user_airdrop_score(user_name, scores)

if __name__ == "__main__":
    default_x_name = "cz_binance"
    args = sys.argv[1:]
    if len(args) > 0:
        default_x_name = args[0] 
    try:
        estimate(default_x_name)
    except Exception as e:
        print(f"Error estimating {default_x_name} score: {e}")
        raise e