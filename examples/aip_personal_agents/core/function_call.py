"""
推文搜索API的Function Call函数模块

本模块提供了用于LLM调用推文搜索相关API接口的函数集合，支持两种主要的推文搜索方式：
1. 本地知识库搜索 - 从已存储的推文数据库中进行语义搜索和结构化查询
2. 实时推文搜索 - 通过Apify服务从Twitter获取最新的实时推文数据

主要功能：
- 语义相似度搜索：基于Milvus向量数据库的语义匹配
- 结构化过滤：支持按域名、用户名、时间等条件过滤
- 实时数据获取：通过外部API服务获取Twitter最新推文
- 错误处理和参数验证：完整的输入验证和异常处理机制
- JSON格式化输出：统一的返回格式便于LLM处理

依赖服务：
- Milvus向量数据库：用于语义搜索
- PostgreSQL数据库：用于结构化数据存储
- Apify服务：用于实时Twitter数据抓取
- UniMind API：本地API服务接口

环境变量要求：
- UNIMIND_API_KEY：API认证密钥
- UNIMIND_BASE_URL：API服务基础URL（默认：http://127.0.0.1:8000）

使用场景：
- 市场情绪分析和趋势监控
- 特定话题的历史数据分析
- 实时社交媒体数据收集
- 用户行为和内容分析
- 新闻事件和舆情监测
"""

from typing import Dict, List, Optional, Any, Union
import json
from dotenv import load_dotenv
import requests
import os
from datetime import datetime, timedelta

from core.common import load_user_profile,load_report
try:
    from fastapi import HTTPException
except ImportError:
    # 如果没有安装 fastapi，定义一个简单的替代
    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str):
            self.status_code = status_code
            self.detail = detail
            super().__init__(detail)

try:
    from openai import AsyncOpenAI
except ImportError:
    # 如果没有安装 openai，定义一个模拟类
    class AsyncOpenAI:
        def __init__(self, api_key=None):
            self.api_key = api_key
        
        class chat:
            class completions:
                @staticmethod
                async def create(**kwargs):
                    return type('MockResponse', (), {
                        'choices': [type('Choice', (), {
                            'message': type('Message', (), {
                                'content': '这是一个模拟回复，因为没有安装 openai 库。'
                            })()
                        })()]
                    })()

import logging

load_dotenv()

# 设置日志
logger = logging.getLogger(__name__)

# 全局变量声明 - 这些需要在使用前初始化
llm_chat_service = None

