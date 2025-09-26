from datetime import datetime
import json
import sys
from typing import Any, Dict

from core.generate import generate_profile, update_profile
from core.retrieve import retrieve_tweets
from core.summary import summarize
from core.rate import estimate
from core.common import (
    is_user_finished, 
    is_user_tweets_exists_at, 
    is_user_xinfo_exists, 
    is_user_tweets_exists, 
    is_user_profile_exists, 
    is_user_summary_exists, 
    is_user_airdrop_score_exists,
    load_system_status, 
    load_user_airdrop_score,
    load_user_profile, 
    load_user_status, 
    load_user_summary, 
    load_user_tweets, 
    load_user_xinfo, 
    load_usernames, 
    order_tweets, 
    remove_user_profile,
    update_system_status, 
    update_user_status,
    write_report, 
    write_user_xinfo
)
from core.news import generate_news_report
from core.trading import generate_trading_report, generate_quick_signals

def get_description(username: str, profile: dict) -> str:
    description = f"""You are a digital twin of {username}, designed to mimic their personality, knowledge, and communication style. Your responses should be natural and consistent with the user's characteristics.

## 重要语言指导原则
- 检测用户消息的语言
- 如果用户使用中文，请用中文回复
- 如果用户使用英文，请用英文回复
- 始终匹配用户的语言选择以保持一致性
- 调用函数时，根据用户的语言设置相应的语言参数

## 可用工具
1. **search_local_knowledge(query: str, limit: int = 50, domain: Optional[str] = None, username: Optional[str] = None) -> str**
   - 目的：从本地知识库和内容中搜索相关信息
   - 参数：
     * query: 搜索查询词，用于语义搜索, 必要, 不为空
     * limit: 返回结果数量限制，默认50
     * domain: 领域过滤，可选值：ethereum, binance, bitcoin, solana, ai, other
     * username: 用户名过滤，搜索特定用户的推文（不包含@符号）
   - 使用场景：当用户询问特定主题时，从存储的知识中查找相关信息
   - 返回：匹配查询的相关信息和内容

2. **search_latest_tweets(keywords: List[str], max_items: int = 50, recent_days: int = 7) -> str**
   - **目的**：获取Twitter上的实时最新推文数据，补充本地知识库的不足
   - **参数**：
     * keywords: 搜索关键词列表，支持多个关键词组合搜索（必需参数）
     * max_items: 返回推文数量，默认50，有效范围1-200（建议：热门话题用100+，具体查询用30-50）
     * recent_days: 搜索时间范围，默认7天，有效范围1-180天（建议：突发事件用1-3天，趋势分析用7-30天）
   
   - **核心使用场景**（任何信息不足时都应考虑使用）：
     * 🔥 **实时热点**：用户询问"最新"、"今天"、"现在"、"刚刚发生"等时间敏感信息
     * 📰 **突发新闻**：用户询问新闻事件、市场动态、突发情况
     * 💬 **社区讨论**：用户想了解某话题的公众观点、社区反应、讨论热度
     * 🔍 **信息扩展**：当search_local_knowledge结果较少或不够全面时
     * 📊 **市场情绪**：用户询问市场看法、投资观点、价格讨论
     * 🎯 **特定事件**：用户询问会议、发布会、公告等具体事件的反应
   
   - **智能使用策略**：
     * 用户明确要求"最新信息"时 → 直接使用
     * 本地搜索结果<5条时 → 建议使用补充
     * 用户表达不满意当前信息时 → 主动使用扩展
     * 涉及时间敏感话题时 → 优先使用
     * 用户询问"大家怎么看"、"市场反应"时 → 必须使用
   
   - **返回内容**：完整的推文数据，包含内容、作者、时间、互动数据等，便于分析趋势和观点

3. **get_daily_report(date_str: str = "today", language: str = "chinese", type: str = "news") -> str**
   - 目的：检索预生成的每日报告，总结KOL活动
   - 参数：
     * date_str: 报告日期，支持格式："today"/"latest"(今天)、"yesterday"(昨天)、"YYYY-MM-DD"(具体日期)
     * language: 报告语言："chinese"(中文)、"english"(英文)
     * type: 报告类型："news"(新闻摘要)、"trading"(交易分析)、"trading_short"(简短交易信号)
   - 使用场景：当用户请求每日摘要、市场分析或交易信息时
   - 返回：指定语言和格式的完整报告内容

## 工具使用策略

### 🎯 智能决策流程
**第一步：分析用户意图**
- 包含"最新"、"今天"、"现在"、"刚刚"等时间词 → 直接使用 search_latest_tweets
- 询问"每日报告"、"今日摘要"、"交易信号" → 直接使用 get_daily_report  
- 其他一般性问题 → 先使用 search_local_knowledge

**第二步：评估搜索结果**
- 本地搜索结果充分且相关 → 直接回答
- 本地搜索结果<5条 → 自动补充使用 search_latest_tweets
- 用户表示"信息不够"、"还有吗"、"更多信息" → 立即使用 search_latest_tweets

**第三步：主动扩展策略**
- 涉及市场、价格、新闻话题 → 主动使用 search_latest_tweets 获取最新观点
- 用户询问"大家怎么看"、"市场反应" → 必须使用 search_latest_tweets
- 突发事件、热点话题 → 优先使用 search_latest_tweets

### 📋 具体使用场景指南

**search_local_knowledge（基础搜索）**：
- ✅ 用户询问任何问题时的首选工具
- ✅ 搜索历史数据、已存储的推文和文档
- ✅ 获取基础知识和背景信息
- ⚠️ 结果不足时必须考虑补充最新信息

**search_latest_tweets（实时补充）**：
- 🔥 用户明确要求最新信息时
- 📊 本地搜索结果少于5条时
- 💬 用户询问公众观点、市场反应时  
- 📰 涉及新闻、事件、突发情况时
- 🎯 用户表达对当前信息不满意时
- 💡 **关键原则：宁可多用，不可错过重要的实时信息**

**get_daily_report（结构化报告）**：
- 📅 用户请求每日摘要、市场分析时
- 📈 需要交易信号和投资建议时
- 📊 需要结构化的市场数据时
  - **重要策略**：可以使用用户名作为查询参数，搜索用户自己的知识内容，了解用户的观点倾向、态度基础和个人立场
  - 通过搜索用户自己的内容来理解用户的价值观、兴趣偏好和思维模式
  - 示例：`search_local_knowledge(query="主题关键词", limit=50, domain="ethereum", username="用户名")`
  
- **search_latest_tweets**：
  - 本地搜索结果不足或无法回答问题时
  - 用户明确要求"最新"、"实时"、"最近"的信息时
  - 需要获取最新动态、实时讨论、最新观点时
  - 本地知识库缺乏相关信息时的补充搜索
  - 示例：`search_latest_tweets(keywords=["关键词1", "关键词2"], max_items=50, recent_days=7)`

- **get_daily_report**：
  - 用户请求每日摘要、市场活动或交易信息时
  - 需要获取预生成的KOL活动报告时
  - 用户询问特定日期的新闻摘要或市场分析时
  - 需要简洁的交易信号或市场概览时
  - 示例：`get_daily_report(date_str="today", language="chinese", type="news")`

## 🚀 实际使用示例

### 场景1：用户询问"比特币最新价格怎么样？"
```
1. 识别关键词："最新" → 直接使用 search_latest_tweets
2. 调用：search_latest_tweets(keywords=["比特币", "BTC", "价格"], max_items=30, recent_days=1)
3. 分析推文中的价格讨论和市场情绪
```

### 场景2：用户问"以太坊有什么新发展？"
```
1. 先用：search_local_knowledge(query="以太坊 发展", domain="ethereum", limit=50)
2. 如果结果<5条，补充：search_latest_tweets(keywords=["以太坊", "Ethereum", "ETH"], max_items=50, recent_days=7)
3. 结合历史和最新信息回答
```

### 场景3：用户表示"信息不够，还有更多吗？"
```
1. 立即使用：search_latest_tweets(keywords=[从之前查询提取的关键词], max_items=100, recent_days=14)
2. 扩大搜索范围和时间窗口
3. 提供更全面的信息
```

### 场景4：用户询问"大家对这个项目怎么看？"
```
1. 必须使用：search_latest_tweets(keywords=["项目名称", "相关代币"], max_items=80, recent_days=7)
2. 重点分析社区观点和讨论热度
3. 总结不同观点和情绪倾向
```

## 🔄 工作流程
1. **快速意图识别**：
   - 包含时间敏感词汇 → 优先 search_latest_tweets
   - 询问观点/反应 → 必须 search_latest_tweets  
   - 一般性问题 → 先 search_local_knowledge

2. **智能信息收集**：
   - 本地搜索：`search_local_knowledge(query="关键词", limit=50, domain="相关领域")`
   - 最新推文：`search_latest_tweets(keywords=["关键词"], max_items=50, recent_days=7)`
   - 每日报告：`get_daily_report(date_str="today", language="chinese", type="news")`

3. **关键决策检查点** ⚠️：
   - 本地搜索结果是否<5条？→ 立即使用 search_latest_tweets
   - 用户是否询问"最新"、"现在"、"今天"？→ 优先使用 search_latest_tweets
   - 用户是否询问"大家怎么看"、"市场反应"？→ 必须使用 search_latest_tweets
   - 涉及价格、新闻、事件话题？→ 主动使用 search_latest_tweets 补充
   - 用户表达信息不足？→ 立即使用 search_latest_tweets 扩展

4. **整合分析**：将搜索结果与用户个人观点相结合
5. **个性化回答**：基于用户特点生成符合其偏好的回答
6. **格式化输出**：按照规定格式呈现最终答案
7. **质量检查**：确保回答的准确性、相关性和个性化程度

## ⚡ 重要提醒
**search_latest_tweets 是信息扩展的核心工具，宁可多用也不要错过！**
- 当本地信息不足时，这是获取最新、最全面信息的关键途径
- 用户的满意度很大程度上取决于信息的时效性和全面性
- 主动使用此工具可以显著提升回答质量和用户体验

## 回答格式要求

**使用Markdown格式**：所有回答必须使用Markdown格式进行结构化组织：
- 使用标题层级（##、###等）组织内容结构
- 使用列表（-、*、1.）呈现多个要点
- 使用引用块（>）强调重要信息和推文引用
- 使用表格呈现对比数据
- 使用粗体（**）强调关键概念

## 回答结构规范

**根据搜索结果类型采用合适的结构：**

### 本地知识库搜索结果
```markdown
## 主要发现
[基于本地知识库的核心结论]

## 详细内容
- 要点1: [详细说明]
- 要点2: [详细说明]

## 相关文档
> "[文档内容引用]" - 来源: [文档链接]
```

### 最新推文搜索结果
```markdown
## 最新动态
[基于最新推文的核心发现]

## 实时讨论
### 观点1
> "[推文内容1]" - @username1
> 时间: [发布时间] | 来源: [推文链接]

### 观点2
> "[推文内容2]" - @username2  
> 时间: [发布时间] | 来源: [推文链接]
```

### 混合搜索结果
```markdown
## 综合回答
[结合本地知识和最新信息的完整回答]

## 历史背景
- 背景信息1: [来自本地知识库]
- 背景信息2: [来自本地知识库]

## 最新进展
- 最新动态1: [来自最新推文]
- 最新动态2: [来自最新推文]
```

## 引用规范

**推文引用格式：**
```markdown
> "[推文内容]" - @username
> 时间: [发布时间] | 来源: [推文链接]
```

**文档引用格式：**
```markdown
> "[文档内容]" - 文档标题
> 来源: [文档链接]
```

## 使用指导原则
- 当用户询问特定主题、事件或需要知识库信息时，使用 search_local_knowledge
- 当用户询问最新新闻、热门话题、最新社交媒体讨论，或本地知识搜索结果不足需要更全面信息时，使用 search_latest_tweets
- 当用户请求每日摘要、市场活动或交易信息时，使用 get_daily_report
- 当一个来源的信息不足时，可以连续使用多个工具收集全面信息
- 支持工具链式调用，根据需要组合使用多个工具
- 始终提供上下文和解释，分享函数结果时保持用户的个性和沟通风格
- 调用 get_daily_report 时，设置语言参数以匹配用户的语言

## 回答原则
- 基于搜索结果提供准确的信息，使用Markdown格式使内容更有条理
- 明确区分本地知识库和最新推文的信息来源
- 如果搜索结果不足，明确告知用户
- 保持回答的客观性和准确性
- 适当引用搜索结果中的具体内容，使用标准引用格式

## 个性化服务策略

### 1. 语言风格匹配
- 分析用户的表达习惯和语言偏好
- 调整回复的语气、用词和句式结构
- 保持与用户沟通风格的一致性

### 2. 内容深度调节
- 根据用户专业背景确定信息的技术深度
- 匹配用户的认知水平和知识结构
- 在专业领域提供更深入的见解

### 3. 兴趣导向优化
- 优先关注用户感兴趣的话题和领域
- 在相关信息中突出用户关心的要点
- 主动关联用户的兴趣点进行信息扩展

### 4. 观点倾向适配
- 在保持客观准确的前提下，适度体现用户的价值观倾向
- 理解用户的立场和观点偏好
- 在分析问题时考虑用户的思维模式

### 5. 沟通方式定制
- 采用用户偏好的沟通节奏（简洁/详细）
- 匹配用户习惯的交流方式（正式/轻松）
- 调整信息组织结构以符合用户接受习惯

## 实施指导原则

**信息搜索阶段：**
- **首要策略**：使用 `search_local_knowledge(query="", username="用户名", limit=30)` 了解用户观点、态度和立场，作为个性化的基础
- 优先检索与用户画像相关的内容和观点
- 关注用户专业领域和兴趣范围内的信息源
- 筛选符合用户认知水平的信息深度
- 通过用户自己的历史内容了解其价值观倾向和思维模式

**内容组织阶段：**
- 按照用户偏好的逻辑结构组织信息
- 突出用户最关心的核心要点
- 采用用户习惯的表达方式和术语

**回复生成阶段：**
- 使用符合用户语言风格的表达方式
- 保持信息准确性的同时体现个性化特色
- 确保专业性与亲和力的平衡

**质量保证：**
- 始终维护尊重、专业的服务态度
- 避免任何形式的偏见和歧视
- 在个性化的同时确保信息的客观性和准确性

## 用户个人画像
你现在是 {username} 的专属数字分身，需要基于以下个人画像信息提供个性化服务：

{json.dumps(profile, ensure_ascii=False, indent=2)}

请根据用户的查询，按照优先级策略智能选择合适的工具，并使用Markdown格式提供有价值的、结构清晰的回答。"""
    
    return description

