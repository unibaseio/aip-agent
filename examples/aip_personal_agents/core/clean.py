import json
import os
from typing import Dict, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum
import instructor
from openai import OpenAI
from .common import load_user_tweets, write_user_status, update_user_status

# ============ Multi-level Categories ============

class DeFiSubCategory(str, Enum):
    """DeFi subcategories"""
    YIELD_FARMING = "yield_farming"
    STABLECOINS = "stablecoins"
    STAKING = "staking"
    LENDING = "lending"
    DEX = "dex"
    DERIVATIVES = "derivatives"

class NFTSubCategory(str, Enum):
    """NFT subcategories"""
    GAMING = "gaming"
    MUSIC = "music"
    PFP = "pfp"  # Profile Picture
    ART = "art"
    UTILITY = "utility"
    COLLECTIBLES = "collectibles"

class DAOSubCategory(str, Enum):
    """DAO subcategories"""
    GOVERNANCE = "governance"
    TREASURY = "treasury"
    VOTING = "voting"
    PROPOSALS = "proposals"

class Layer1SubCategory(str, Enum):
    """Layer 1 blockchain subcategories"""
    ETHEREUM = "ethereum"
    SOLANA = "solana"
    AVALANCHE = "avalanche"
    POLYGON = "polygon"
    CARDANO = "cardano"

class Layer2SubCategory(str, Enum):
    """Layer 2 scaling solution subcategories"""
    ARBITRUM = "arbitrum"
    ZKSYNC = "zksync"
    BASE = "base"
    OPTIMISM = "optimism"
    STARKNET = "starknet"

class MemeCoinSubCategory(str, Enum):
    """Meme coin subcategories"""
    DOGE = "doge"
    PEPE = "pepe"
    WIF = "wif"
    SHIB = "shib"
    BONK = "bonk"

class LLMSubCategory(str, Enum):
    """Large Language Model subcategories"""
    GPT_4 = "gpt-4"
    CLAUDE = "claude"
    GEMINI = "gemini"
    OPEN_SOURCE = "open-source"
    LLAMA = "llama"

class AgentSubCategory(str, Enum):
    """AI Agent subcategories"""
    AUTONOMOUS = "autonomous"
    CHATBOT = "chatbot"
    WORKFLOW = "workflow"
    MULTI_AGENT = "multi-agent"
    REASONING = "reasoning"

# ============ Main Categories ============

class Web3MainCategory(str, Enum):
    """Web3 main categories"""
    DEFI = "defi"
    NFT = "nft"
    DAO = "dao"
    GAMEFI = "gamefi"
    METAVERSE = "metaverse"

class BlockchainMainCategory(str, Enum):
    """Blockchain main categories"""
    LAYER1 = "layer1"
    LAYER2 = "layer2"
    INTEROPERABILITY = "interoperability"
    CONSENSUS = "consensus"

class CryptoMainCategory(str, Enum):
    """Crypto main categories"""
    TOKENOMICS = "tokenomics"
    MEME_COIN = "meme_coin"
    REGULATION = "regulation"
    SECURITY = "security"
    TRADING = "trading"

class AIMainCategory(str, Enum):
    """AI main categories"""
    LLM = "llm"
    AGENT = "agent"
    PROMPT_ENGINEERING = "prompt_engineering"
    MACHINE_LEARNING = "machine_learning"
    COMPUTER_VISION = "computer_vision"

# ============ Multi-dimensional Tags ============

class IntentType(str, Enum):
    """Intent classification for tweets"""
    INFORMATIVE = "informative"
    PROMOTIONAL = "promotional"
    EDUCATIONAL = "educational"
    DISCUSSION = "discussion"
    QUESTION = "question"
    ANNOUNCEMENT = "announcement"

class ToneType(str, Enum):
    """Tone classification for tweets"""
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    HUMOROUS = "humorous"
    SERIOUS = "serious"
    EXCITED = "excited"
    NEUTRAL = "neutral"

class AudienceType(str, Enum):
    """Target audience classification"""
    BEGINNERS = "beginners"
    INTERMEDIATE = "intermediate"
    EXPERTS = "experts"
    DEVELOPERS = "developers"
    INVESTORS = "investors"
    TRADERS = "traders"
    GENERAL_PUBLIC = "general_public"

class SentimentType(str, Enum):
    """Sentiment analysis"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    BULLISH = "bullish"
    BEARISH = "bearish"

class ContentType(str, Enum):
    """Content type classification"""
    NEWS = "news"
    ANALYSIS = "analysis"
    OPINION = "opinion"
    TUTORIAL = "tutorial"
    ANNOUNCEMENT = "announcement"
    DISCUSSION = "discussion"
    MEME = "meme"
    ALPHA = "alpha"

# ============ Hierarchical Tag Structure ============

class HierarchicalTag(BaseModel):
    """Hierarchical tag with main category and subcategories"""
    main_category: str = Field(description="Main category")
    sub_categories: List[str] = Field(default=[], description="Subcategories under the main category")
    confidence: float = Field(ge=0.0, le=1.0, default=0.8, description="Confidence in this categorization")

class TweetTags(BaseModel):
    """Tweet tagging structure with hierarchical categories and multi-dimensional classification"""
    
    # Primary classification
    is_web3_related: bool = Field(description="Whether the tweet is related to Web3")
    is_blockchain_related: bool = Field(description="Whether the tweet is related to blockchain technology")
    is_crypto_related: bool = Field(description="Whether the tweet is related to cryptocurrency")
    is_ai_related: bool = Field(description="Whether the tweet is related to AI/ML")
    
    # Hierarchical categories
    web3_tags: List[HierarchicalTag] = Field(default=[], description="Web3 hierarchical tags")
    blockchain_tags: List[HierarchicalTag] = Field(default=[], description="Blockchain hierarchical tags")
    crypto_tags: List[HierarchicalTag] = Field(default=[], description="Crypto hierarchical tags")
    ai_tags: List[HierarchicalTag] = Field(default=[], description="AI hierarchical tags")
    
    # Multi-dimensional tags (主题，主体，意图，语气，受众)
    content_type: ContentType = Field(description="Type of content (主题)")
    intent: IntentType = Field(description="Intent of the tweet (意图)")
    tone: ToneType = Field(description="Tone of the tweet (语气)")
    target_audience: AudienceType = Field(description="Target audience (受众)")
    sentiment: SentimentType = Field(description="Overall sentiment of the tweet")
    
    # Extracted information (主体)
    key_topics: List[str] = Field(description="Key topics/keywords mentioned")
    mentioned_projects: List[str] = Field(default=[], description="Specific projects/companies mentioned")
    mentioned_tokens: List[str] = Field(default=[], description="Specific tokens/cryptocurrencies mentioned")
    mentioned_people: List[str] = Field(default=[], description="Notable people mentioned")
    
    # Quality metrics
    technical_level: int = Field(ge=1, le=5, description="Technical complexity level (1=beginner, 5=expert)")
    engagement_potential: int = Field(ge=1, le=5, description="Potential for engagement (1=low, 5=high)")
    
    # Special flags
    is_alpha: bool = Field(default=False, description="Contains potential alpha/insider information")
    is_educational: bool = Field(default=False, description="Has educational value")
    is_time_sensitive: bool = Field(default=False, description="Time-sensitive information")

class TweetAnalysis(BaseModel):
    """Complete tweet analysis with metadata"""
    tweet_id: str
    tweet_text: str
    created_at: str
    author: str
    tags: TweetTags
    analysis_timestamp: str
    confidence_score: float = Field(ge=0.0, le=1.0, description="Overall confidence in the analysis")

# ============ User Profile Structures ============

class TopicInterest(BaseModel):
    """User's interest in a specific topic"""
    topic: str = Field(description="Topic name")
    category: str = Field(description="Main category (web3, blockchain, crypto, ai)")
    frequency: int = Field(description="Number of tweets about this topic")
    percentage: float = Field(description="Percentage of total tweets")
    sentiment_distribution: Dict[str, int] = Field(default={}, description="Sentiment distribution for this topic")
    recent_activity: bool = Field(default=False, description="Active in this topic recently")
    confidence: float = Field(ge=0.0, le=1.0, default=0.8, description="Confidence in this interest")

