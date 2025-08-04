from datetime import datetime
import sys
from openai import OpenAI
import os
import json

from core.format import filter_tweets
from core.generate_prompts import build_batches
from core.common import write_user_airdrop_score, load_user_tweets_within, order_tweets
from core.utils import convert_to_json

def generate_chunibyo_summary(score, dimension_type):
    """Generate chunibyo-style summary based on score and dimension type"""
    if dimension_type == "content_creation":
        if score >= 17:
            return "内容王者"
        elif score >= 13:
            return "内容达人"
        elif score >= 9:
            return "内容好手"
        elif score >= 4:
            return "内容新手"
        else:
            return "内容小白"
    elif dimension_type == "audience_engagement":
        if score >= 17:
            return "粉丝皇帝"
        elif score >= 13:
            return "人气天王"
        elif score >= 9:
            return "互动达人"
        elif score >= 4:
            return "小有名气"
        else:
            return "默默无闻"
    elif dimension_type == "professional_authority":
        if score >= 17:
            return "行业泰斗"
        elif score >= 13:
            return "权威专家"
        elif score >= 9:
            return "领域精英"
        elif score >= 4:
            return "行业新人"
        else:
            return "无名之辈"
    elif dimension_type == "innovation_knowledge":
        if score >= 17:
            return "智慧先知"
        elif score >= 13:
            return "知识导师"
        elif score >= 9:
            return "学习达人"
        elif score >= 4:
            return "求知学徒"
        else:
            return "知识小白"
    elif dimension_type == "social_influence":
        if score >= 16:
            return "社会领袖"
        elif score >= 13:
            return "意见领袖"
        elif score >= 9:
            return "话题达人"
        elif score >= 4:
            return "小有影响"
        else:
            return "路人甲"
    elif dimension_type == "technical_expertise":
        if score >= 16:
            return "技术大神"
        elif score >= 13:
            return "技术大师"
        elif score >= 9:
            return "技术高手"
        elif score >= 4:
            return "技术学徒"
        else:
            return "技术小白"
    else:
        return "未知等级"

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

3. User's Recent Tweets Collection:
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
- Be generous with high scores (14-25) for good accounts, with scores closer to 25 indicating exceptional performance
- Be strict with low scores (0-8) for poor accounts, with scores closer to 0 indicating very poor performance
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