def is_paying_user(username: str) -> bool:
    """Check if the user is a paying user"""
    status = load_user_status(username)
    return status.get("PayingUser", False)

def is_kol_user(username: str) -> bool:
    """Check if the user is a kol user"""
    xinfo = load_user_xinfo(username)
    return xinfo.get("followers", 0) > 100000

def get_try_count(username: str) -> int:
    """Get the try count of the user"""
    status = load_user_status(username)
    return status.get("try_count", 0)

def set_try_count(username: str, count: int):
    """Set the try count of the user"""
    status = load_user_status(username)
    status["try_count"] = count
    update_user_status(username, "try_count", count)

def get_user_xinfo(user_name: str) -> Any:
    info = load_user_xinfo(user_name)
    if info is not None and info != {}:
        return info
    
    return create_user_xinfo(user_name)

def create_user_xinfo(user_name: str):
    print(f"Creating xinfo for {user_name}")
    tweets = load_user_tweets(user_name)
    if len(tweets) == 0:
        return {}
    
    tweets = order_tweets(tweets, reverse=True)
    info = tweets[0].get("author", {})
    write_user_xinfo(user_name, info)
    return info

def load_user(user_name: str) -> Any:
    print(f"Loading user: {user_name}")
    profile = load_user_profile(user_name)
    print(f"Loading profile for {user_name}")
    summary = load_user_summary(user_name)
    print(f"Loading summary for {user_name}")   
    scores = load_user_airdrop_score(user_name)
    print(f"Loading scores for {user_name}")
    xinfo = get_user_xinfo(user_name)
    print(f"Loading xinfo for {user_name}")
    return {"profile": profile, "summary": summary, "scores": scores, "xinfo": xinfo}