# 模拟的类定义，用于包含agentic_chat方法
class LLMChatService:
    def __init__(self, model="gpt-4.1"):
        self.model = model
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OpenAI API key is required")
        
        # 使用异步客户端
        self.client = AsyncOpenAI(api_key=openai_api_key)
    
    async def agentic_chat(self, user_query: str, conversation_history: Optional[List[Dict[str, str]]] = None,
                          function_schemas: Optional[List[Dict[str, Any]]] = None,
                          function_executor: Optional[callable] = None,
                          max_function_calls: int = 5,
                          personality: Optional[str] = None) -> Dict[str, Any]:
        """
        处理 agentic 聊天请求，支持多次 function calling
        
        Args:
            user_query: 用户查询
            conversation_history: 对话历史
            function_schemas: 可用的函数 schema 列表
            function_executor: 函数执行器
            max_function_calls: 最大函数调用次数，防止无限循环（默认5次）
            personality: 用户个人画像信息，用于个性化回复
            
        Returns:
            包含 AI 回复和执行结果的字典，包括：
            - user_query: 用户查询
            - llm_response: AI 最终回复
            - function_calls: 函数调用历史列表
            - total_function_calls: 总函数调用次数
            - timestamp: 时间戳
        """
        try:
            # 构建系统提示
            system_prompt = self._get_agentic_chat_system_prompt(personality)
            
            # 构建用户提示
            user_prompt = self._build_agentic_chat_prompt(user_query)
            
            # 准备消息
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # 添加对话历史
            if conversation_history:
                formatted_history = self._format_conversation_history(conversation_history, max_rounds=5)
                if formatted_history:
                    messages.insert(-1, {"role": "system", "content": f"对话历史：\n{formatted_history}"})
            
            # 使用支持 function calling 的模型
            function_model = "gpt-4.1" if function_schemas else self.model
            function_results = []
            function_call_count = 0
            
            # 参数验证
            if max_function_calls < 1:
                max_function_calls = 1
            elif max_function_calls > 10:
                logger.warning("Max function calls limited to 10 for safety", 
                             requested=max_function_calls, 
                             limited_to=10)
                max_function_calls = 10
            
            # 循环处理函数调用，直到LLM不再请求函数调用或达到最大次数
            while function_call_count < max_function_calls:
                # 调用 LLM
                response = await self.client.chat.completions.create(
                    model=function_model,
                    messages=messages,
                    functions=function_schemas if function_schemas else None,
                    function_call="auto" if function_schemas else None,
                    timeout=121.0
                )
                
                message = response.choices[0].message
                
                # 检查是否有函数调用
                if message.function_call and function_executor:
                    function_name = message.function_call.name
                    function_args = json.loads(message.function_call.arguments)
                    function_call_count += 1
                    
                    logger.info("Executing function call", 
                              function=function_name, 
                              args=function_args, 
                              call_count=function_call_count)
                    
                    # 执行函数调用，添加错误处理
                    try:
                        function_result = await function_executor(function_name, function_args)
                        function_results.append({
                            "function_name": function_name,
                            "arguments": function_args,
                            "result": function_result,
                            "call_order": function_call_count,
                            "success": True
                        })
                    except Exception as func_error:
                        logger.error("Function execution failed", 
                                   function=function_name, 
                                   args=function_args, 
                                   error=str(func_error))
                        function_result = {
                            "error": f"函数执行失败: {str(func_error)}",
                            "function_name": function_name
                        }
                        function_results.append({
                            "function_name": function_name,
                            "arguments": function_args,
                            "result": function_result,
                            "call_order": function_call_count,
                            "success": False
                        })
                    
                    # 将函数调用结果添加到对话中
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "function_call": {
                            "name": function_name,
                            "arguments": message.function_call.arguments
                        }
                    })
                    
                    messages.append({
                        "role": "function",
                        "name": function_name,
                        "content": json.dumps(function_result, ensure_ascii=False)
                    })
                    
                    # 继续循环，让LLM基于函数结果决定下一步
                    continue
                else:
                    # 没有函数调用，生成最终回复并退出循环
                    final_message = message.content.strip() if message.content else "抱歉，我无法处理您的请求。"
                    break
            else:
                # 达到最大函数调用次数，强制生成最终回复
                logger.warning("Reached maximum function calls limit", 
                             max_calls=max_function_calls, 
                             user_query=user_query)
                
                # 最后一次调用LLM生成回复，不允许函数调用
                final_response = await self.client.chat.completions.create(
                    model=function_model,
                    messages=messages + [{"role": "system", "content": "请基于以上信息生成最终回复，不要再调用任何函数。"}],
                    timeout=121.0
                )
                final_message = final_response.choices[0].message.content.strip()
            
            return {
                "user_query": user_query,
                "llm_response": final_message,
                "function_calls": function_results,
                "total_function_calls": len(function_results),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("Agentic chat processing failed", error=str(e), user_query=user_query)
            return {
                "user_query": user_query,
                "llm_response": f"抱歉，处理您的请求时出现了错误：{str(e)}",
                "function_calls": [],
                "timestamp": datetime.now().isoformat()
            }

    def _get_agentic_chat_system_prompt(self, personality: str = None) -> str:
        """获取 agentic chat 的系统提示"""
        
        # 基础系统提示
        base_prompt = """你是一个智能助手，专门帮助用户搜索和分析推文、文档等内容。你有以下能力：

## 重要语言指导原则
- 检测用户消息的语言
- 如果用户使用中文，请用中文回复
- 如果用户使用英文，请用英文回复
- 始终匹配用户的语言选择以保持一致性
- 调用函数时，根据用户的语言设置相应的语言参数

## 可用工具
1. **search_local_knowledge(query: str) -> str**
   - 目的：从本地知识库和内容中搜索相关信息
   - 使用场景：当用户询问特定主题时，从存储的知识中查找相关信息
   - 返回：匹配查询的相关信息和内容

2. **search_latest_tweets(query: str) -> str**
   - 目的：搜索与给定查询相关的最新推文和社交媒体内容
   - 使用场景：当用户询问最新新闻、热门话题、最新社交媒体讨论，或当本地知识不足需要更多信息时
   - 返回：匹配查询的最新推文和社交媒体内容

3. **get_daily_report(date_str: str = "today", language: str = "chinese", type: str = "news") -> str**
   - 目的：检索预生成的每日报告，总结KOL活动
   - 参数：
     * date_str: "today"、"yesterday" 或 "YYYY-MM-DD" 格式
     * language: "chinese" 或 "english"（根据用户语言设置）
     * type: "news"（每日摘要）、"trading"（交易或市场分析）或 "trading_short"（简洁信号）
   - 使用场景：当用户请求每日摘要、市场分析或交易信息时
   - 返回：指定语言和格式的完整报告内容

## 工具使用策略
**优先级原则**：
1. **首先使用 search_local_knowledge**：当用户提出任何问题时，优先在本地知识库中搜索相关信息
2. **信息不足时使用 search_latest_tweets**：当本地搜索结果无法充分回答用户问题，或用户明确要求最新信息时，再使用此工具扩展搜索
3. **使用 get_daily_report**：当用户请求每日摘要、市场活动或交易信息时

**具体使用场景**：
- **search_local_knowledge**：
  - 用户询问任何问题时的首选工具
  - 搜索已有的文档、推文、知识内容
  - 获取历史信息和已存储的数据
  
- **search_latest_tweets**：
  - 本地搜索结果不足或无法回答问题时
  - 用户明确要求"最新"、"实时"、"最近"的信息时
  - 需要获取最新动态、实时讨论、最新观点时
  - 本地知识库缺乏相关信息时的补充搜索

- **get_daily_report**：
  - 用户请求每日摘要、市场活动或交易信息时
  - 需要获取预生成的KOL活动报告时
  - 用户询问特定日期的新闻摘要或市场分析时
  - 需要简洁的交易信号或市场概览时

## 使用指导原则
- 当用户询问特定主题、事件或需要知识库信息时，使用 search_local_knowledge
- 当用户询问最新新闻、热门话题、最新社交媒体讨论，或本地知识搜索结果不足需要更全面信息时，使用 search_latest_tweets
- 当用户请求每日摘要、市场活动或交易信息时，使用 get_daily_report
- 当一个来源的信息不足时，尝试使用 search_latest_tweets 收集额外的实时信息
- 始终提供上下文和解释，分享函数结果时保持用户的个性和沟通风格
- 调用 get_daily_report 时，设置语言参数以匹配用户的语言

## 工作流程
1. 分析用户查询意图和语言
2. 根据查询类型选择合适的工具：
   - 一般问题：首先使用 search_local_knowledge
   - 每日报告请求：使用 get_daily_report
   - 最新信息请求：使用 search_latest_tweets
3. 评估搜索结果是否足够回答用户问题
4. 如果信息不足，使用 search_latest_tweets 获取最新信息
5. 综合所有搜索结果为用户提供完整的回答

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

## 回答原则
- 基于搜索结果提供准确的信息，使用Markdown格式使内容更有条理
- 明确区分本地知识库和最新推文的信息来源
- 如果搜索结果不足，明确告知用户
- 保持回答的客观性和准确性
- 适当引用搜索结果中的具体内容，使用标准引用格式"""

        # 如果有个人画像，添加个性化指令, 
        if personality and personality.strip() != "":
            # personality is username
            username = personality
            profile = load_user_profile(username)
            if profile:
                personality = json.dumps(profile, ensure_ascii=False, indent=2)
            personality_prompt = f"""

## 数字分身角色定位
你现在是 {username} 的专属数字分身，需要基于以下个人画像信息提供个性化服务。

## 用户个人画像
{personality}

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
- 优先检索与用户画像相关的内容和观点
- 关注用户专业领域和兴趣范围内的信息源
- 筛选符合用户认知水平的信息深度

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
- 在个性化的同时确保信息的客观性和准确性"""
            
            return base_prompt + personality_prompt

        # 没有个人画像时，添加通用的专业回复指令
        return base_prompt + """

请根据用户的查询，按照优先级策略智能选择合适的工具，并使用Markdown格式提供有价值的、结构清晰的回答。"""

    def _format_conversation_history(self, conversation_history: List[Dict[str, str]], max_rounds: int = 5) -> str:
        """格式化对话历史"""
        if not conversation_history:
            return ""
        
        # 只保留最近的几轮对话
        recent_history = conversation_history[-max_rounds:] if len(conversation_history) > max_rounds else conversation_history
        
        formatted = []
        for item in recent_history:
            role = item.get('role', 'user')
            content = item.get('content', '')
            if role and content:
                formatted.append(f"{role}: {content}")
        
        return "\n".join(formatted)

    def _build_agentic_chat_prompt(self, user_query: str) -> str:
        """构建 agentic chat 的用户提示"""
        prompt = f"用户查询：{user_query}\n"
        
        prompt += "\n请分析用户的查询意图，选择合适的搜索工具来获取相关信息，然后基于搜索结果为用户提供准确的回答。"
        
        return prompt


# Function call schemas for agentic chat
FUNCTION_SCHEMAS = [
    {
        "name": "search_local_knowledge",
        "description": "搜索本地知识库中的相关文档和推文。当用户询问问题时，优先使用此函数在已有的知识库中查找相关信息。如果本地搜索结果不足或无法回答用户问题，再考虑使用其他搜索方式。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询词，用于语义搜索，不能为空字符串",
                    "default": ""
                },
                "domain": {
                    "type": "string",
                    "description": "领域过滤，可选值：ethereum, binance, bitcoin, solana, ai, other"
                },
                "username": {
                    "type": "string",
                    "description": "用户名过滤，搜索特定用户的推文（不包含@符号）"
                },
                "limit": {
                    "type": "integer",
                    "description": "返回结果数量限制，默认50",
                    "default": 50
                }
            },
            "required": []
        }
    },
    {
        "name": "search_latest_tweets",
        "description": "搜索最新的实时 Twitter 推文数据。当本地知识库搜索结果不足，或用户明确要求最新信息、实时数据、最新推文时使用。特别适用于需要获取最新动态、实时讨论、最新观点的场景。",
        "parameters": {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "搜索关键词列表，用于在 Twitter 上搜索相关推文"
                },
                "max_items": {
                    "type": "integer",
                    "description": "最大返回推文数量，默认50，有效范围1-200",
                    "default": 50
                },
                "recent_days": {
                    "type": "integer",
                    "description": "搜索最近几天的推文，默认7天，有效范围1-180天",
                    "default": 7
                }
            },
            "required": ["keywords"]
        }
    },
    {
        "name": "get_daily_report",
        "description": "获取指定日期的每日报告。支持获取新闻摘要、交易分析等不同类型的报告。当用户询问每日报告、新闻摘要、市场分析等信息时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "date_str": {
                    "type": "string",
                    "description": "报告日期，支持格式：'today'/'latest'(今天)、'yesterday'(昨天)、'YYYY-MM-DD'(具体日期)",
                    "default": "today"
                },
                "language": {
                    "type": "string",
                    "description": "报告语言：'chinese'(中文)、'english'(英文)",
                    "default": "chinese"
                },
                "type": {
                    "type": "string",
                    "description": "报告类型：'news'(新闻摘要)、'trading'(交易分析)、'trading_short'(简短交易信号)",
                    "default": "news"
                }
            },
            "required": []
        }
    }
]