class UserBehaviorPattern(BaseModel):
    """User's behavioral patterns from tweet analysis"""
    posting_frequency: float = Field(description="Average tweets per day")
    technical_level: int = Field(ge=1, le=5, description="User's technical sophistication level")
    engagement_style: str = Field(description="How user typically engages (Educator, Alpha Sharer, etc.)")
    
    # Content preferences
    preferred_content_types: List[ContentType] = Field(default=[], description="Preferred content types")
    typical_intent: IntentType = Field(description="User's typical intent")
    typical_tone: ToneType = Field(description="User's typical tone")
    typical_audience: AudienceType = Field(description="User's typical target audience")
    typical_sentiment: SentimentType = Field(description="User's typical sentiment")
    
    # Special characteristics
    shares_alpha: bool = Field(default=False, description="Frequently shares alpha information")
    creates_educational_content: bool = Field(default=False, description="Creates educational content")
    provides_market_commentary: bool = Field(default=False, description="Provides market commentary")
    
    # Influence metrics
    influence_score: int = Field(ge=1, le=10, description="User's influence in the community")

class UserProfile(BaseModel):
    """Comprehensive user profile based on tweet analysis"""
    username: str
    analysis_period: str = Field(description="Time period of analysis")
    total_tweets_analyzed: int
    
    # Interest analysis
    topic_interests: List[TopicInterest] = Field(default=[], description="User's topic interests")
    primary_focus_areas: List[str] = Field(default=[], description="Top 3-5 primary focus areas")
    secondary_interests: List[str] = Field(default=[], description="Secondary interests")
    
    # Behavioral patterns
    behavior_patterns: UserBehaviorPattern
    
    # User classification
    user_type: str = Field(description="Primary user type (e.g., 'DeFi Enthusiast', 'AI Researcher')")
    expertise_areas: List[str] = Field(default=[], description="Areas of demonstrated expertise")
    
    # Social network analysis
    frequently_mentioned_projects: List[str] = Field(default=[], description="Frequently mentioned projects")
    frequently_mentioned_people: List[str] = Field(default=[], description="Frequently mentioned people")
    frequently_mentioned_tokens: List[str] = Field(default=[], description="Frequently mentioned tokens")
    
    # Profile insights
    profile_summary: str = Field(description="AI-generated profile summary")
    key_insights: List[str] = Field(default=[], description="Key insights about the user")
    
    # Metadata
    created_at: str = Field(description="Profile creation timestamp")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Confidence in profile accuracy")

# ============ Tweet Filtering and Personalized Report Structures ============

class FilteredTweet(BaseModel):
    """Tweet that has been filtered based on user profile"""
    tweet_id: str
    tweet_text: str
    author: str
    created_at: str
    tags: TweetTags
    
    # Filtering metadata
    relevance_score: float = Field(ge=0.0, le=1.0, description="Relevance to user profile")
    matching_interests: List[str] = Field(default=[], description="User interests that this tweet matches")
    relevance_reason: str = Field(description="Why this tweet is relevant to the user")

class TopicInsight(BaseModel):
    """Insights about a specific topic for personalized report"""
    topic: str
    category: str = Field(description="Main category (web3, blockchain, crypto, ai)")
    
    # Analysis metrics
    total_tweets: int = Field(description="Total tweets about this topic")
    relevant_tweets: int = Field(description="Tweets relevant to user")
    sentiment_trend: str = Field(description="Overall sentiment trend")
    
    # Key information
    key_developments: List[str] = Field(default=[], description="Key developments in this topic")
    top_tweets: List[FilteredTweet] = Field(default=[], description="Most relevant tweets")
    emerging_subtopics: List[str] = Field(default=[], description="Emerging subtopics")
    
    # Actionable insights
    opportunities: List[str] = Field(default=[], description="Potential opportunities")
    risks: List[str] = Field(default=[], description="Potential risks")
    recommendations: List[str] = Field(default=[], description="Recommendations for the user")

class PersonalizedReport(BaseModel):
    """Personalized report based on user profile and filtered tweets"""
    username: str
    report_period: str = Field(description="Time period covered by report")
    generated_at: str = Field(description="Report generation timestamp")
    
    # Executive summary
    executive_summary: str = Field(description="High-level summary of key insights")
    key_highlights: List[str] = Field(default=[], description="Key highlights for the user")
    
    # Topic analysis
    topic_insights: List[TopicInsight] = Field(default=[], description="Insights by topic")
    
    # Curated content
    trending_content: List[FilteredTweet] = Field(default=[], description="Trending content in user's interests")
    alpha_opportunities: List[FilteredTweet] = Field(default=[], description="Potential alpha opportunities")
    educational_content: List[FilteredTweet] = Field(default=[], description="Educational content recommendations")
    
    # Market analysis
    market_sentiment: str = Field(description="Overall market sentiment in user's areas of interest")
    emerging_trends: List[str] = Field(default=[], description="Emerging trends relevant to user")
    
    # Actionable recommendations
    immediate_actions: List[str] = Field(default=[], description="Immediate actions to consider")
    research_suggestions: List[str] = Field(default=[], description="Areas for further research")
    networking_opportunities: List[str] = Field(default=[], description="Networking opportunities")
    
    # Report metadata
    total_tweets_analyzed: int
    total_relevant_tweets: int
    relevance_threshold: float = Field(description="Minimum relevance score used for filtering")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Confidence in report accuracy")

# ============ Tweet Tagger Class ============

class TweetTagger:
    """Enhanced tweet tagging system with user profiling and personalized reports"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.client = instructor.from_openai(OpenAI(api_key=self.api_key))
        
    def analyze_tweet(self, tweet_text: str, tweet_metadata: Dict = None) -> TweetTags:
        """Analyze a single tweet and return hierarchical tags with multi-dimensional classification"""
        
        system_prompt = """You are an expert analyst specializing in Web3, blockchain, cryptocurrency, and AI content analysis with deep understanding of hierarchical categorization and multi-dimensional tagging.

Your task is to analyze tweets and provide detailed, accurate hierarchical tagging with multi-dimensional classification.

**Hierarchical Categories:**
- Web3: defi → yield_farming/stablecoins/staking, nft → gaming/music/pfp, dao → governance/treasury
- Blockchain: layer1 → ethereum/solana/avalanche, layer2 → arbitrum/zksync/base
- Crypto: tokenomics, meme_coin → doge/pepe/wif, regulation, security
- AI: llm → gpt-4/claude/open-source, agent → autonomous/chatbot/workflow

**Multi-dimensional Classification:**
- Content Type (主题): news, analysis, opinion, tutorial, announcement, discussion, meme, alpha
- Intent (意图): informative, promotional, educational, discussion, question, announcement
- Tone (语气): professional, casual, humorous, serious, excited, neutral
- Audience (受众): beginners, intermediate, experts, developers, investors, traders, general_public
- Sentiment: positive, negative, neutral, bullish, bearish

**Guidelines:**
1. Use hierarchical thinking for main categories and specific subcategories
2. Apply multi-dimensional classification for comprehensive understanding
3. Extract specific entities (projects, tokens, people)
4. Assess technical complexity and engagement potential
5. Identify special content flags (alpha, educational, time-sensitive)
"""

        user_prompt = f"""Analyze this tweet using hierarchical categorization and multi-dimensional classification:

Tweet: "{tweet_text}"

Provide comprehensive analysis including:
1. Primary categorization (Web3, Blockchain, Crypto, AI)
2. Hierarchical tags with main categories and subcategories
3. Multi-dimensional classification (content type, intent, tone, audience, sentiment)
4. Entity extraction (projects, tokens, people)
5. Quality metrics and special flags