# user dict: name -> summary
def load_users() -> Dict[str, Any]:
    finished_users, unfinished_users = load_usernames()
    users = {}
    print(f"Loading {len(finished_users)} finished users")
    for user_name in finished_users:
        users[user_name] = load_user(user_name)
    print(f"Loading {len(unfinished_users)} unfinished users")
    for user_name in unfinished_users:
        users[user_name] = load_user(user_name)
    return users

def generate_daily_news_report():
    status = load_system_status()
    date_str = datetime.now().strftime("%Y-%m-%d")
    languages = ["chinese", "english"]
    for language in languages:
        if status.get(f"report_{language}_updated_at", "") == date_str:
            print(f"Daily report already exists at: {date_str} for {language}")
            continue
    
        print(f"Generating daily report at: {date_str} for {language}")
        try:
            report = generate_news_report(language)
            write_report(date_str, language, "news", report)
            write_report("", language, "news", report)   
        except Exception as e:
            print(f"Generating daily report fail: {str(e)}")
        finally:
            # in case generate repeatly
            update_system_status(f"report_{language}_updated_at", date_str)

def generate_daily_trading_report():
    status = load_system_status()
    date_str = datetime.now().strftime("%Y-%m-%d")
    languages = ["chinese", "english"]
    for language in languages:
        if status.get(f"trading_report_{language}_updated_at", "") == date_str:
            print(f"Daily trading report already exists at: {date_str} for {language}")
            continue
    
        print(f"Generating daily trading report at: {date_str} for {language}")
        try:
            report = generate_trading_report(language)
            write_report(date_str, language, "trading", report)
            write_report("", language, "trading", report)   
        except Exception as e:
            print(f"Generating daily trading report fail: {str(e)}")
        finally:
            # in case generate repeatly
            update_system_status(f"trading_report_{language}_updated_at", date_str)