async def execute_function_call(function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    执行 function call
    
    Args:
        function_name: 函数名称
        arguments: 函数参数
        unified_service: 统一存储服务
        
    Returns:
        函数执行结果
    """
    try:
        if function_name == "search_local_knowledge":
            
            query = arguments.get("query", "")
            domain = arguments.get("domain")
            username = arguments.get("username")
            limit = arguments.get("limit", 50)
            
            print(f"search local knowledge for domain={domain}, username={username}") 
            
            result = search_local_knowledge(
                query=query,
                domain=domain,
                username=username,
                limit=limit
            )
            
            # Parse the JSON result to get the actual data
            import json
            try:
                parsed_result = json.loads(result)
                results = parsed_result.get("tweets", [])
            except:
                results = []
            
            return {
                "success": True,
                "function": function_name,
                "results": results,
                "count": len(results) if results else 0
            }
            
        elif function_name == "search_latest_tweets":
            print(f"search latest tweets")
            keywords = arguments.get("keywords", [])

            if len(keywords) == 0:
                return {
                    "success": False,
                    "function": function_name,
                    "results": None,
                    "count": 0
                }
            max_items = arguments.get("max_items", 50)
            recent_days = arguments.get("recent_days", 7)
            
            result = search_latest_tweets(keywords, max_items, recent_days)
            
            # Parse the JSON result to get the actual data
            import json
            try:
                parsed_result = json.loads(result)
                results = parsed_result.get("tweets", [])
            except:
                results = []
            
            return {
                "success": True,
                "function": function_name,
                "results": results,
                "count": len(results) if results else 0
            }
            
        elif function_name == "get_daily_report":
            print(f"get daily report")
            date_str = arguments.get("date_str", "today")
            language = arguments.get("language", "chinese")
            report_type = arguments.get("type", "news")
            
            result = get_daily_report(date_str, language, report_type)
            
            return {
                "success": True,
                "function": function_name,
                "results": result,
                "count": 1 if result else 0
            }
            
        else:
            return {
                "success": False,
                "error": f"Unknown function: {function_name}"
            }
            
    except Exception as e:
        logger.error("Function call execution failed", function=function_name, error=str(e))
        return {
            "success": False,
            "function": function_name,
            "error": str(e)
        }

async def process_agentic_chat_message(message: str, conversation_history: Optional[List[Dict[str, str]]] = None,
                                     personality: Optional[str] = None) -> str:
    """
    处理 agentic 聊天消息，支持 function calling
    
    Args:
        message: 用户消息
        conversation_history: 对话历史
        personality: 用户个人画像信息，用于个性化回复
        
    Returns:
        AI回复文本
    """

    print(f"handle chat using agentic agent")
    try:
        if not llm_chat_service:
            raise HTTPException(status_code=500, detail="LLM聊天服务未初始化")
        
        if not message or message.strip() == "":
            raise HTTPException(status_code=400, detail="消息不能为空")
        
        # 使用 function calling 进行 agentic chat
        result = await llm_chat_service.agentic_chat(
            user_query=message,
            conversation_history=conversation_history,
            function_schemas=FUNCTION_SCHEMAS,
            function_executor=lambda func_name, args: execute_function_call(func_name, args),
            personality=personality
        )
        
        return result["llm_response"]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Agentic 聊天消息处理失败", error=str(e), message=message)
        return f"抱歉，处理您的消息时出现了错误：{str(e)}"

def get_daily_report(date_str: str = "today", language: str = "chinese", type: str = "news") -> str:
    """Get daily report content for a specific date, language, and report type.
    
    This function retrieves pre-generated daily reports that summarize KOL (Key Opinion Leader) 
    posts and activities. The reports are categorized by type and available in multiple languages.
    
    Args:
        date_str (str): Date for the report. Accepts:
            - "today" or "latest": Current date (default)
            - "yesterday": Previous day
            - "YYYY-MM-DD": Specific date format (e.g., "2025-01-15")
        language (str): Report language. Options:
            - "chinese": Chinese language report (default)
            - "english": English language report
        type (str): Report category. Options:
            - "news": Daily web3 and crypto news summary of latest KOL posts and activities (default)
            - "trading": Comprehensive daily web3 and crypto trading and market analysis from KOL posts
            - "trading_short": Concise web3 and crypto trading signals from KOL posts
    
    Returns:
        str: The complete report content in the specified language and format
        
    Examples:
        - get_daily_report() -> Latest Chinese news report
        - get_daily_report("2025-01-15", "english", "trading") -> English trading report for Jan 15, 2025
        - get_daily_report("yesterday", "chinese", "trading_short") -> Chinese trading signals for yesterday
    """
    
    print(f"Getting daily report for {date_str}, {language}, {type}")
    
    # check if date_str is valid date
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        if date_str is None or date_str == "" or date_str.lower() == "today" or date_str.lower() == "latest":
            date_str = datetime.now().strftime("%Y-%m-%d")
        elif date_str.lower() == "yesterday":
            date_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            return f"Invalid date format: {date_str}"
    
    report = load_report(date_str, language, type)
    return report        

def search_local_knowledge(
    query: str = "",
    limit: int = 50,
    domain: Optional[str] = None,
    username: Optional[str] = None,
) -> str:
    """Search tweets from local knowledge base with semantic search and filtering capabilities.
    
    This function searches through the local tweet database using Milvus vector search and SQL filtering.
    It supports various filtering options for comprehensive tweet retrieval and analysis, providing
    both semantic similarity matching and structured data filtering.
    
    Args:
        query (str, optional): Search query string for semantic similarity search. Can be keywords,
            phrases, or natural language questions. Empty string means no semantic filtering.
            Default is "".
        limit (int, optional): Maximum number of tweets to return. Controls the size
            of the result set for pagination and performance optimization. Must be positive integer.
            Default is 50.
        domain (Optional[str], optional): Domain filter for tweet categorization. Filters tweets
            by predefined content categories. Available options:
            - "ethereum": Ethereum blockchain and smart contract related content
            - "binance": Binance exchange, trading, and ecosystem related content  
            - "bitcoin": Bitcoin cryptocurrency and network related content
            - "solana": Solana blockchain and ecosystem related content
            - "ai": Artificial intelligence, machine learning, and tech related content
            - "other": Miscellaneous relevant content not fitting other categories
            - None: No domain filtering applied (default)
        username (Optional[str], optional): Filter by specific Twitter username (without @ symbol).
            Searches for tweets from a particular user account. Case-insensitive matching.
            Default is None (no user filtering).
  
    Returns:
        str: JSON formatted string containing comprehensive search results including:
            - tweets: List of matching tweet objects with full metadata
            - total_count: Total number of matching tweets in database
            - page_info: Pagination information (current page, page size)
            - search_metadata: Search parameters and execution statistics
            - error: Error message if request fails
        
    Examples:
        - search_local_knowledge("artificial intelligence", limit=20, domain="ai") -> AI tech tweets
        - search_local_knowledge("DeFi protocols", username="elonmusk") -> Elon's DeFi tweets
        - search_local_knowledge("", domain="bitcoin", limit=100) -> All Bitcoin domain tweets
        - search_local_knowledge("market analysis") -> General market analysis tweets
    """
    
    print(f"Searching tweets with query: {query}, username {username}")
    
    # 构建API请求数据
    request_data = {
        "page": 1,
        "page_size": limit
    }
    
    if query:
        request_data["query"] = query
    if domain:
        request_data["domain"] = domain
    if username:
        request_data["username"] = username
    
    # 获取API密钥
    api_key = os.getenv("UNIMIND_API_KEY")
    if not api_key:
        return json.dumps({"error": "UNIMIND_API_KEY not found in environment variables"}, ensure_ascii=False)
    
    try:
        # 调用本地API接口
        base_url = os.getenv("UNIMIND_BASE_URL", "http://127.0.0.1:8000")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        response = requests.post(f"{base_url}/api/tweets/search", json=request_data, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except requests.exceptions.RequestException as e:
        error_msg = f"API request failed: {str(e)}"
        print(error_msg)
        return json.dumps({"error": error_msg}, ensure_ascii=False)
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(error_msg)
        return json.dumps({"error": error_msg}, ensure_ascii=False)


def search_latest_tweets(
    keywords: List[str],
    max_items: int = 50,
    recent_days: int = 7
) -> str:
    """Search latest tweets from Twitter using Apify service for real-time data collection.
    
    This function fetches the most recent tweets directly from Twitter using the external Apify
    web scraping service, providing real-time social media data and current discussions. It's
    ideal for monitoring trending topics, breaking news, market sentiment, and current public
    opinions on specific subjects. The function bypasses local database and fetches fresh data.
    
    Args:
        keywords (List[str]): List of search keywords and phrases to find relevant tweets on Twitter.
            Multiple keywords are combined using OR logic for broader search coverage. Each keyword
            can be a single word, phrase, or hashtag. Cannot be empty list.
            Examples: ["AI", "artificial intelligence"], ["#bitcoin", "cryptocurrency"]
        max_items (int, optional): Maximum number of tweets to return from the search. Valid range
            is 1-200 tweets. Higher values provide more comprehensive results but may take longer
            to process and consume more API resources. Default is 50.
        recent_days (int, optional): Number of recent days to search within, counting backwards
            from current date. Valid range is 1-180 days. Smaller values provide more recent
            but potentially fewer results, while larger values cover more historical data.
            Default is 7 days.
    
    Returns:
        str: JSON formatted string containing comprehensive latest tweet results including:
            - tweets: Array of tweet objects with full content, metadata, and user information
            - user_data: Twitter user profiles and verification status
            - engagement_metrics: Like counts, retweet counts, reply counts, and view counts
            - timestamp_data: Tweet creation time, processing time, and data freshness indicators
            - search_metadata: Search parameters, execution time, and result statistics
            - api_status: Apify service status and rate limiting information
            - error: Detailed error message if the request fails or validation errors occur
        
    Raises:
        ValueError: If keywords list is empty or parameters are outside valid ranges
        RequestException: If Apify API service is unavailable or returns errors
        
    Examples:
        - search_latest_tweets(["AI", "artificial intelligence"]) -> Latest AI discussion tweets
        - search_latest_tweets(["crypto", "bitcoin"], max_items=30, recent_days=3) -> Recent crypto tweets
        - search_latest_tweets(["climate change", "environment"], max_items=100, recent_days=14) -> Environmental tweets
        - search_latest_tweets(["#Tesla", "$TSLA"], max_items=20, recent_days=1) -> Tesla stock tweets today
    """
    
    print(f"Searching latest tweets with keywords: {keywords}, max_items: {max_items}, recent_days: {recent_days}")
    
    # 验证参数
    if not keywords or len(keywords) == 0:
        return json.dumps({"error": "Keywords list cannot be empty"}, ensure_ascii=False)
    
    if max_items < 1 or max_items > 200:
        return json.dumps({"error": "max_items must be between 1 and 200"}, ensure_ascii=False)
    
    if recent_days < 1 or recent_days > 180:
        return json.dumps({"error": "recent_days must be between 1 and 180"}, ensure_ascii=False)
    
    # 构建API请求数据
    request_data = {
        "keywords": keywords,
        "max_items": max_items,
        "recent_days": recent_days
    }
    
    # 获取API密钥
    api_key = os.getenv("UNIMIND_API_KEY")
    if not api_key:
        return json.dumps({"error": "UNIMIND_API_KEY not found in environment variables"}, ensure_ascii=False)
    
    try:
        # 调用本地API接口
        base_url = os.getenv("UNIMIND_BASE_URL", "http://127.0.0.1:8000")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        response = requests.post(
            f"{base_url}/api/tweets/search-latest", 
            json=request_data,
            headers=headers
        )
        response.raise_for_status()
        
        result = response.json()
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except requests.exceptions.RequestException as e:
        error_msg = f"API request failed: {str(e)}"
        print(error_msg)
        return json.dumps({"error": error_msg}, ensure_ascii=False)
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(error_msg)
        return json.dumps({"error": error_msg}, ensure_ascii=False)


# 初始化全局服务实例
def initialize_services():
    """初始化全局服务实例"""
    global llm_chat_service
    
    if llm_chat_service is None:
        llm_chat_service = LLMChatService()

# 在模块加载时初始化服务
initialize_services()

if __name__ == "__main__":
    import asyncio
    
    async def test_functions():
        print("=== 搜索本地推文示例 ===")
        #local_result = search_local_knowledge(
        #    query="人工智能",
        #    domain="ai",
        #)
        #print(local_result)
        
        print("\n=== 搜索最新推文示例 ===")
        #latest_result = search_latest_tweets(
        #    keywords=["人工智能", "AI", "机器学习"],
        #    max_items=10,
        #    recent_days=3
        #)
        #print(latest_result)

        
        print("\n=== 测试 process_agentic_chat_message ===")
        # 初始化服务
        initialize_services()
        
        # 测试简单查询
        response = await process_agentic_chat_message(
            message="请帮我搜索一下关于人工智能的最新信息",
            conversation_history=[],
            personality="cz_binance"
        )
        print("AI回复:", response)
        
        print("\n=== 测试带对话历史的查询 ===")
        conversation_history = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！我是AI助手，有什么可以帮助你的吗？"}
        ]
        response2 = await process_agentic_chat_message(
            message="请获取今天的新闻报告",
            conversation_history=conversation_history,
            personality="cz_binance"
        )
        print("AI回复:", response2)
    
    # 运行异步测试
    asyncio.run(test_functions())