Be precise with subcategories and provide confidence scores."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                response_model=TweetTags,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1
            )
            return response
        except Exception as e:
            print(f"Error analyzing tweet: {e}")
            # Return default tags on error
            return TweetTags(
                is_web3_related=False,
                is_blockchain_related=False,
                is_crypto_related=False,
                is_ai_related=False,
                content_type=ContentType.DISCUSSION,
                intent=IntentType.DISCUSSION,
                tone=ToneType.NEUTRAL,
                target_audience=AudienceType.GENERAL_PUBLIC,
                sentiment=SentimentType.NEUTRAL,
                key_topics=["unknown"],
                technical_level=1,
                engagement_potential=1
            )
    
    def analyze_tweets_batch(self, tweets: List[Dict], batch_size: int = 10) -> List[TweetAnalysis]:
        """Analyze multiple tweets in batches"""
        results = []
        
        for i in range(0, len(tweets), batch_size):
            batch = tweets[i:i + batch_size]
            print(f"Processing batch {i//batch_size + 1}/{(len(tweets) + batch_size - 1)//batch_size}")
            
            for tweet in batch:
                tweet_text = tweet.get('text', '')
                tweet_id = tweet.get('id', str(i))
                created_at = tweet.get('createdAt', '')
                author = tweet.get('username', 'unknown')
                
                if not tweet_text.strip():
                    continue
                
                tags = self.analyze_tweet(tweet_text, tweet)
                
                analysis = TweetAnalysis(
                    tweet_id=tweet_id,
                    tweet_text=tweet_text,
                    created_at=created_at,
                    author=author,
                    tags=tags,
                    analysis_timestamp=datetime.now().isoformat(),
                    confidence_score=0.85  # Default confidence
                )
                
                results.append(analysis)
        
        return results
    
    def generate_user_profile(self, user_name: str, tweet_analyses: List[TweetAnalysis]) -> UserProfile:
        """Generate comprehensive user profile based on tweet analyses"""
        
        if not tweet_analyses:
            raise ValueError("No tweet analyses provided for profile generation")
        
        print(f"Generating user profile for {user_name} based on {len(tweet_analyses)} tweets")
        
        # Calculate basic statistics
        total_tweets = len(tweet_analyses)
        analysis_period = f"{tweet_analyses[-1].created_at} to {tweet_analyses[0].created_at}"
        
        # Analyze topic interests
        topic_interests = self._analyze_topic_interests(tweet_analyses)
        
        # Determine primary focus areas
        primary_focus_areas = [interest.topic for interest in topic_interests[:5] if interest.percentage > 10]
        secondary_interests = [interest.topic for interest in topic_interests[5:10] if interest.percentage > 5]
        
        # Analyze behavioral patterns
        behavior_patterns = self._analyze_behavior_patterns(tweet_analyses)
        
        # Determine user type and expertise
        user_type, expertise_areas = self._determine_user_type_and_expertise(topic_interests, behavior_patterns)
        
        # Extract frequently mentioned entities
        frequently_mentioned_projects = self._extract_frequent_entities(tweet_analyses, "mentioned_projects")
        frequently_mentioned_people = self._extract_frequent_entities(tweet_analyses, "mentioned_people")
        frequently_mentioned_tokens = self._extract_frequent_entities(tweet_analyses, "mentioned_tokens")
        
        # Generate profile summary and insights
        profile_summary, key_insights = self._generate_profile_summary_and_insights(
            user_name, topic_interests, behavior_patterns, user_type, expertise_areas
        )
        
        return UserProfile(
            username=user_name,
            analysis_period=analysis_period,
            total_tweets_analyzed=total_tweets,
            topic_interests=topic_interests,
            primary_focus_areas=primary_focus_areas,
            secondary_interests=secondary_interests,
            behavior_patterns=behavior_patterns,
            user_type=user_type,
            expertise_areas=expertise_areas,
            frequently_mentioned_projects=frequently_mentioned_projects[:10],
            frequently_mentioned_people=frequently_mentioned_people[:10],
            frequently_mentioned_tokens=frequently_mentioned_tokens[:10],
            profile_summary=profile_summary,
            key_insights=key_insights,
            created_at=datetime.now().isoformat(),
            confidence_score=min(0.95, total_tweets / 100)  # Higher confidence with more tweets
        )
    
    def _analyze_topic_interests(self, tweet_analyses: List[TweetAnalysis]) -> List[TopicInterest]:
        """Analyze user's topic interests from tweet analyses"""
        
        # Count topics by category
        topic_counts = {}
        topic_sentiments = {}
        
        for analysis in tweet_analyses:
            tags = analysis.tags
            
            # Process hierarchical tags
            for tag_list, category in [
                (tags.web3_tags, "web3"),
                (tags.blockchain_tags, "blockchain"), 
                (tags.crypto_tags, "crypto"),
                (tags.ai_tags, "ai")
            ]:
                for tag in tag_list:
                    # Main category
                    main_topic = tag.main_category
                    topic_key = f"{category}_{main_topic}"
                    
                    topic_counts[topic_key] = topic_counts.get(topic_key, 0) + 1
                    
                    # Track sentiment
                    if topic_key not in topic_sentiments:
                        topic_sentiments[topic_key] = {}
                    sentiment = tags.sentiment.value
                    topic_sentiments[topic_key][sentiment] = topic_sentiments[topic_key].get(sentiment, 0) + 1
                    
                    # Subcategories
                    for sub_cat in tag.sub_categories:
                        sub_topic_key = f"{category}_{main_topic}_{sub_cat}"
                        topic_counts[sub_topic_key] = topic_counts.get(sub_topic_key, 0) + 1
                        
                        if sub_topic_key not in topic_sentiments:
                            topic_sentiments[sub_topic_key] = {}
                        topic_sentiments[sub_topic_key][sentiment] = topic_sentiments[sub_topic_key].get(sentiment, 0) + 1
        
        total_tweets = len(tweet_analyses)
        
        # Convert to TopicInterest objects
        interests = []
        for topic, count in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True):
            if count >= 2:  # Only include topics with at least 2 mentions
                # Determine category
                category = topic.split('_')[0]
                topic_name = '_'.join(topic.split('_')[1:])
                
                interests.append(TopicInterest(
                    topic=topic_name,
                    category=category,
                    frequency=count,
                    percentage=round(count / total_tweets * 100, 2),
                    sentiment_distribution=topic_sentiments.get(topic, {}),
                    recent_activity=True,  # Would need time-based analysis
                    confidence=min(0.95, count / 10)  # Higher confidence with more mentions
                ))
        
        return interests[:20]  # Top 20 interests
    
    def _analyze_behavior_patterns(self, tweet_analyses: List[TweetAnalysis]) -> UserBehaviorPattern:
        """Analyze user's behavioral patterns"""
        
        total_tweets = len(tweet_analyses)
        
        # Calculate posting frequency (simplified - assume 30 day period)
        posting_frequency = round(total_tweets / 30, 2)
        
        # Analyze content preferences
        content_types = {}
        intents = {}
        tones = {}
        audiences = {}
        sentiments = {}
        
        technical_scores = []
        engagement_scores = []
        
        alpha_count = 0
        educational_count = 0
        
        for analysis in tweet_analyses:
            tags = analysis.tags
            
            # Count preferences
            content_types[tags.content_type] = content_types.get(tags.content_type, 0) + 1
            intents[tags.intent] = intents.get(tags.intent, 0) + 1
            tones[tags.tone] = tones.get(tags.tone, 0) + 1
            audiences[tags.target_audience] = audiences.get(tags.target_audience, 0) + 1
            sentiments[tags.sentiment] = sentiments.get(tags.sentiment, 0) + 1
            
            # Collect scores
            technical_scores.append(tags.technical_level)
            engagement_scores.append(tags.engagement_potential)
            
            # Count special flags
            if tags.is_alpha:
                alpha_count += 1
            if tags.is_educational:
                educational_count += 1
        
        # Determine typical patterns
        typical_content_type = max(content_types.items(), key=lambda x: x[1])[0]
        typical_intent = max(intents.items(), key=lambda x: x[1])[0]
        typical_tone = max(tones.items(), key=lambda x: x[1])[0]
        typical_audience = max(audiences.items(), key=lambda x: x[1])[0]
        typical_sentiment = max(sentiments.items(), key=lambda x: x[1])[0]
        
        # Calculate averages
        avg_technical_level = round(sum(technical_scores) / len(technical_scores))
        avg_engagement = round(sum(engagement_scores) / len(engagement_scores))
        
        # Determine engagement style
        if alpha_count > total_tweets * 0.1:
            engagement_style = "Alpha Sharer"
        elif educational_count > total_tweets * 0.2:
            engagement_style = "Educator"
        elif typical_intent == IntentType.PROMOTIONAL:
            engagement_style = "Promoter"
        elif typical_content_type == ContentType.ANALYSIS:
            engagement_style = "Analyst"
        else:
            engagement_style = "Community Participant"
        
        # Calculate influence score
        influence_score = min(10, max(1, int(avg_technical_level * 1.5 + avg_engagement * 0.5)))
        
        # Get top content types
        preferred_content_types = [ContentType(ct) for ct, _ in 
                                 sorted(content_types.items(), key=lambda x: x[1], reverse=True)[:3]]
        
        return UserBehaviorPattern(
            posting_frequency=posting_frequency,
            technical_level=avg_technical_level,
            engagement_style=engagement_style,
            preferred_content_types=preferred_content_types,
            typical_intent=IntentType(typical_intent),
            typical_tone=ToneType(typical_tone),
            typical_audience=AudienceType(typical_audience),
            typical_sentiment=SentimentType(typical_sentiment),
            shares_alpha=alpha_count > total_tweets * 0.05,
            creates_educational_content=educational_count > total_tweets * 0.1,
            provides_market_commentary=typical_content_type in [ContentType.ANALYSIS, ContentType.OPINION],
            influence_score=influence_score
        )
    
    def _extract_frequent_entities(self, tweet_analyses: List[TweetAnalysis], entity_type: str) -> List[str]:
        """Extract frequently mentioned entities"""
        entity_counts = {}
        
        for analysis in tweet_analyses:
            entities = getattr(analysis.tags, entity_type, [])
            for entity in entities:
                entity_counts[entity] = entity_counts.get(entity, 0) + 1
        
        # Return sorted by frequency
        return [entity for entity, _ in sorted(entity_counts.items(), key=lambda x: x[1], reverse=True)]
    
    def _determine_user_type_and_expertise(self, topic_interests: List[TopicInterest], 
                                         behavior_patterns: UserBehaviorPattern) -> tuple[str, List[str]]:
        """Determine user type and expertise areas"""
        
        if not topic_interests:
            return "General User", []
        
        # Get top interests
        top_interest = topic_interests[0]
        top_category = top_interest.category
        top_topic = top_interest.topic
        
        # Determine user type based on top interests and behavior
        if top_category == "web3":
            if "defi" in top_topic.lower():
                user_type = "DeFi Enthusiast"
            elif "nft" in top_topic.lower():
                user_type = "NFT Collector/Creator"
            elif "dao" in top_topic.lower():
                user_type = "DAO Participant"
            else:
                user_type = "Web3 Enthusiast"
        elif top_category == "blockchain":
            user_type = "Blockchain Infrastructure Expert"
        elif top_category == "crypto":
            if "meme" in top_topic.lower():
                user_type = "Meme Coin Trader"
            else:
                user_type = "Crypto Trader/Investor"
        elif top_category == "ai":
            if behavior_patterns.creates_educational_content:
                user_type = "AI Researcher/Educator"
            else:
                user_type = "AI Enthusiast"
        else:
            user_type = "Crypto Enthusiast"
        
        # Add behavior-based modifiers
        if behavior_patterns.creates_educational_content:
            user_type += " & Educator"
        elif behavior_patterns.shares_alpha:
            user_type += " & Alpha Sharer"
        
        # Extract expertise areas
        expertise_areas = []
        for interest in topic_interests[:5]:
            if interest.percentage > 15:  # Significant expertise threshold
                expertise_areas.append(interest.topic)
        
        return user_type, expertise_areas
    
    def _generate_profile_summary_and_insights(self, user_name: str, topic_interests: List[TopicInterest],
                                             behavior_patterns: UserBehaviorPattern, user_type: str, 
                                             expertise_areas: List[str]) -> tuple[str, List[str]]:
        """Generate AI-powered profile summary and insights"""
        
        # Prepare data for AI analysis
        top_interests = [f"{interest.topic} ({interest.percentage}%)" for interest in topic_interests[:5]]
        
        system_prompt = """You are an expert analyst creating user profiles based on social media activity analysis.

Generate a concise but comprehensive profile summary and key insights for a user based on their tweet analysis data.

Focus on:
1. Primary interests and expertise areas
2. Communication style and engagement patterns  
3. Technical sophistication level
4. Community role and influence
5. Unique characteristics or specializations

Provide actionable insights that would be useful for personalized content recommendations."""

        user_prompt = f"""Create a profile summary and insights for user @{user_name}:

User Type: {user_type}
Expertise Areas: {', '.join(expertise_areas)}

Top Interests: {', '.join(top_interests)}

Behavior Patterns:
- Posting Frequency: {behavior_patterns.posting_frequency} tweets/day
- Technical Level: {behavior_patterns.technical_level}/5
- Engagement Style: {behavior_patterns.engagement_style}
- Typical Intent: {behavior_patterns.typical_intent}
- Typical Tone: {behavior_patterns.typical_tone}
- Target Audience: {behavior_patterns.typical_audience}
- Shares Alpha: {behavior_patterns.shares_alpha}
- Creates Educational Content: {behavior_patterns.creates_educational_content}
- Influence Score: {behavior_patterns.influence_score}/10

Generate:
1. A 2-3 sentence profile summary in Chinese
2. 3-5 key insights about this user in Chinese

Be specific and actionable."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            
            # Parse the response to extract summary and insights
            lines = content.split('\n')
            summary_lines = []
            insights = []
            
            current_section = None
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if "总结" in line or "摘要" in line or "summary" in line.lower():
                    current_section = "summary"
                elif "洞察" in line or "insights" in line.lower() or "关键" in line:
                    current_section = "insights"
                elif line.startswith('-') or line.startswith('•') or line.startswith('*') or line.startswith('1.') or line.startswith('2.'):
                    if current_section == "insights":
                        clean_insight = line.lstrip('-•*123456789. ')
                        if len(clean_insight) > 10:
                            insights.append(clean_insight)
                elif current_section == "summary" and len(line) > 20:
                    summary_lines.append(line)
                elif current_section == "insights" and len(line) > 10 and not any(x in line for x in ["洞察", "insights", "关键"]):
                    insights.append(line)
            
            profile_summary = ' '.join(summary_lines) if summary_lines else f"{user_type}，专注于{', '.join(expertise_areas[:3])}领域。"
            key_insights = insights[:5] if insights else [
                f"主要关注{topic_interests[0].topic if topic_interests else '通用话题'}",
                f"技术水平：{behavior_patterns.technical_level}/5",
                f"参与风格：{behavior_patterns.engagement_style}",
                f"影响力评分：{behavior_patterns.influence_score}/10"
            ]
            
            return profile_summary, key_insights
            
        except Exception as e:
            print(f"Error generating profile summary: {e}")
            # Fallback to template-based summary
            profile_summary = f"{user_type}，专注于{', '.join(expertise_areas[:3])}领域。活跃于{', '.join([i.topic for i in topic_interests[:2]])}相关讨论，{behavior_patterns.engagement_style.lower()}风格。"
            key_insights = [
                f"主要关注{topic_interests[0].topic if topic_interests else '通用话题'}",
                f"技术水平：{behavior_patterns.technical_level}/5",
                f"平均每天发推{behavior_patterns.posting_frequency}条",
                f"参与风格：{behavior_patterns.engagement_style}",
                f"{'经常分享alpha信息' if behavior_patterns.shares_alpha else '专注于社区讨论'}"
            ]
            
            return profile_summary, key_insights

    def filter_tweets_by_user_profile(self, user_profile: UserProfile, tweet_analyses: List[TweetAnalysis], 
                                    relevance_threshold: float = 0.6) -> List[FilteredTweet]:
        """Filter tweets based on user profile and interests"""
        
        print(f"Filtering {len(tweet_analyses)} tweets for user {user_profile.username} with threshold {relevance_threshold}")
        
        # Extract user interest keywords
        interest_keywords = set()
        user_topics = set()
        
        for interest in user_profile.topic_interests:
            # Add topic as keyword
            topic_parts = interest.topic.lower().split('_')
            interest_keywords.update(topic_parts)
            user_topics.add(interest.topic.lower())
        
        # Add frequently mentioned entities
        interest_keywords.update([p.lower() for p in user_profile.frequently_mentioned_projects])
        interest_keywords.update([t.lower() for t in user_profile.frequently_mentioned_tokens])
        
        filtered_tweets = []
        
        for tweet_analysis in tweet_analyses:
            # Skip user's own tweets
            if tweet_analysis.author.lower() == user_profile.username.lower():
                continue
                
            relevance_score = self._calculate_tweet_relevance(tweet_analysis, user_profile, interest_keywords, user_topics)
            
            if relevance_score >= relevance_threshold:
                matching_interests = self._identify_matching_interests(tweet_analysis, user_profile)
                relevance_reason = self._generate_relevance_explanation(tweet_analysis, user_profile, matching_interests, relevance_score)
                
                filtered_tweet = FilteredTweet(
                    tweet_id=tweet_analysis.tweet_id,
                    tweet_text=tweet_analysis.tweet_text,
                    author=tweet_analysis.author,
                    created_at=tweet_analysis.created_at,
                    tags=tweet_analysis.tags,
                    relevance_score=relevance_score,
                    matching_interests=matching_interests,
                    relevance_reason=relevance_reason
                )
                
                filtered_tweets.append(filtered_tweet)
        
        # Sort by relevance score
        filtered_tweets.sort(key=lambda x: x.relevance_score, reverse=True)
        
        print(f"Filtered to {len(filtered_tweets)} relevant tweets")
        return filtered_tweets
    
    def _calculate_tweet_relevance(self, tweet_analysis: TweetAnalysis, user_profile: UserProfile, 
                                 interest_keywords: set, user_topics: set) -> float:
        """Calculate relevance score for a tweet based on user profile"""
        
        score = 0.0
        tags = tweet_analysis.tags
        
        # Check hierarchical tag matches
        for tag_list in [tags.web3_tags, tags.blockchain_tags, tags.crypto_tags, tags.ai_tags]:
            for tag in tag_list:
                # Main category match
                if tag.main_category.lower() in user_topics:
                    score += 0.4 * tag.confidence
                elif tag.main_category.lower() in interest_keywords:
                    score += 0.3 * tag.confidence
                
                # Subcategory match
                for sub_cat in tag.sub_categories:
                    sub_topic = f"{tag.main_category}_{sub_cat}".lower()
                    if sub_topic in user_topics:
                        score += 0.3 * tag.confidence
                    elif sub_cat.lower() in interest_keywords:
                        score += 0.2 * tag.confidence
        
        # Check mentioned entities
        for entity in tags.mentioned_projects + tags.mentioned_tokens:
            if entity.lower() in interest_keywords:
                score += 0.25
        
        # Check key topics
        for topic in tags.key_topics:
            if any(keyword in topic.lower() for keyword in interest_keywords):
                score += 0.15
        
        # Content type preference match
        if tags.content_type in user_profile.behavior_patterns.preferred_content_types:
            score += 0.1
        
        # Special content boosts
        if tags.is_alpha and user_profile.behavior_patterns.shares_alpha:
            score += 0.2
        
        if tags.is_educational and user_profile.behavior_patterns.creates_educational_content:
            score += 0.15
        
        # Technical level match
        user_tech_level = user_profile.behavior_patterns.technical_level
        tweet_tech_level = tags.technical_level
        
        # Prefer content slightly above or at user's level
        if tweet_tech_level <= user_tech_level + 1:
            score += 0.1
        elif tweet_tech_level > user_tech_level + 2:
            score -= 0.1  # Penalize content that's too advanced
        
        # Audience match
        if tags.target_audience == user_profile.behavior_patterns.typical_audience:
            score += 0.1
        
        return min(1.0, score)
    
    def _identify_matching_interests(self, tweet_analysis: TweetAnalysis, user_profile: UserProfile) -> List[str]:
        """Identify which user interests this tweet matches"""
        
        matching_interests = []
        tags = tweet_analysis.tags
        
        # Check against user's topic interests
        for interest in user_profile.topic_interests[:10]:  # Top 10 interests
            interest_topic = interest.topic.lower()
            
            # Check hierarchical tags
            for tag_list in [tags.web3_tags, tags.blockchain_tags, tags.crypto_tags, tags.ai_tags]:
                for tag in tag_list:
                    if tag.main_category.lower() == interest_topic:
                        matching_interests.append(interest.topic)
                        break
                    
                    for sub_cat in tag.sub_categories:
                        sub_topic = f"{tag.main_category}_{sub_cat}".lower()
                        if sub_topic == interest_topic:
                            matching_interests.append(interest.topic)
                            break
        
        return list(set(matching_interests))  # Remove duplicates
    
    def _generate_relevance_explanation(self, tweet_analysis: TweetAnalysis, user_profile: UserProfile, 
                                      matching_interests: List[str], relevance_score: float) -> str:
        """Generate explanation for why this tweet is relevant"""
        
        reasons = []
        tags = tweet_analysis.tags
        
        # Interest matches
        if matching_interests:
            reasons.append(f"匹配您的兴趣：{', '.join(matching_interests[:2])}")
        
        # Entity matches
        mentioned_entities = []
        for entity in tags.mentioned_projects:
            if entity in user_profile.frequently_mentioned_projects[:5]:
                mentioned_entities.append(entity)
        
        if mentioned_entities:
            reasons.append(f"提及您关注的项目：{', '.join(mentioned_entities[:2])}")
        
        # Special content flags
        if tags.is_alpha and user_profile.behavior_patterns.shares_alpha:
            reasons.append("包含潜在alpha信息")
        
        if tags.is_educational and user_profile.behavior_patterns.creates_educational_content:
            reasons.append("教育性内容")
        
        # Content type match
        if tags.content_type in user_profile.behavior_patterns.preferred_content_types:
            reasons.append(f"符合您偏好的内容类型：{tags.content_type}")
        
        # High relevance score
        if relevance_score > 0.8:
            reasons.append(f"高相关性评分：{relevance_score:.2f}")
        
        if not reasons:
            reasons.append(f"基于内容分析的相关性评分：{relevance_score:.2f}")
        
        return "；".join(reasons[:3])  # Limit to 3 main reasons

    def generate_personalized_report(self, user_profile: UserProfile, filtered_tweets: List[FilteredTweet], 
                                   report_period: str = "最近7天") -> PersonalizedReport:
        """Generate personalized report based on user profile and filtered tweets"""
        
        print(f"Generating personalized report for {user_profile.username} with {len(filtered_tweets)} tweets")
        
        # Analyze topics
        topic_insights = self._generate_topic_insights(user_profile, filtered_tweets)
        
        # Categorize content
        trending_content = self._identify_trending_content(filtered_tweets)
        alpha_opportunities = self._identify_alpha_opportunities(filtered_tweets)
        educational_content = self._identify_educational_content(filtered_tweets)
        
        # Generate market analysis
        market_sentiment = self._analyze_market_sentiment(filtered_tweets, user_profile)
        emerging_trends = self._identify_emerging_trends(filtered_tweets, user_profile)
        
        # Generate AI-powered insights
        executive_summary, key_highlights, immediate_actions, research_suggestions, networking_opportunities = \
            self._generate_ai_report_insights(user_profile, topic_insights, trending_content, alpha_opportunities)
        
        return PersonalizedReport(
            username=user_profile.username,
            report_period=report_period,
            generated_at=datetime.now().isoformat(),
            executive_summary=executive_summary,
            key_highlights=key_highlights,
            topic_insights=topic_insights,
            trending_content=trending_content[:10],
            alpha_opportunities=alpha_opportunities[:5],
            educational_content=educational_content[:8],
            market_sentiment=market_sentiment,
            emerging_trends=emerging_trends,
            immediate_actions=immediate_actions,
            research_suggestions=research_suggestions,
            networking_opportunities=networking_opportunities,
            total_tweets_analyzed=len(filtered_tweets),
            total_relevant_tweets=len(filtered_tweets),
            relevance_threshold=0.6,
            confidence_score=min(0.95, len(filtered_tweets) / 50)
        )
    
    def _generate_topic_insights(self, user_profile: UserProfile, filtered_tweets: List[FilteredTweet]) -> List[TopicInsight]:
        """Generate insights for each topic based on filtered tweets"""
        
        # Group tweets by topic
        topic_groups = {}
        
        for tweet in filtered_tweets:
            for interest in tweet.matching_interests:
                if interest not in topic_groups:
                    topic_groups[interest] = []
                topic_groups[interest].append(tweet)
        
        insights = []
        
        for topic, tweets in topic_groups.items():
            if len(tweets) < 2:  # Skip topics with too few tweets
                continue
            
            # Find the category for this topic
            category = "general"
            for user_interest in user_profile.topic_interests:
                if user_interest.topic == topic:
                    category = user_interest.category
                    break
            
            # Analyze sentiment trend
            sentiments = [tweet.tags.sentiment.value for tweet in tweets]
            sentiment_counts = {}
            for sentiment in sentiments:
                sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
            
            dominant_sentiment = max(sentiment_counts.items(), key=lambda x: x[1])[0]
            sentiment_trend = f"主要情绪：{dominant_sentiment} ({sentiment_counts[dominant_sentiment]}/{len(tweets)})"
            
            # Extract key developments
            key_developments = []
            alpha_tweets = [t for t in tweets if t.tags.is_alpha]
            if alpha_tweets:
                key_developments.extend([f"Alpha机会：{t.tweet_text[:50]}..." for t in alpha_tweets[:2]])
            
            news_tweets = [t for t in tweets if t.tags.content_type == ContentType.NEWS]
            if news_tweets:
                key_developments.extend([f"新闻：{t.tweet_text[:50]}..." for t in news_tweets[:2]])
            
            # Get top tweets (highest relevance)
            top_tweets = sorted(tweets, key=lambda x: x.relevance_score, reverse=True)[:3]
            
            # Generate opportunities and risks
            opportunities = []
            risks = []
            recommendations = []
            
            if alpha_tweets:
                opportunities.append("发现潜在alpha机会，建议深入研究")
            
            if any(t.tags.is_time_sensitive for t in tweets):
                recommendations.append("包含时效性信息，建议及时关注")
            
            if len(tweets) > 5:
                recommendations.append(f"该话题讨论活跃（{len(tweets)}条相关推文），建议持续关注")
            
            insights.append(TopicInsight(
                topic=topic,
                category=category,
                total_tweets=len(tweets),
                relevant_tweets=len(tweets),
                sentiment_trend=sentiment_trend,
                key_developments=key_developments[:3],
                top_tweets=top_tweets,
                emerging_subtopics=[],  # Would need more sophisticated analysis
                opportunities=opportunities,
                risks=risks,
                recommendations=recommendations
            ))
        
        return sorted(insights, key=lambda x: x.total_tweets, reverse=True)[:8]
    
    def _identify_trending_content(self, filtered_tweets: List[FilteredTweet]) -> List[FilteredTweet]:
        """Identify trending content based on engagement potential and recency"""
        
        # Score tweets based on engagement potential and other factors
        scored_tweets = []
        
        for tweet in filtered_tweets:
            score = tweet.tags.engagement_potential * 0.4
            score += tweet.relevance_score * 0.3
            
            # Boost for special content
            if tweet.tags.is_alpha:
                score += 0.2
            if tweet.tags.content_type in [ContentType.NEWS, ContentType.ANNOUNCEMENT]:
                score += 0.1
            
            scored_tweets.append((tweet, score))
        
        # Sort by score and return top tweets
        scored_tweets.sort(key=lambda x: x[1], reverse=True)
        return [tweet for tweet, _ in scored_tweets[:15]]
    
    def _identify_alpha_opportunities(self, filtered_tweets: List[FilteredTweet]) -> List[FilteredTweet]:
        """Identify potential alpha opportunities"""
        
        alpha_tweets = [tweet for tweet in filtered_tweets if tweet.tags.is_alpha]
        
        # Sort by relevance score
        alpha_tweets.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return alpha_tweets[:8]
    
    def _identify_educational_content(self, filtered_tweets: List[FilteredTweet]) -> List[FilteredTweet]:
        """Identify educational content"""
        
        educational_tweets = [tweet for tweet in filtered_tweets if tweet.tags.is_educational]
        
        # Also include tutorials and analysis
        for tweet in filtered_tweets:
            if tweet.tags.content_type in [ContentType.TUTORIAL, ContentType.ANALYSIS] and tweet not in educational_tweets:
                educational_tweets.append(tweet)
        
        # Sort by relevance score
        educational_tweets.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return educational_tweets[:10]
    
    def _analyze_market_sentiment(self, filtered_tweets: List[FilteredTweet], user_profile: UserProfile) -> str:
        """Analyze overall market sentiment in user's areas of interest"""
        
        sentiments = [tweet.tags.sentiment.value for tweet in filtered_tweets]
        
        if not sentiments:
            return "中性"
        
        sentiment_counts = {}
        for sentiment in sentiments:
            sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
        
        total = len(sentiments)
        
        # Calculate percentages
        positive_pct = (sentiment_counts.get('positive', 0) + sentiment_counts.get('bullish', 0)) / total * 100
        negative_pct = (sentiment_counts.get('negative', 0) + sentiment_counts.get('bearish', 0)) / total * 100
        neutral_pct = sentiment_counts.get('neutral', 0) / total * 100
        
        if positive_pct > 50:
            return f"积极 ({positive_pct:.1f}%积极情绪)"
        elif negative_pct > 50:
            return f"消极 ({negative_pct:.1f}%消极情绪)"
        elif positive_pct > negative_pct:
            return f"偏积极 (积极{positive_pct:.1f}% vs 消极{negative_pct:.1f}%)"
        elif negative_pct > positive_pct:
            return f"偏消极 (消极{negative_pct:.1f}% vs 积极{positive_pct:.1f}%)"
        else:
            return f"中性 (中性情绪{neutral_pct:.1f}%)"
    
    def _identify_emerging_trends(self, filtered_tweets: List[FilteredTweet], user_profile: UserProfile) -> List[str]:
        """Identify emerging trends from filtered tweets"""
        
        # Extract key topics and projects mentioned
        topic_mentions = {}
        project_mentions = {}
        
        for tweet in filtered_tweets:
            # Count key topics
            for topic in tweet.tags.key_topics:
                topic_mentions[topic] = topic_mentions.get(topic, 0) + 1
            
            # Count mentioned projects
            for project in tweet.tags.mentioned_projects:
                project_mentions[project] = project_mentions.get(project, 0) + 1
        
        trends = []
        
        # Identify trending topics (mentioned multiple times)
        for topic, count in topic_mentions.items():
            if count >= 3:  # Mentioned in at least 3 tweets
                trends.append(f"{topic}相关讨论增加")
        
        # Identify trending projects
        for project, count in project_mentions.items():
            if count >= 2 and project not in user_profile.frequently_mentioned_projects[:3]:
                trends.append(f"{project}项目获得关注")
        
        return trends[:5]
    
    def _generate_ai_report_insights(self, user_profile: UserProfile, topic_insights: List[TopicInsight], 
                                   trending_content: List[FilteredTweet], alpha_opportunities: List[FilteredTweet]) -> tuple:
        """Generate AI-powered report insights"""
        
        # Prepare data for AI analysis
        top_topics = [insight.topic for insight in topic_insights[:3]]
        alpha_count = len(alpha_opportunities)
        trending_count = len(trending_content)
        
        system_prompt = """You are an expert crypto/Web3 analyst creating personalized reports for users based on their interests and recent market activity.

Generate actionable insights and recommendations in Chinese that would be valuable for the user based on their profile and the analyzed content.

Focus on:
1. Executive summary highlighting key developments
2. Key highlights that matter to this specific user
3. Immediate actions they should consider
4. Research areas worth exploring
5. Networking opportunities

Be specific, actionable, and tailored to the user's interests and expertise level."""

        user_prompt = f"""Generate personalized report insights for user @{user_profile.username}:

User Profile:
- Type: {user_profile.user_type}
- Primary Interests: {', '.join(user_profile.primary_focus_areas)}
- Technical Level: {user_profile.behavior_patterns.technical_level}/5
- Engagement Style: {user_profile.behavior_patterns.engagement_style}

Content Analysis:
- Top Active Topics: {', '.join(top_topics)}
- Alpha Opportunities Found: {alpha_count}
- Trending Content Items: {trending_count}
- Key Topic Insights: {len(topic_insights)} topics analyzed

Generate in Chinese:
1. Executive Summary (2-3 sentences)
2. Key Highlights (3-4 bullet points)
3. Immediate Actions (2-3 actionable items)
4. Research Suggestions (2-3 areas to explore)
5. Networking Opportunities (1-2 suggestions)

Be specific and actionable for this user's profile."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            
            # Parse the response
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            
            executive_summary = ""
            key_highlights = []
            immediate_actions = []
            research_suggestions = []
            networking_opportunities = []
            
            current_section = None
            
            for line in lines:
                # Identify sections
                if "总结" in line or "摘要" in line or "executive" in line.lower():
                    current_section = "summary"
                    continue
                elif "亮点" in line or "highlights" in line.lower() or "要点" in line:
                    current_section = "highlights"
                    continue
                elif "行动" in line or "actions" in line.lower() or "建议" in line:
                    current_section = "actions"
                    continue
                elif "研究" in line or "research" in line.lower():
                    current_section = "research"
                    continue
                elif "网络" in line or "networking" in line.lower() or "社交" in line:
                    current_section = "networking"
                    continue
                
                # Process content based on current section
                if current_section == "summary" and len(line) > 10:
                    executive_summary += line + " "
                elif current_section == "highlights" and (line.startswith('-') or line.startswith('•') or line.startswith('*')):
                    clean_line = line.lstrip('-•* ')
                    if len(clean_line) > 5:
                        key_highlights.append(clean_line)
                elif current_section == "actions" and (line.startswith('-') or line.startswith('•') or line.startswith('*')):
                    clean_line = line.lstrip('-•* ')
                    if len(clean_line) > 5:
                        immediate_actions.append(clean_line)
                elif current_section == "research" and (line.startswith('-') or line.startswith('•') or line.startswith('*')):
                    clean_line = line.lstrip('-•* ')
                    if len(clean_line) > 5:
                        research_suggestions.append(clean_line)
                elif current_section == "networking" and (line.startswith('-') or line.startswith('•') or line.startswith('*')):
                    clean_line = line.lstrip('-•* ')
                    if len(clean_line) > 5:
                        networking_opportunities.append(clean_line)
            
            # Fallback if parsing failed
            if not executive_summary:
                executive_summary = f"基于您在{', '.join(top_topics)}领域的兴趣，本期发现{alpha_count}个潜在机会和{trending_count}个热门话题。"
            
            if not key_highlights:
                key_highlights = [
                    f"{top_topics[0] if top_topics else '主要关注领域'}活动增加",
                    f"发现{alpha_count}个潜在alpha机会" if alpha_count > 0 else "市场讨论活跃",
                    f"识别出{len(topic_insights)}个相关话题趋势"
                ]
            
            if not immediate_actions:
                immediate_actions = [
                    "关注标记的alpha机会推文" if alpha_count > 0 else "持续关注热门讨论",
                    "深入研究相关性评分最高的内容"
                ]
            
            if not research_suggestions:
                research_suggestions = [
                    f"深入了解{top_topics[0] if top_topics else '主要兴趣领域'}的最新发展",
                    "关注新兴项目和技术趋势"
                ]
            
            if not networking_opportunities:
                networking_opportunities = [
                    "关注活跃讨论者，寻找合作机会"
                ]
            
            return (
                executive_summary.strip(),
                key_highlights[:4],
                immediate_actions[:3],
                research_suggestions[:3],
                networking_opportunities[:2]
            )
            
        except Exception as e:
            print(f"Error generating AI report insights: {e}")
            # Fallback insights
            return (
                f"基于您在{', '.join(user_profile.primary_focus_areas[:2])}领域的兴趣，本期分析了{len(topic_insights)}个相关话题。",
                [
                    f"发现{alpha_count}个潜在机会" if alpha_count > 0 else "识别多个讨论热点",
                    f"在{top_topics[0] if top_topics else '主要领域'}中活动增加",
                    f"总计{trending_count}个热门内容值得关注"
                ],
                [
                    "查看高相关性评分的推文",
                    "关注alpha机会标记的内容" if alpha_count > 0 else "跟进热门讨论"
                ],
                [
                    f"深入研究{user_profile.primary_focus_areas[0] if user_profile.primary_focus_areas else '相关领域'}",
                    "关注新兴趋势和项目动态"
                ],
                [
                    "与活跃讨论者建立联系"
                ]
            )

    # ============ Data Persistence Functions ============
    
    def save_tweet_analyses(self, username: str, tweet_analyses: List[TweetAnalysis], output_dir: str = "output") -> str:
        """Save tweet analyses to JSON file"""
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"{username}_tweet_analyses.json"
        filepath = os.path.join(output_dir, filename)
        
        # Convert to dict for JSON serialization
        data = {
            "username": username,
            "total_tweets": len(tweet_analyses),
            "generated_at": datetime.now().isoformat(),
            "analyses": [analysis.model_dump() for analysis in tweet_analyses]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"Saved {len(tweet_analyses)} tweet analyses to {filepath}")
        return filepath
    
    def save_user_profile(self, user_profile: UserProfile, output_dir: str = "output") -> str:
        """Save user profile to JSON file"""
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"{user_profile.username}_user_profile.json"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(user_profile.model_dump(), f, ensure_ascii=False, indent=2)
        
        print(f"Saved user profile to {filepath}")
        return filepath
    
    def save_personalized_report(self, report: PersonalizedReport, output_dir: str = "output") -> str:
        """Save personalized report to JSON file"""
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"{report.username}_personalized_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report.model_dump(), f, ensure_ascii=False, indent=2)
        
        print(f"Saved personalized report to {filepath}")
        return filepath
    
    def save_filtered_tweets(self, username: str, filtered_tweets: List[FilteredTweet], output_dir: str = "output") -> str:
        """Save filtered tweets to JSON file"""
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"{username}_filtered_tweets.json"
        filepath = os.path.join(output_dir, filename)
        
        data = {
            "username": username,
            "total_filtered_tweets": len(filtered_tweets),
            "generated_at": datetime.now().isoformat(),
            "filtered_tweets": [tweet.model_dump() for tweet in filtered_tweets]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"Saved {len(filtered_tweets)} filtered tweets to {filepath}")
        return filepath
    
    def load_user_profile(self, username: str, input_dir: str = "output") -> Optional[UserProfile]:
        """Load user profile from JSON file"""
        filename = f"{username}_user_profile.json"
        filepath = os.path.join(input_dir, filename)
        
        if not os.path.exists(filepath):
            print(f"User profile file not found: {filepath}")
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return UserProfile(**data)
        except Exception as e:
            print(f"Error loading user profile: {e}")
            return None
    
    def load_tweet_analyses(self, username: str, input_dir: str = "output") -> Optional[List[TweetAnalysis]]:
        """Load tweet analyses from JSON file"""
        filename = f"{username}_tweet_analyses.json"
        filepath = os.path.join(input_dir, filename)
        
        if not os.path.exists(filepath):
            print(f"Tweet analyses file not found: {filepath}")
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            analyses = []
            for analysis_data in data.get("analyses", []):
                analyses.append(TweetAnalysis(**analysis_data))
            
            return analyses
        except Exception as e:
            print(f"Error loading tweet analyses: {e}")
            return None

# ============ Workflow Functions ============

def analyze_user_tweets_and_generate_profile(username: str, api_key: Optional[str] = None, 
                                            output_dir: str = "output") -> tuple[UserProfile, List[TweetAnalysis]]:
    """Complete workflow: Load user tweets → Analyze → Generate profile"""
    
    print(f"Starting complete analysis for user: {username}")
    
    # Initialize tagger
    tagger = TweetTagger(api_key=api_key)
    
    # Load user tweets
    print("Loading user tweets...")
    tweets = load_user_tweets(username)
    
    if not tweets:
        raise ValueError(f"No tweets found for user {username}")
    
    print(f"Loaded {len(tweets)} tweets for {username}")
    
    # Analyze tweets
    print("Analyzing tweets...")
    tweet_analyses = tagger.analyze_tweets_batch(tweets)
    
    if not tweet_analyses:
        raise ValueError("No tweet analyses generated")
    
    # Generate user profile
    print("Generating user profile...")
    user_profile = tagger.generate_user_profile(username, tweet_analyses)
    
    # Save results
    tagger.save_tweet_analyses(username, tweet_analyses, output_dir)
    tagger.save_user_profile(user_profile, output_dir)
    
    print(f"✅ Analysis complete for {username}")
    print(f"📊 Profile: {user_profile.user_type}")
    print(f"🎯 Primary interests: {', '.join(user_profile.primary_focus_areas[:3])}")
    print(f"📈 Technical level: {user_profile.behavior_patterns.technical_level}/5")
    
    return user_profile, tweet_analyses

def filter_tweets_and_generate_report(username: str, kol_tweets: List[Dict], 
                                     user_profile: Optional[UserProfile] = None,
                                     api_key: Optional[str] = None, 
                                     output_dir: str = "output") -> PersonalizedReport:
    """Complete workflow: Filter KOL tweets → Generate personalized report"""
    
    print(f"Generating personalized report for {username}")
    
    # Initialize tagger
    tagger = TweetTagger(api_key=api_key)
    
    # Load user profile if not provided
    if user_profile is None:
        user_profile = tagger.load_user_profile(username, output_dir)
        if user_profile is None:
            raise ValueError(f"User profile not found for {username}. Please run analysis first.")
    
    print(f"Using profile: {user_profile.user_type}")
    
    # Analyze KOL tweets
    print(f"Analyzing {len(kol_tweets)} KOL tweets...")
    kol_analyses = tagger.analyze_tweets_batch(kol_tweets)
    
    # Filter tweets based on user profile
    print("Filtering tweets based on user interests...")
    filtered_tweets = tagger.filter_tweets_by_user_profile(user_profile, kol_analyses)
    
    if not filtered_tweets:
        print("⚠️ No relevant tweets found for this user profile")
        # Create empty report
        return PersonalizedReport(
            username=username,
            report_period="最近7天",
            generated_at=datetime.now().isoformat(),
            executive_summary="本期未发现与您兴趣高度相关的内容。",
            key_highlights=["暂无相关内容"],
            topic_insights=[],
            trending_content=[],
            alpha_opportunities=[],
            educational_content=[],
            market_sentiment="中性",
            emerging_trends=[],
            immediate_actions=["继续关注相关话题发展"],
            research_suggestions=["扩展关注领域"],
            networking_opportunities=[],
            total_tweets_analyzed=len(kol_analyses),
            total_relevant_tweets=0,
            relevance_threshold=0.6,
            confidence_score=0.5
        )
    
    # Generate personalized report
    print("Generating personalized report...")
    report = tagger.generate_personalized_report(user_profile, filtered_tweets)
    
    # Save results
    tagger.save_filtered_tweets(username, filtered_tweets, output_dir)
    tagger.save_personalized_report(report, output_dir)
    
    print(f"✅ Report generated for {username}")
    print(f"📊 Relevant tweets: {len(filtered_tweets)}/{len(kol_analyses)}")
    print(f"🎯 Topics analyzed: {len(report.topic_insights)}")
    print(f"⚡ Alpha opportunities: {len(report.alpha_opportunities)}")
    
    return report

def complete_personalized_analysis(username: str, kol_tweets: List[Dict], 
                                 api_key: Optional[str] = None, 
                                 output_dir: str = "output") -> tuple[UserProfile, PersonalizedReport]:
    """Complete end-to-end workflow: User analysis → Tweet filtering → Report generation"""
    
    print(f"🚀 Starting complete personalized analysis for {username}")
    
    # Step 1: Analyze user tweets and generate profile
    try:
        user_profile, tweet_analyses = analyze_user_tweets_and_generate_profile(
            username, api_key, output_dir
        )
    except Exception as e:
        print(f"❌ Error in user analysis: {e}")
        raise
    
    # Step 2: Filter KOL tweets and generate report
    try:
        report = filter_tweets_and_generate_report(
            username, kol_tweets, user_profile, api_key, output_dir
        )
    except Exception as e:
        print(f"❌ Error in report generation: {e}")
        raise
    
    print(f"🎉 Complete analysis finished for {username}")
    print(f"📁 Results saved to: {output_dir}/")
    
    return user_profile, report

def batch_generate_reports(usernames: List[str], kol_tweets: List[Dict], 
                          api_key: Optional[str] = None, 
                          output_dir: str = "output") -> Dict[str, PersonalizedReport]:
    """Generate personalized reports for multiple users"""
    
    print(f"📊 Batch generating reports for {len(usernames)} users")
    
    reports = {}
    
    for i, username in enumerate(usernames, 1):
        print(f"\n[{i}/{len(usernames)}] Processing {username}...")
        
        try:
            _, report = complete_personalized_analysis(username, kol_tweets, api_key, output_dir)
            reports[username] = report
            print(f"✅ {username} completed")
        except Exception as e:
            print(f"❌ {username} failed: {e}")
            continue
    
    print(f"\n🎉 Batch processing complete: {len(reports)}/{len(usernames)} successful")
    return reports

# ============ Demo and Testing Functions ============

def demo_tweet_analysis(sample_tweets: List[str], api_key: Optional[str] = None):
    """Demo function to show tweet analysis capabilities"""
    
    print("🔍 Demo: Tweet Analysis")
    
    tagger = TweetTagger(api_key=api_key)
    
    for i, tweet_text in enumerate(sample_tweets, 1):
        print(f"\n--- Tweet {i} ---")
        print(f"Text: {tweet_text}")
        
        tags = tagger.analyze_tweet(tweet_text)
        
        print(f"Categories: Web3={tags.is_web3_related}, Blockchain={tags.is_blockchain_related}, "
              f"Crypto={tags.is_crypto_related}, AI={tags.is_ai_related}")
        print(f"Content Type: {tags.content_type}")
        print(f"Intent: {tags.intent}")
        print(f"Tone: {tags.tone}")
        print(f"Technical Level: {tags.technical_level}/5")
        print(f"Key Topics: {', '.join(tags.key_topics)}")
        
        if tags.mentioned_projects:
            print(f"Projects: {', '.join(tags.mentioned_projects)}")
        if tags.mentioned_tokens:
            print(f"Tokens: {', '.join(tags.mentioned_tokens)}")

def demo_user_profile_analysis(username: str, api_key: Optional[str] = None):
    """Demo function to show user profile analysis"""
    
    print(f"👤 Demo: User Profile Analysis for {username}")
    
    try:
        user_profile, _ = analyze_user_tweets_and_generate_profile(username, api_key)
        
        print(f"\n📊 User Profile Summary:")
        print(f"Type: {user_profile.user_type}")
        print(f"Primary Focus: {', '.join(user_profile.primary_focus_areas)}")
        print(f"Technical Level: {user_profile.behavior_patterns.technical_level}/5")
        print(f"Engagement Style: {user_profile.behavior_patterns.engagement_style}")
        print(f"Influence Score: {user_profile.behavior_patterns.influence_score}/10")
        
        print(f"\n🎯 Top Interests:")
        for interest in user_profile.topic_interests[:5]:
            print(f"  - {interest.topic}: {interest.percentage}% ({interest.frequency} tweets)")
        
        print(f"\n💡 Key Insights:")
        for insight in user_profile.key_insights:
            print(f"  - {insight}")
            
    except Exception as e:
        print(f"❌ Demo failed: {e}")

if __name__ == "__main__":
    # Example usage
    sample_tweets = [
        "Just discovered this new DeFi protocol with 20% APY on stablecoins. DYOR but looks promising! 🚀",
        "The latest GPT-4 update is incredible. The reasoning capabilities are getting scary good.",
        "PEPE is pumping again! Meme season is back 🐸💚",
        "Ethereum's next upgrade will reduce gas fees by 50%. This is huge for adoption!"
    ]
    
    print("🎯 Tweet Tagger Demo")
    demo_tweet_analysis(sample_tweets)