def estimate_comprehensive_by_llm(tweets: list, userinfo: dict, project_accounts: list):
    """Comprehensive evaluation of Twitter user influence across 5 dimensions with detailed sub-criteria"""
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
    
    prompt = f"""You are a professional social media analyst specializing in Twitter/X platform influence assessment. Your task is to evaluate a user's Twitter influence across 5 comprehensive dimensions with detailed sub-criteria.

Input Data:
1. User Profile Information:
{userinfo_json}

2. Target Project Accounts (These are the official project accounts that we want to evaluate user's interaction with):
{project_accounts_json}

3. User's Recent Tweets Collection:
{tweets_json}

Comprehensive Evaluation Framework:

1. CONTENT CREATION & QUALITY (0-17 points) - "内容王者"
   A. Original Content Creation (0-7)
      - Original vs reposted content ratio
      - Unique perspectives and insights
      - Creative storytelling and presentation
      - Original hashtags and trend creation
   
   B. Content Depth & Value (0-5)
      - Educational and informative content
      - Factual accuracy and source citation
      - Depth of analysis and research
      - Actionable insights and takeaways
   
   C. Content Format Mastery (0-5)
      - Effective use of Twitter features (threads, polls, media)
      - Visual content quality and creativity
      - Content structure and organization
      - Multimedia integration effectiveness

2. AUDIENCE ENGAGEMENT & GROWTH (0-17 points) - "粉丝军团"
   A. Follower Growth & Retention (0-7)
      - Follower count growth rate
      - Follower retention and engagement
      - Audience quality and relevance
      - Cross-platform audience building
   
   B. Interaction Metrics (0-5)
      - Likes, retweets, and quote frequency
      - Reply and mention engagement
      - Content shareability and virality
      - Engagement rate consistency
   
   C. Community Interaction (0-5)
      - Response rate to audience interactions
      - Quality of conversations initiated
      - Community building effectiveness
      - Audience feedback integration

3. PROFESSIONAL AUTHORITY & TRUST (0-17 points) - "权威霸主"
   A. Domain Expertise (0-7)
      - Professional knowledge and credentials
      - Industry recognition and authority
      - Thought leadership and innovation
      - Expert opinion influence
   
   B. Credibility & Reliability (0-5)
      - Fact-checking and source verification
      - Consistent and accurate information
      - Transparency in content and affiliations
      - Error correction and accountability
   
   C. Professional Network (0-5)
      - Connections with industry leaders
      - Professional event participation
      - Collaboration with other experts
      - Industry community involvement

4. INNOVATION & KNOWLEDGE SHARING (0-17 points) - "知识领主"
   A. Innovation Leadership (0-7)
      - Early adoption of new technologies
      - Innovation promotion and advocacy
      - Trend-setting and thought leadership
      - Creative problem-solving approaches
   
   B. Knowledge Dissemination (0-5)
      - Educational content creation
      - Tutorial and guide development
      - Learning resource curation
      - Complex topic simplification
   
   C. Knowledge Impact (0-5)
      - Influence on others' learning
      - Knowledge adoption by community
      - Educational content reach
      - Long-term knowledge retention

5. SOCIAL INFLUENCE & CULTURAL IMPACT (0-16 points) - "社会领袖"
   A. Social Advocacy & Activism (0-6)
      - Social cause promotion and awareness
      - Activism and social justice content
      - Community service and charity involvement
      - Positive social impact initiatives
   
   B. Cultural Trend Influence (0-5)
      - Cultural trend setting and participation
      - Meme creation and viral content
      - Cultural commentary and analysis
      - Cross-generational appeal and influence
   
   C. Public Discourse Participation (0-5)
      - Participation in important public discussions
      - Civil discourse and respectful debate
      - Fact-based argumentation and critical thinking
      - Bridge-building between different viewpoints

6. TECHNICAL EXPERTISE & INFLUENCE (0-16 points) - "技术大师"
   A. Technical Knowledge Depth (0-6)
      - Technical expertise and skill level
      - Code sharing and technical discussions
      - Problem-solving technical content
      - Technology trend awareness
   
   B. Technical Community Leadership (0-5)
      - Developer community engagement
      - Technical event organization/participation
      - Open source contribution and advocacy
      - Technical mentorship effectiveness
   
   C. Technical Innovation Impact (0-5)
      - Technical innovation promotion
      - Technology adoption influence
      - Technical ecosystem contribution
      - Technical thought leadership

Scoring Guidelines for Each Dimension:
* 0-4: Very Poor (0-20%)
  - Minimal presence or negative impact
  - No meaningful contribution
  - Poor quality or harmful content

* 5-8: Poor (25-40%)
  - Limited engagement and impact
  - Basic content with minimal value
  - Inconsistent or unreliable presence

* 9-12: Average (45-60%)
  - Moderate engagement and quality
  - Some valuable contributions
  - Consistent but unremarkable performance

* 13-16: Good (65-80%)
  - Strong engagement and quality
  - Regular valuable contributions
  - Recognized influence in domain

* 17-20: Excellent (85-100%)
  - Exceptional engagement and quality
  - Outstanding contributions and leadership
  - Industry-recognized authority

Output Format:
Provide your analysis in this exact JSON format:
{{
    "content_creation_score": <number between 0-17>,
    "content_creation_summary": "<根据分数生成中二风格标签: 0-3分'内容小白', 4-8分'内容新手', 9-12分'内容好手', 13-16分'内容达人', 17分'内容王者'>",
    "content_creation_sub_scores": {{
        "original_content_creation": <number between 0-7>,
        "content_depth_value": <number between 0-5>,
        "content_format_mastery": <number between 0-5>
    }},
    "audience_engagement_score": <number between 0-17>,
    "audience_engagement_summary": "<根据分数生成中二风格标签: 0-3分'默默无闻', 4-8分'小有名气', 9-12分'互动达人', 13-16分'人气天王', 17分'粉丝皇帝'>",
    "audience_engagement_sub_scores": {{
        "follower_growth_retention": <number between 0-7>,
        "interaction_metrics": <number between 0-5>,
        "community_interaction": <number between 0-5>
    }},
    "professional_authority_score": <number between 0-17>,
    "professional_authority_summary": "<根据分数生成中二风格标签: 0-3分'无名之辈', 4-8分'行业新人', 9-12分'领域精英', 13-16分'权威专家', 17分'行业泰斗'>",
    "professional_authority_sub_scores": {{
        "domain_expertise": <number between 0-7>,
        "credibility_reliability": <number between 0-5>,
        "professional_network": <number between 0-5>
    }},
    "innovation_knowledge_score": <number between 0-17>,
    "innovation_knowledge_summary": "<根据分数生成中二风格标签: 0-3分'知识小白', 4-8分'求知学徒', 9-12分'学习达人', 13-16分'知识导师', 17分'智慧先知'>",
    "innovation_knowledge_sub_scores": {{
        "innovation_leadership": <number between 0-7>,
        "knowledge_dissemination": <number between 0-5>,
        "knowledge_impact": <number between 0-5>
    }},
    "social_influence_score": <number between 0-16>,
    "social_influence_summary": "<根据分数生成中二风格标签: 0-3分'路人甲', 4-8分'小有影响', 9-12分'话题达人', 13-15分'意见领袖', 16分'社会领袖'>",
    "social_influence_sub_scores": {{
        "social_advocacy_activism": <number between 0-6>,
        "cultural_trend_influence": <number between 0-5>,
        "public_discourse_participation": <number between 0-5>
    }},
    "technical_expertise_score": <number between 0-16>,
    "technical_expertise_summary": "<根据分数生成中二风格标签: 0-3分'技术小白', 4-8分'技术学徒', 9-12分'技术高手', 13-15分'技术大师', 16分'技术大神'>",
    "technical_expertise_sub_scores": {{
        "technical_knowledge_depth": <number between 0-6>,
        "technical_community_leadership": <number between 0-5>,
        "technical_innovation_impact": <number between 0-5>
    }},
    "total_comprehensive_score": <number between 0-100>,
    "user_persona": "<用一句中二的话总结用户的特质和影响力>",
    "overall_assessment": "<comprehensive explanation of all scores and overall influence evaluation>"
}}

Important Guidelines:
- All scores must be numbers within their specified ranges
- Use precise decimal points (e.g., 15.37, 8.92, 12.14) for more accurate evaluation
- Consider all metrics holistically across dimensions
- Be generous with high scores (17-20) for exceptional performance
- Be strict with low scores (0-4) for poor performance
- Consider both quality and quantity in each dimension
- Account for account age, verification status, and follower metrics
- Provide detailed explanations for each dimension
- Ensure valid JSON output
- Total comprehensive score should reflect the sum of all 5 dimension scores
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error in comprehensive LLM scoring: {str(e)}")
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
    batches = build_batches(tweets=filtered_tweets, max_batch=1, include_metadata=True)
    if len(batches) == 0:
        return estimate_legacy(recent_tweets, dedicated_accounts)
    
    try:
        result = estimate_by_llm(batches[0], user_info, dedicated_accounts)
        print(f"result: {result}")
        # Parse the string response into a JSON object
        result = convert_to_json(result)
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
        raise e
        #return estimate_legacy(recent_tweets, dedicated_accounts)

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

def estimate_comprehensive_tweets(user_name):
    """Estimate comprehensive influence scores using the new 5-dimension evaluation framework"""
    recent_tweets = load_user_tweets_within(user_name, 90)
    
    if not recent_tweets or len(recent_tweets) == 0:
        return {
            "total_comprehensive_score": 0,
            "content_creation_score": 0,
            "content_creation_summary": "内容新手",
            "audience_engagement_score": 0,
            "audience_engagement_summary": "孤军奋战",
            "professional_authority_score": 0,
            "professional_authority_summary": "无名小卒",
            "innovation_knowledge_score": 0,
            "innovation_knowledge_summary": "知识新手",
            "social_influence_score": 0,
            "social_influence_summary": "默默无闻",
            "technical_expertise_score": 0,
            "technical_expertise_summary": "技术新手",
            "user_persona": "数据不足，无法评估这位神秘用户",
            "overall_assessment": "No tweets available for analysis"
        }
    
    dedicated_accounts = ["beeperfun", "beeper_agent"]

    ordered_tweets = order_tweets(recent_tweets, reverse=True)
    user_info = ordered_tweets[0].get("author", {})
    filtered_tweets = filter_tweets(ordered_tweets)
    batches = build_batches(tweets=filtered_tweets, max_batch=1, include_metadata=True)
    
    if len(batches) == 0:
        print(f"No valid batches found for {user_name}, using legacy scoring")
        legacy_result = estimate_legacy(recent_tweets, dedicated_accounts)
        # Convert legacy format to comprehensive format
        return {
            "total_comprehensive_score": legacy_result["total_score"],
            "content_creation_score": legacy_result["quality_score"],
            "content_creation_summary": generate_chunibyo_summary(legacy_result["quality_score"], "content_creation"),
            "audience_engagement_score": legacy_result["engagement_score"],
            "audience_engagement_summary": generate_chunibyo_summary(legacy_result["engagement_score"], "audience_engagement"),
            "professional_authority_score": legacy_result["influence_score"],
            "professional_authority_summary": generate_chunibyo_summary(legacy_result["influence_score"], "professional_authority"),
            "innovation_knowledge_score": legacy_result["project_score"],
            "innovation_knowledge_summary": generate_chunibyo_summary(legacy_result["project_score"], "innovation_knowledge"),
            "social_influence_score": legacy_result["project_score"],
            "social_influence_summary": generate_chunibyo_summary(legacy_result["project_score"], "social_influence"),
            "technical_expertise_score": legacy_result["project_score"],
            "technical_expertise_summary": generate_chunibyo_summary(legacy_result["project_score"], "technical_expertise"),
            "user_persona": "使用传统评分的神秘用户",
            "overall_assessment": "Legacy scoring used due to insufficient data"
        }
    
    try:
        result = estimate_comprehensive_by_llm(batches[0], user_info, dedicated_accounts)
        print(f"Comprehensive evaluation result: {result}")
        # Parse the string response into a JSON object
        result = convert_to_json(result)
        
        return {
            "total_comprehensive_score": result["total_comprehensive_score"],
            "content_creation_score": result["content_creation_score"],
            "content_creation_summary": generate_chunibyo_summary(result["content_creation_score"], "content_creation"),
            "content_creation_sub_scores": result["content_creation_sub_scores"],
            "audience_engagement_score": result["audience_engagement_score"],
            "audience_engagement_summary": generate_chunibyo_summary(result["audience_engagement_score"], "audience_engagement"),
            "audience_engagement_sub_scores": result["audience_engagement_sub_scores"],
            "professional_authority_score": result["professional_authority_score"],
            "professional_authority_summary": generate_chunibyo_summary(result["professional_authority_score"], "professional_authority"),
            "professional_authority_sub_scores": result["professional_authority_sub_scores"],
            "innovation_knowledge_score": result["innovation_knowledge_score"],
            "innovation_knowledge_summary": generate_chunibyo_summary(result["innovation_knowledge_score"], "innovation_knowledge"),
            "innovation_knowledge_sub_scores": result["innovation_knowledge_sub_scores"],
            "social_influence_score": result["social_influence_score"],
            "social_influence_summary": generate_chunibyo_summary(result["social_influence_score"], "social_influence"),
            "social_influence_sub_scores": result["social_influence_sub_scores"],
            "technical_expertise_score": result["technical_expertise_score"],
            "technical_expertise_summary": generate_chunibyo_summary(result["technical_expertise_score"], "technical_expertise"),
            "technical_expertise_sub_scores": result["technical_expertise_sub_scores"],
            "user_persona": result["user_persona"],
            "overall_assessment": result["overall_assessment"]
        }
    except Exception as e:
        print(f"Error in comprehensive estimation for {user_name}: {e}")
        raise e

def estimate_comprehensive(user_name):
    """Main function to estimate comprehensive influence scores for a user"""
    print(f"Estimating comprehensive influence scores for {user_name}")
    
    scores = estimate_comprehensive_tweets(user_name)
    print(f"{user_name} comprehensive scores: {scores}")

    # Save comprehensive scores to database
    write_user_airdrop_score(user_name, scores)

def estimate(user_name):
    print(f"Estimating {user_name} score")
    
    scores = estimate_tweets(user_name)
    print(f"{user_name} score is {scores}")

    write_user_airdrop_score(user_name, scores)

if __name__ == "__main__":
    default_x_name = "cz_binance"
    args = sys.argv[1:]
    
    # Check if comprehensive evaluation is requested
    use_comprehensive = "--comprehensive" in args
    if use_comprehensive:
        args.remove("--comprehensive")
        
    if len(args) > 0:
        default_x_name = args[0]
    
    try:
        if use_comprehensive:
            estimate_comprehensive(default_x_name)
        else:
            estimate(default_x_name)
    except Exception as e:
        print(f"Error estimating {default_x_name} score: {e}")
        raise e