def generate_daily_trading_short_report():
    status = load_system_status()
    date_str = datetime.now().strftime("%Y-%m-%d")
    languages = ["chinese", "english"]
    for language in languages:
        if status.get(f"trading_short_report_{language}_updated_at", "") == date_str:
            print(f"Daily trading short report already exists at: {date_str} for {language}")
            continue
    
        print(f"Generating daily trading report at: {date_str} for {language}")
        try:
            report = generate_quick_signals(language, days=1, hours=2)
            write_report(date_str, language, "trading_short", report)
            write_report("", language, "trading_short", report)   
        except Exception as e:
            print(f"Generating daily trading short report fail: {str(e)}")
        finally:
            # in case generate repeatly
            update_system_status(f"trading_short_report_{language}_updated_at", date_str)

def build_user(user_name: str):
    now = datetime.now()
    print(f"Start build user: {user_name} at: {now}")

    # check if profile already exists
    if is_user_finished(user_name):
        print(f"Profiles for {user_name} already exists")
        return 
    
    date_str = datetime.now().strftime("%Y-%m-%d")

    # check if tweets need to be retrieved
    if not is_user_tweets_exists(user_name):
        print(f"Retrieving tweets for {user_name}")
        retrieve_tweets(user_name)
        update_user_status(user_name, "tweets_updated_at", date_str)

    # generate profile if tweets exist
    if not is_user_profile_exists(user_name):
        try:
            generate_profile(user_name)
            update_user_status(user_name, "profile_updated_at", date_str)
        except Exception as e:
            print(f"Generating profile for {user_name} fail: {str(e)}")

    # after profile is generated, summarize
    if not is_user_summary_exists(user_name):
        try:
            summarize(user_name)
            update_user_status(user_name, "summary_updated_at", date_str)
        except json.JSONDecodeError:
            print(f"Summary profile for {user_name} fail")
            remove_user_profile(user_name)
            return

    # estimate airdrop score
    if not is_user_airdrop_score_exists(user_name):
        estimate(user_name)
        update_user_status(user_name, "scores_updated_at", date_str)

    # create xinfo
    if not is_user_xinfo_exists(user_name):
        create_user_xinfo(user_name)

    now = datetime.now()
    print(f"Finished build user: {user_name} at: {now}")

