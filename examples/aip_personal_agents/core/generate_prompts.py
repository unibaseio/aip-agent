import json
import os
from tiktoken import encoding_for_model
from openai import OpenAI

from core.common import load_user_tweets

ENCODER = encoding_for_model("gpt-4o-mini")

def num_tokens(text):
    return len(ENCODER.encode(text))

def build_batches(tweets, max_tokens=51200, max_batch=4, include_metadata=False):
    batches, current, total = [], [], 0
    for t in tweets:
        # If we've reached max_batch, stop processing
        if len(batches) >= max_batch:
            break
            
        txt = t['text']
        if include_metadata:
            txt = json.dumps(t, indent=2)
        tokens = num_tokens(txt)
        if total + tokens > max_tokens and current:
            batches.append(current)
            current, total = [], 0
        current.append(txt)
        total += tokens
        
    if current and len(batches) < max_batch:
        batches.append(current)
    return batches

# Initialize OpenAI client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    #base_url="https://api.deepseek.com/v1"
)

model_name = "gpt-4.1-mini"

prompt_template = """
You are an expert in personality analysis through social media data. Your task is to analyze a user's tweets and generate a comprehensive personality profile. Focus on both explicit and implicit characteristics, and provide evidence-based insights.

The user's information is as follows:
==== BEGIN USER INFO ====
{user_info}
==== END USER INFO ====

Below is a list of tweets from a user:

==== BEGIN TWEETS ====
{tweets_here}
==== END TWEETS ====

Important Twitter Field Explanations:
- text: The main content of the tweet, including:
  * Original tweet text
  * Quoted tweet content (if any) with format: "Quoted from @username: [quoted text]"
  * Reply content (if any) with format: "Reply to @username: [reply text]"
- post_type: Type of tweet:
  * "original": Original tweet
  * "reply": Reply to another tweet
  * "quote": Quote of another tweet
- created_at: Timestamp when the tweet was posted
- likeCount: Number of likes to the tweet
- retweetCount: Number of retweets to the tweet
- replyCount: Number of replies to the tweet

Analyze these tweets and generate a detailed persona profile. Your analysis should be thorough, evidence-based, and include specific examples from the tweets when relevant.

Return your analysis in the following structured JSON format:

{
  "basic_profile": {
    "language": "Main language(s) used in tweets",
    "active_hours": "Typical posting hours and patterns",
    "posting_frequency": "How often the user posts",
    "account_age": "How long the account has been active",
    "platform_usage": "How the user utilizes different platform features"
  },
  "communication_style": {
    "writing_style": "Describe tone and writing traits (e.g., sarcastic, blunt, humorous, concise, emotional)",
    "expression_patterns": "How the user expresses opinions or emotions (direct, ironic, analytical, fragmented etc.)",
    "vocabulary_level": "Level of language sophistication and word choice",
    "emoji_usage": "How and when emojis are used",
    "punctuation_style": "Use of punctuation and formatting",
    "sentence_structure": "Typical sentence length and complexity",
    "rhetorical_devices": "Use of rhetorical techniques (questions, analogies, etc.)"
  },
  "content_analysis": {
    "topics_of_interest": ["List of dominant themes/subjects (no hashtags) the user engages with, including attitude towards the topic and the frequency of engagement for each topic"],
    "keywords_or_phrases": ["List of recurring terms, slang, hashtags, named entities, etc."],
    "external_links_or_sources": ["Mentioned or quoted platforms/accounts"],
    "content_type": "Types of content shared (personal, news, opinions, memes, etc.)",
    "content_quality": "Quality and depth of content (superficial, in-depth, research-based, etc.)",
    "content_originality": "Ratio of original content vs. shared/retweeted content",
    "content_evolution": "How content focus has changed over time"
  },
  "emotional_profile": {
    "emotional_tone": "Overall emotional attitude expressed (optimistic, frustrated, concerned, critical, neutral, etc.)",
    "emotional_variability": "Does the tone fluctuate? How intense or stable is it?",
    "sentiment_trends": "Any noticeable patterns in emotional expression",
    "emotional_triggers": "What topics or situations trigger strong emotional responses",
    "emotional_resilience": "How quickly emotional states change or recover"
  },
  "social_behavior": {
    "interaction_style": "Level of engagement with others (highly interactive, reactive, mostly broadcasting)",
    "social_identity": "What role does the user appear to play on the platform? (influencer, activist, observer, provocateur, educator, etc.)",
    "community_engagement": "How the user interacts with their community",
    "response_patterns": "How the user responds to different types of interactions",
    "social_network": "Size and nature of their social network",
    "influence_style": "How they exert influence (direct, indirect, through engagement, etc.)"
  },
  "values_and_beliefs": {
    "value_orientation": "Political/social/cultural values inferred from their engagement or retweets",
    "opinion_strength": "How strongly are views expressed? (Mild, assertive, provocative)",
    "consistency": "How consistent are their views across different topics?",
    "moral_framework": "Underlying moral principles and ethical stance",
    "worldview": "General perspective on society and the world"
  },
  "motivation_analysis": {
    "probable_motivation": "Why do they post? (Information sharing, emotional release, public stance, meme culture, critique etc.)",
    "engagement_drivers": "What seems to motivate their social media activity?",
    "content_purpose": "Primary purpose of their posts",
    "personal_branding": "How they manage their online persona",
    "platform_goals": "What they aim to achieve on the platform"
  },
  "influence_metrics": {
    "reach": "Estimated audience size and engagement level",
    "authority": "Perceived expertise and credibility in specific domains",
    "impact": "How their content affects others and the platform",
    "network_position": "Their position in the social network (central, peripheral, etc.)",
    "trend_setting": "Ability to set or follow trends"
  },
  "behavioral_patterns": {
    "posting_patterns": "Regular posting times, frequency patterns",
    "engagement_patterns": "How they engage with different types of content",
    "response_time": "Typical response time to interactions",
    "content_rhythm": "Patterns in content creation and sharing",
    "platform_habits": "Specific platform features they frequently use"
  },
  "content_quality_metrics": {
    "originality_score": "How original and unique their content is",
    "engagement_quality": "Quality of interactions and discussions",
    "information_value": "Value of information shared",
    "content_depth": "Depth and thoroughness of content",
    "reliability": "Consistency and reliability of information"
  }
}

Important notes:
1. Base your analysis on concrete evidence from the tweets
2. Be specific and avoid generic descriptions
3. Include examples when relevant
4. Maintain a professional and objective tone
5. Focus on observable patterns rather than assumptions
6. Consider both quantitative and qualitative aspects
7. Note any significant changes or evolution in behavior over time
8. Highlight unique or distinctive characteristics
9. Consider the context of the platform and its norms
10. Identify any potential biases or limitations in the analysis
"""

def call_batch(user_info, batch):
    # convert user info into string
    if isinstance(user_info, dict):
        user_info = json.dumps(user_info)
    prompt = prompt_template.replace("{user_info}", user_info).replace("{tweets_here}", "\n".join(batch))
    response = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message.content

if __name__ == "__main__":
    user_name = "elonmusk"
    tweets = load_user_tweets(user_name)
    
    if len(tweets) == 0:
        print(f"No tweets found for {user_name}")
        exit()

    user_info = tweets[-1].get("author", {})

    batches = build_batches(tweets)
    
    results = []
    for i, batch in enumerate(batches):
        print(f"Processing batch {i+1}/{len(batches)}")
        result = call_batch(user_info, batch)
        results.append(result)
        with open(f"outputs/{user_name}/{user_name}_profile_batch_{i+1}.json", "w") as f:
            f.write(result)