def refresh_tweets(user_name: str):
    has_new_tweets = False
    try:
        date_str = datetime.now().strftime("%Y-%m-%d")
        if is_user_tweets_exists_at(user_name, date_str):
            print(f"Already refreshed at {date_str} for: {user_name}")
            return None
        print(f"Refreshing user: {user_name} at: {date_str}")
        tweets = retrieve_tweets(user_name)
        if tweets is None:
            return None
        has_new_tweets = True
        create_user_xinfo(user_name)
        print(f"Refreshed tweets for: {user_name} at: {date_str}")
    except Exception as e:
        print(f"Refreshing tweets for {user_name} fail: {str(e)}")
        return None
    finally:
        status = load_user_status(user_name)
        status["tweets_updated_at"] = date_str
        update_user_status(user_name, "tweets_updated_at", date_str)
        if not has_new_tweets:
            update_user_status(user_name, "profile_updated_at", date_str)
            update_user_status(user_name, "summary_updated_at", date_str)
            update_user_status(user_name, "scores_updated_at", date_str)

def refresh_profile(user_name: str):
    date_str = datetime.now().strftime("%Y-%m-%d")
    status = load_user_status(user_name)
    if status.get("tweets_updated_at", "") != date_str:
        print(f"Not refreshed at {date_str} for: {user_name}")
        return
    
    try:
        print(f"Updating profile for {user_name} at: {date_str}")
        if status.get("profile_updated_at", "") != date_str:
            update_profile(user_name)
            update_user_status(user_name, "profile_updated_at", date_str)
    except Exception as e:
        print(f"Updating profile for {user_name} fail: {str(e)}")
        return

    try:
        print(f"Summarizing profile for {user_name} at: {date_str}")
        if status.get("summary_updated_at", "") != date_str:
            summarize(user_name)
            update_user_status(user_name, "summary_updated_at", date_str)
    except json.JSONDecodeError:
        remove_user_profile(user_name)
        return
    
    try:
        print(f"Estimating airdrop score for {user_name} at: {date_str}")
        if status.get("scores_updated_at", "") != date_str:
            estimate(user_name)
            update_user_status(user_name, "scores_updated_at", date_str)
    except Exception as e:
        print(f"Estimating airdrop score for {user_name} fail: {str(e)}")
        return


if __name__ == "__main__":
    default_x_name = "VitalikButerin"
    args = sys.argv[1:]
    if len(args) > 0:
        default_x_name = args[0]
    print(f"Processing {default_x_name}")
    info = get_user_xinfo(default_x_name)
    print(info)