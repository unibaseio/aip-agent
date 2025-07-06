import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException, Depends, Header, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import os
import json
from concurrent.futures import ThreadPoolExecutor
import time
import argparse
import signal
import sys
from typing import Optional, List, Dict, Any
from threading import Lock
from contextlib import asynccontextmanager
import threading

from membase.chain.chain import membase_id
from aip_agent.agents.custom_agent import CallbackAgent
from aip_agent.agents.full_agent import FullAgentWrapper
from core.build import (
    generate_daily_news_report,
    generate_daily_trading_report,
    generate_daily_trading_short_report,
    get_description,
    get_try_count,
    load_user, 
    load_users, 
    build_user, 
    refresh_tweets, 
    refresh_profile,
    is_kol_user, is_paying_user,
    set_try_count
)
from core.common import (
    init_user, 
    is_user_exists, 
    load_usernames, 
    load_user_status, 
    update_user_status,
    load_report
)
from core.rag import search_similar_posts, switch_user
from core.save import save_tweets
from core.utils import convert_to_json

# Add global shutdown flag
is_shutting_down = False

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

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: setup code goes here
    print("Application startup...")
    yield
    # Shutdown: cleanup code goes here
    print("Application shutdown...")
    await graceful_shutdown()

app = FastAPI(
    title="TwinX API",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
try:
    app.mount("/static", StaticFiles(directory="templates"), name="static")
except Exception:
    # If templates directory doesn't exist, create it
    import os
    os.makedirs("templates", exist_ok=True)
    app.mount("/static", StaticFiles(directory="templates"), name="static")

# Create security scheme
security = HTTPBearer()

# Create separate thread pool executors
build_executor = ThreadPoolExecutor(max_workers=6)  # For build_user_sync
refresh_executor = ThreadPoolExecutor(max_workers=4)  # For refresh/save_users_task

# Flag to control background tasks
app.running = True

# Add after app initialization
app.user_locks = {}  # Store locks for each user (for both building and other operations)
app.current_builds = 0  # Current number of builds in progress
app.build_lock = Lock()  # Lock for protecting current_builds
app.max_concurrent_builds = 4  # Maximum number of concurrent builds
app.users = {}
app.candidates = []
app.refresh_counts = {}
app.agent = None
app.agents = {}
app.grpc_server_url = os.getenv("GRPC_SERVER_URL", "54.169.29.193:8081")
app.agent_prefix = "agent_"

prefix = os.getenv("AGENT_PREFIX")
if prefix:
    app.agent_prefix = prefix

def get_user_lock(username: str) -> bool:
    """Get or create a lock for a specific user and try to acquire it
    
    Returns:
        bool: True if lock was acquired, False if lock is already held
    """
    if username not in app.user_locks:
        app.user_locks[username] = Lock()
    return app.user_locks[username].acquire(blocking=False)

def release_user_lock(username: str) -> None:
    """Release the lock for a specific user"""
    if username in app.user_locks:
        try:
            app.user_locks[username].release()
        except RuntimeError:
            # Lock was not held
            pass

async def load_user_agents():
    usernames = list(app.users.keys())
    usernames.sort()
    for username in usernames:
        if not is_paying_user(username):  
            continue
        
        if username in app.agents:
            continue

        profile = app.users[username]["profile"]
        if profile is None or profile == {}:
            continue

        print("Initializing agent for " + username + "...")
        
        useragent = FullAgentWrapper(
            agent_cls=CallbackAgent,
            name=app.agent_prefix + username,
            description=get_description(username, profile),
            host_address=app.grpc_server_url,
            functions=[search_similar_posts, get_daily_report]
        )
    
        try:
            await useragent.initialize()
            app.agents[username] = useragent
        except Exception as e:
            print(f"Error initializing agent: {str(e)}")
            raise e

async def refresh_users_task():
    """Background task to periodically refresh users list"""
    while app.running:
        await asyncio.sleep(6000)
        try:
            print(f"Refreshing users list at {datetime.now()}")
            finished_users, unfinished_users = load_usernames()
            for username in unfinished_users:
                if username in app.candidates:
                    print(f"Skipping: {username} because it's in candidates")
                    continue
                if username not in app.refresh_counts:
                    app.refresh_counts[username] = get_try_count(username)
                app.refresh_counts[username] += 1
                set_try_count(username, app.refresh_counts[username])
                if app.refresh_counts[username] < 3 or app.refresh_counts[username] % 100 == 0:
                    if get_user_lock(username):
                        try:
                            # Use thread pool executor to avoid blocking event loop
                            await asyncio.get_event_loop().run_in_executor(
                                refresh_executor, build_user, username
                            )
                            app.users[username] = load_user(username)
                        except Exception as e:
                            print(f"Error building user {username}: {str(e)}")
                        finally:
                            release_user_lock(username)
                    else:
                        print(f"Skipping: {username} because it's locked")

            users_len = len(finished_users)
            if users_len == 0:
                print(f"No users to refresh at {datetime.now()}")
                users = load_users()
                for username in users:
                    app.users[username] = users[username]
                await asyncio.sleep(600)
                continue

            # refresh tweets
            print(f"Refreshing tweets for {len(finished_users)} users at {datetime.now()}")
            for i, username in enumerate(finished_users):
                if username in app.candidates:
                    continue
                # user is paying or is kol for news
                if not is_paying_user(username) and not is_kol_user(username):
                    continue
                if get_user_lock(username):
                    try:
                        print(f"Refreshing tweets for {i}/{users_len} user {username} at {datetime.now()}")
                        # Use thread pool executor to avoid blocking event loop
                        await asyncio.get_event_loop().run_in_executor(
                            refresh_executor, refresh_tweets, username
                        )
                    except Exception as e:
                        print(f"Error refreshing tweets for {username}: {str(e)}")
                    finally:
                        release_user_lock(username)
                else:
                    print(f"Skipping tweets refresh for {username} because it's locked")

            # Generate reports using thread pool executor to avoid blocking event loop
            print(f"Generating daily news report at {datetime.now()}")
            try:
                await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        refresh_executor, generate_daily_news_report
                    ),
                    timeout=300  # 5 minutes timeout
                )
            except asyncio.TimeoutError:
                print(f"Daily news report generation timed out after 5 minutes")
            except Exception as e:
                print(f"Error generating daily news report: {str(e)}")

            print(f"Generating daily trading short report at {datetime.now()}")
            try:
                await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        refresh_executor, generate_daily_trading_short_report
                    ),
                    timeout=300  # 5 minutes timeout
                )
            except asyncio.TimeoutError:
                print(f"Daily trading short report generation timed out after 5 minutes")
            except Exception as e:
                print(f"Error generating daily trading short report: {str(e)}")

            print(f"Generating daily trading report at {datetime.now()}")
            try:
                await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        refresh_executor, generate_daily_trading_report
                    ),
                    timeout=600  # 10 minutes timeout
                )
            except asyncio.TimeoutError:
                print(f"Daily trading report generation timed out after 10 minutes")
            except Exception as e:
                print(f"Error generating daily trading report: {str(e)}")

            # refresh profile
            print(f"Refreshing profile for {len(finished_users)} users at {datetime.now()}")
            for i, username in enumerate(finished_users):
                if username in app.candidates:
                    continue
                # user is paying
                if not is_paying_user(username):
                    continue
                if get_user_lock(username):
                    try:
                        print(f"Refreshing profile for {i}/{users_len} user {username} at {datetime.now()}")
                        # Use thread pool executor to avoid blocking event loop
                        await asyncio.get_event_loop().run_in_executor(
                            refresh_executor, refresh_profile, username
                        )
                    except Exception as e:
                        print(f"Error refreshing profile for {username}: {str(e)}")
                    finally:
                        release_user_lock(username)
                else:
                    print(f"Skipping profile refresh for {username} because it's locked")

            print(f"Loading users list at {datetime.now()}")
            users = load_users()
            # Update existing users and add new ones
            for username in users:
                app.users[username] = users[username]
            # Remove users that no longer exist
            users_to_remove = [username for username in app.users if username not in users]
            for username in users_to_remove:
                del app.users[username]
            print(f"Loading user agents at {datetime.now()}")
            await load_user_agents()
            print(f"Users list refreshed at {datetime.now()}")
        except Exception as e:
            print(f"Error refreshing users: {str(e)}")
        await asyncio.sleep(600)  # Refresh every 10 minutes

async def save_users_task():
    """Background task to periodically save users tweets"""
    while app.running:
        await asyncio.sleep(7800)  # Refresh every 13 minutes
        try:
            print(f"Saving users tweets at {datetime.now()}")
            users = list(app.users.keys())
            users.sort()
            for username in users:
                print(f"Saving tweets for {username} at {datetime.now()}")
                if get_user_lock(username):
                    try:
                        # Use thread pool executor to avoid blocking event loop
                        await asyncio.get_event_loop().run_in_executor(
                            refresh_executor, save_tweets, username
                        )
                    except Exception as e:
                        print(f"Error saving tweets for {username}: {str(e)}")
                    finally:
                        release_user_lock(username)
                else:
                    print(f"Skipping saving tweets for {username} because it's locked")
            print(f"Users tweets saved at {datetime.now()}")
        except Exception as e:
            print(f"Error saving users tweets: {str(e)}")
        finally:
            await asyncio.sleep(780)  # Refresh every 13 minutes

# Dependency for token validation
async def validate_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Validate bearer token"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    token = credentials.credentials
    if token != app.bearer_token:
        raise HTTPException(status_code=403, detail="Invalid bearer token")
    
    return token

# Dependency for required fields validation
def validate_required_fields(required_fields: List[str]):
    async def dependency(request: Request):
        try:
            data = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON format")
            
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise HTTPException(
                status_code=400,
                detail=f'Missing required fields: {", ".join(missing_fields)}'
            )
        return data
    return dependency

@app.get("/", response_class=HTMLResponse)
async def report_dashboard():
    """Serve the report dashboard HTML page"""
    try:
        with open("templates/report.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content, status_code=200)
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Report dashboard not found</h1><p>Please ensure templates/report.html exists</p>",
            status_code=404
        )

@app.get("/api/list_info")
async def list_info_api(
    sort_by: Optional[str] = "score",
    order: Optional[str] = "desc",
    token: str = Depends(validate_token)
):
    """List all available users and their info
    
    Args:
        sort_by: Sort by field, can be 'name' or 'score'
        order: Sort order, can be 'asc' or 'desc', default is 'desc'
        token: Authentication token
    """
    try:
        res = []
        for username in app.users:
            resinfo = {
                "username": username,
                "summary": app.users[username].get("summary", {}),
                "scores": app.users[username].get("scores", {}),
                "xinfo": app.users[username].get("xinfo", {}),
            }
            res.append(resinfo)   
        
        # Sort the results
        def get_total_score(x):
            scores = x.get("scores", {})
            return scores.get("total_score", 0)

        if sort_by == "score":
            res.sort(key=get_total_score, reverse=(order == "desc"))
        elif sort_by == "name":
            res.sort(key=lambda x: x["username"], reverse=(order == "desc"))
        else:
            raise HTTPException(status_code=400, detail="Invalid sort_by parameter. Must be 'name' or 'score'")
            
        return {"success": True, "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/get_info")
async def get_info_api(username: str, token: str = Depends(validate_token)):
    """Get info by username"""
    try:
        if not username:
            raise HTTPException(status_code=400, detail="Missing username parameter")

        if username not in app.users:
            if username in app.candidates:
                return {"success": False, "data": "Building..."}    
            raise HTTPException(status_code=404, detail="User not found")
        
        res = {
            "username": username,
            "xinfo": app.users[username].get("xinfo", {}),
            "summary": app.users[username].get("summary", {}),
            "scores": app.users[username].get("scores", {}),
        }    

        return {"success": True, "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/list_users")
async def list_users_api(token: str = Depends(validate_token)):
    """List all available users"""
    try:
        accounts = list(app.users.keys())
        accounts.sort()  # Sort the accounts list alphabetically
        return {"success": True, "data": accounts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/get_profile")
async def get_profile_api(username: str, token: str = Depends(validate_token)):
    """Get a specific profile by username"""
    try:
        if not username:
            raise HTTPException(status_code=400, detail="Missing username parameter")

        if username not in app.users:
            if username in app.candidates:
                return {"success": False, "data": "Building..."} 
            raise HTTPException(status_code=404, detail="User not found")
        
        profile = app.users[username].get("profile", {})          
        return {"success": True, "data": profile}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/get_xinfo")
async def get_xinfo_api(username: str, token: str = Depends(validate_token)):
    """Get x info by username"""
    try:
        if not username:
            raise HTTPException(status_code=400, detail="Missing username parameter")

        if username not in app.users:
            if username in app.candidates:
                return {"success": False, "data": "Building..."} 
            raise HTTPException(status_code=404, detail="User xinfo not found")

        xinfo = app.users[username].get("xinfo", {})        
        return {"success": True, "data": xinfo}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/get_conversation")
async def get_conversation_api(
    username: str,
    conversation_id: Optional[str] = None,
    recent_n_messages: Optional[int] = 128,
    token: str = Depends(validate_token)
):
    """Get conversation by username"""
    try:
        if not username:
            raise HTTPException(status_code=400, detail="Missing username parameter")

        if conversation_id is None or conversation_id == "":
            conversation_id = membase_id + "_" + username

        user_memory = app.agent._memory.get_memory(conversation_id)
        if not user_memory:
            raise HTTPException(status_code=404, detail="memory not found")
        app.agent._memory.load_from_hub(conversation_id)

        messages = user_memory.get(recent_n=recent_n_messages)
        res = []
        for msg in messages:
            res.append({
                "role": msg.role,
                "content": msg.content
            })

        return {"success": True, "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate")
async def generate_profile_api(
    token: str = Depends(validate_token),
    data: Dict[str, Any] = Depends(validate_required_fields(['username']))
):
    """Generate a new profile based on username"""
    try:
        username = data['username']
        
        if len(username) > 15:  # Add length validation (twitter username is no longer than 15 characters) 
            raise HTTPException(status_code=400, detail="Username too long")
            
        if username not in app.users:
            if username not in app.candidates:
                app.candidates.append(username)
                # create a new dir in outputs/{username}
                # check if the dir exists or is dir
                if not is_user_exists(username):
                    init_user(username)
                    build_executor.submit(build_user_sync, username)
                return {"success": True, "data": "start building..."}
            else:
                return {"success": True, "data": "already in building..."}
        else:
            return {"success": True, "data": "already built"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def build_user_sync(username: str):
    """Synchronously build user profile with concurrency control"""
    # Try to acquire the user lock
    if not get_user_lock(username):
        print(f"Build already in progress for {username}")
        return

    # Check if we've reached max concurrent builds
    with app.build_lock:
        if app.current_builds >= app.max_concurrent_builds:
            print(f"Max concurrent builds reached, skipping {username}")
            release_user_lock(username)
            if username in app.candidates:
                app.candidates.remove(username)
            return
        app.current_builds += 1
    
    try:
        print(f"Starting build for {username}")
        update_user_status(username, "state", "building")
        build_user(username)
        update_user_status(username, "state", "built")
        app.users[username] = load_user(username)

        print(f"Successfully completed build for {username}")
    except Exception as e:
        print(f"Error building user {username}: {str(e)}")
    finally:
        if username in app.candidates:
            app.candidates.remove(username)
        with app.build_lock:
            app.current_builds -= 1
        release_user_lock(username)

@app.post("/api/chat")
async def chat_api(
    request: Request,
    token: str = Depends(validate_token),
    data: Dict[str, Any] = Depends(validate_required_fields(['username', 'message']))
):
    """Chat with a specific profile using username"""
    try:
        # Log request details for debugging
        print(f"=== Chat API Request Debug ===")
        print(f"Request URL: {request.url}")
        print(f"Request method: {request.method}")
        print(f"Request headers: {dict(request.headers)}")
        print(f"Request body: {data}")
        print(f"Bearer token: {token}")
        
        username = data['username']
        prompt = data.get('prompt', "")
        message = data['message']
        prompt_mode = data.get('prompt_mode', "append")
        
        print(f"Username: {username}")
        print(f"Message: {message}")
        print(f"Message starts with @: {message.startswith('@')}")
        
        conversation_id = data.get('conversation_id', None)
        if conversation_id is None or conversation_id == "":
            conversation_id = membase_id + "_" + username

        if username not in app.users:
            raise HTTPException(status_code=404, detail="User profile not found")

        # TODO: may change due to another task
        switch_user(username)
        profile = app.users[username]["profile"]
        description = get_description(username, profile)
        if prompt != "":
            print(f"Prompt mode: {prompt_mode}")
            print(f"Prompt: {prompt}")
            
            if prompt_mode == "replace":
                description = prompt
            else:
                description = description + "\n\n" + prompt

        if username in app.agents:
            print(f"Using user agent for {username}")
            uagent = app.agents[username]
            response = await uagent.process_query(
                message,
                use_history=False,
                system_prompt=description,
                conversation_id=conversation_id
            )
            print(f"User agent response: {response[:100]}...")
            return {"success": True, "data": response}
        
        # Run the async operation synchronously
        print(f"Using main agent")
        response = await app.agent.process_query(
            message,
            use_history=False,
            system_prompt=description,
            conversation_id=conversation_id
        )
        print(f"Main agent response: {response[:100]}...")
        return {"success": True, "data": response}
    except Exception as e:
        print(f"Error in chat_api: {str(e)}")
        print(f"Exception type: {type(e).__name__}")
        raise HTTPException(status_code=500, detail=str(e))

def _stream_chat_base(
    username: str,
    message: str,
    description: str,
    conversation_id: str,
    progress_config: dict = None,
    chunking_config: dict = None
):
    """Base streaming chat function to reduce code duplication"""
    
    # Default progress configuration for basic streaming
    if progress_config is None:
        progress_config = {
            "messages": [
                "正在分析您的请求...",
                "正在生成回复内容...",
                "正在优化回复质量...",
                "即将完成...",
                "正在处理中...",
                "请稍候...",
                "正在准备回复...",
                "正在整理信息..."
            ],
            "interval": 3.0,
            "progress_calc": lambda elapsed: min(90, (elapsed / 150) * 90)
        }
    
    # Default chunking configuration for basic streaming
    if chunking_config is None:
        chunking_config = {
            "type": "character",
            "size": 20,
            "delay_base": 0.05,
            "delay_per_char": 0.002
        }
    
    async def generate_base_stream():
        try:
            start_time = time.time()
            
            # Send initial connection message
            yield f"data: {json.dumps({'success': True, 'data': '', 'status': 'connecting'}, ensure_ascii=False)}\n\n"
            
            # Send processing started message
            yield f"data: {json.dumps({'success': True, 'data': '', 'status': 'processing', 'message': '正在处理您的请求...'}, ensure_ascii=False)}\n\n"
            
            # Start processing in background
            if username in app.agents:
                print(f"Using user agent for {username}")
                uagent = app.agents[username]
                processing_task = asyncio.create_task(
                    uagent.process_query(
                        message,
                        use_history=False,
                        system_prompt=description,
                        conversation_id=conversation_id
                    )
                )
            else:
                print(f"Using main agent")
                processing_task = asyncio.create_task(
                    app.agent.process_query(
                        message,
                        use_history=False,
                        system_prompt=description,
                        conversation_id=conversation_id
                    )
                )
            
            # Send progress updates during processing
            message_index = 0
            
            while not processing_task.done():
                # Check for timeout (150 seconds)
                elapsed_time = time.time() - start_time
                if elapsed_time > 150:
                    # Force cancel the task
                    processing_task.cancel()
                    yield f"data: {json.dumps(({'success': False, 'error': '处理超时，请稍后重试', 'status': 'timeout', 'is_complete': True, 'elapsed_time': round(elapsed_time, 1)}), ensure_ascii=False)}\n\n"
                    return
                
                # Get current message (cycle through the list)
                current_message = progress_config["messages"][message_index % len(progress_config["messages"])]
                
                # Calculate elapsed time and progress
                elapsed_time = time.time() - start_time
                progress_percent = progress_config["progress_calc"](elapsed_time)
                
                # Send progress message
                yield f"data: {json.dumps(({'success': True, 'data': '', 'status': 'processing', 'message': current_message, 'progress': round(progress_percent, 1), 'elapsed_time': round(elapsed_time, 1)}), ensure_ascii=False)}\n\n"
                
                # Wait before next message
                await asyncio.sleep(progress_config["interval"])
                
                # Move to next message
                message_index += 1
            
            # Wait for processing to complete
            response = await processing_task
            
            # Send processing complete message
            yield f"data: {json.dumps(({'success': True, 'data': '', 'status': 'processing_complete', 'progress': 100, 'message': '处理完成，正在发送回复...'}), ensure_ascii=False)}\n\n"
            
            # Stream the response based on chunking configuration
            if chunking_config["type"] == "character":
                # Character-based chunking
                chunk_size = chunking_config["size"]
                total_length = len(response)
                
                for i in range(0, total_length, chunk_size):
                    chunk = response[i:i + chunk_size]
                    progress = min(100, (i + chunk_size) / total_length * 100)
                    
                    data_chunk = {
                        "success": True,
                        "data": chunk,
                        "status": "streaming",
                        "progress": round(progress, 1),
                        "is_complete": i + chunk_size >= total_length,
                        "total_length": total_length,
                        "current_position": i + len(chunk)
                    }
                    yield f"data: {json.dumps(data_chunk, ensure_ascii=False)}\n\n"
                    
                    # Variable delay based on chunk size and content
                    delay = chunking_config["delay_base"] + (len(chunk) * chunking_config["delay_per_char"])
                    await asyncio.sleep(delay)
            
            elif chunking_config["type"] == "word":
                # Word-based chunking
                words = response.split()
                current_chunk = ""
                chunk_count = 0
                total_words = len(words)
                
                for i, word in enumerate(words):
                    current_chunk += word + " "
                    chunk_count += 1
                    
                    # Send chunk when it reaches a certain size or at sentence boundaries
                    if (len(current_chunk) >= 30 or 
                        word.endswith('.') or 
                        word.endswith('!') or 
                        word.endswith('?') or
                        chunk_count >= 5):
                        
                        # Calculate streaming progress
                        streaming_progress = min(100, (i + 1) / total_words * 100)
                        
                        data_chunk = {
                            "success": True,
                            "data": current_chunk.strip(),
                            "status": "streaming",
                            "chunk_number": chunk_count,
                            "streaming_progress": round(streaming_progress, 1),
                            "is_complete": False
                        }
                        yield f"data: {json.dumps(data_chunk, ensure_ascii=False)}\n\n"
                        
                        # Reset for next chunk
                        current_chunk = ""
                        chunk_count = 0
                        
                        # Dynamic delay based on chunk size and word length
                        delay = 0.08 + (len(word) * 0.005)
                        await asyncio.sleep(delay)
                
                # Send any remaining content
                if current_chunk.strip():
                    data_chunk = {
                        "success": True,
                        "data": current_chunk.strip(),
                        "status": "streaming",
                        "chunk_number": chunk_count,
                        "streaming_progress": 100,
                        "is_complete": False
                    }
                    yield f"data: {json.dumps(data_chunk, ensure_ascii=False)}\n\n"
            
            # Send final completion signal
            yield f"data: {json.dumps(({'success': True, 'data': '', 'status': 'complete', 'is_complete': True}), ensure_ascii=False)}\n\n"
            
        except Exception as e:
            error_data = {
                "success": False,
                "error": str(e),
                "status": "error",
                "is_complete": True
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
    
    return generate_base_stream()

@app.post("/api/stream_chat")
async def stream_chat_api(
    request: Request,
    token: str = Depends(validate_token),
    data: Dict[str, Any] = Depends(validate_required_fields(['username', 'message']))
):
    """Stream chat with a specific profile using username"""
    try:
        # Log request details for debugging
        print(f"=== Stream Chat API Request Debug ===")
        print(f"Request URL: {request.url}")
        print(f"Request method: {request.method}")
        print(f"Request headers: {dict(request.headers)}")
        print(f"Request body: {data}")
        print(f"Bearer token: {token}")
        
        username = data['username']
        prompt = data.get('prompt', "")
        message = data['message']
        prompt_mode = data.get('prompt_mode', "append")
        
        print(f"Username: {username}")
        print(f"Message: {message}")
        print(f"Message starts with @: {message.startswith('@')}")
        
        conversation_id = data.get('conversation_id', None)
        if conversation_id is None or conversation_id == "":
            conversation_id = membase_id + "_" + username

        if username not in app.users:
            raise HTTPException(status_code=404, detail="User profile not found")

        # TODO: may change due to another task
        switch_user(username)
        profile = app.users[username]["profile"]
        description = get_description(username, profile)
        if prompt != "":
            print(f"Prompt mode: {prompt_mode}")
            print(f"Prompt: {prompt}")
            
            if prompt_mode == "replace":
                description = prompt
            else:
                description = description + "\n\n" + prompt

        return StreamingResponse(
            _stream_chat_base(
                username,
                message,
                description,
                conversation_id
            ),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Methods": "*",
            }
        )
        
    except Exception as e:
        print(f"Error in stream_chat_api: {str(e)}")
        print(f"Exception type: {type(e).__name__}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stream_chat_smart")
async def stream_chat_smart_api(
    request: Request,
    token: str = Depends(validate_token),
    data: Dict[str, Any] = Depends(validate_required_fields(['username', 'message']))
):
    """Smart streaming chat with intelligent progress tracking"""
    try:
        # Log request details for debugging
        print(f"=== Smart Stream Chat API Request Debug ===")
        print(f"Request URL: {request.url}")
        print(f"Request method: {request.method}")
        print(f"Request headers: {dict(request.headers)}")
        print(f"Request body: {data}")
        print(f"Bearer token: {token}")
        
        username = data['username']
        prompt = data.get('prompt', "")
        message = data['message']
        prompt_mode = data.get('prompt_mode', "append")
        
        print(f"Username: {username}")
        print(f"Message: {message}")
        print(f"Message starts with @: {message.startswith('@')}")
        
        conversation_id = data.get('conversation_id', None)
        if conversation_id is None or conversation_id == "":
            conversation_id = membase_id + "_" + username

        if username not in app.users:
            raise HTTPException(status_code=404, detail="User profile not found")

        # TODO: may change due to another task
        switch_user(username)
        profile = app.users[username]["profile"]
        description = get_description(username, profile)
        if prompt != "":
            print(f"Prompt mode: {prompt_mode}")
            print(f"Prompt: {prompt}")
            
            if prompt_mode == "replace":
                description = prompt
            else:
                description = description + "\n\n" + prompt

        # Smart progress configuration
        smart_progress_config = {
            "messages": [
                "正在分析用户请求...",
                "正在检索相关信息...",
                "正在生成回复内容...",
                "正在优化回复质量...",
                "正在完成最终处理...",
                "正在处理中...",
                "请稍候...",
                "正在准备回复...",
                "正在整理信息..."
            ],
            "interval": 2.0,  # Shorter interval for more responsive feel
            "progress_calc": lambda elapsed: min(95, (elapsed / 150) * 95)  # More aggressive progress
        }
        
        # Smart chunking configuration
        smart_chunking_config = {
            "type": "word",
            "size": 30,
            "delay_base": 0.08,
            "delay_per_char": 0.005
        }

        return StreamingResponse(
            _stream_chat_base(
                username,
                message,
                description,
                conversation_id,
                smart_progress_config,
                smart_chunking_config
            ),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Methods": "*",
            }
        )
        
    except Exception as e:
        print(f"Error in stream_chat_smart_api: {str(e)}")
        print(f"Exception type: {type(e).__name__}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stream_chat_advanced")
async def stream_chat_advanced_api(
    request: Request,
    token: str = Depends(validate_token),
    data: Dict[str, Any] = Depends(validate_required_fields(['username', 'message']))
):
    """Advanced streaming chat with real-time response generation"""
    try:
        # Log request details for debugging
        print(f"=== Advanced Stream Chat API Request Debug ===")
        print(f"Request URL: {request.url}")
        print(f"Request method: {request.method}")
        print(f"Request headers: {dict(request.headers)}")
        print(f"Request body: {data}")
        print(f"Bearer token: {token}")
        
        username = data['username']
        prompt = data.get('prompt', "")
        message = data['message']
        prompt_mode = data.get('prompt_mode', "append")
        
        print(f"Username: {username}")
        print(f"Message: {message}")
        print(f"Message starts with @: {message.startswith('@')}")
        
        conversation_id = data.get('conversation_id', None)
        if conversation_id is None or conversation_id == "":
            conversation_id = membase_id + "_" + username

        if username not in app.users:
            raise HTTPException(status_code=404, detail="User profile not found")

        # TODO: may change due to another task
        switch_user(username)
        profile = app.users[username]["profile"]
        description = get_description(username, profile)
        if prompt != "":
            print(f"Prompt mode: {prompt_mode}")
            print(f"Prompt: {prompt}")
            
            if prompt_mode == "replace":
                description = prompt
            else:
                description = description + "\n\n" + prompt

        # Advanced progress configuration
        advanced_progress_config = {
            "messages": [
                "正在分析用户请求...",
                "正在检索相关信息...",
                "正在生成回复内容...",
                "正在优化回复质量...",
                "正在完成最终处理...",
                "正在处理中...",
                "请稍候...",
                "正在准备回复...",
                "正在整理信息..."
            ],
            "interval": 2.0,
            "progress_calc": lambda elapsed: min(90, (elapsed / 150) * 90)
        }
        
        # Advanced chunking configuration
        advanced_chunking_config = {
            "type": "word",
            "size": 30,
            "delay_base": 0.1,
            "delay_per_char": 0.01
        }

        return StreamingResponse(
            _stream_chat_base(
                username,
                message,
                description,
                conversation_id,
                advanced_progress_config,
                advanced_chunking_config
            ),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Methods": "*",
            }
        )
        
    except Exception as e:
        print(f"Error in stream_chat_advanced_api: {str(e)}")
        print(f"Exception type: {type(e).__name__}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate_tweet")
async def generate_tweet_api(
    token: str = Depends(validate_token),
    data: Dict[str, Any] = Depends(validate_required_fields(['username', 'message']))
):
    """Generate a tweet for a specific profile using username"""
    try:
        username = data['username']
        message = data['message']
            
        conversation_id = data.get('conversation_id', None)
        if conversation_id is None or conversation_id == "":
            conversation_id = membase_id + "_" + username

        if username not in app.users:
            raise HTTPException(status_code=404, detail="User profile not found")

        # TODO: may change due to another task
        switch_user(username)
        profile = app.users[username]["profile"]
        profile_str = json.dumps(profile)

        system_prompt = f"""
        You are a digital twin of {username}, designed to mimic their personality, knowledge, and communication style.
        Your responses should be natural and consistent with the following characteristics:
        {profile_str}
        """

        user_message = f"""
        When you hear about the following news:
        {message}

        1. Search similar posts for the news.
        2. Decide if you want to comment on this news.
        3. If you want to comment, generate three tweet posts.
        4. If you don't want to comment, illustrate your thoughts.

        The output should be in JSON format with the following structure:
        {{
            "want_to_comment": true,  // true if you want to comment, false otherwise
            "reason_for_decision": "explain why you want to comment or not",
            "tweets": [
                {{
                    "tweet": "content you want to post",
                    "reason": "the reason you want to post this"
                }},
                {{
                    "tweet": "...",
                    "reason": "..."
                }},
                {{
                    "tweet": "...",
                    "reason": "..."
                }}
            ]
        }}
        
        Ensure your response is only valid JSON without any other text before or after.
        """

        # Run the async operation synchronously
        response = await app.agent.process_query(
            user_message,
            use_history=False,
            system_prompt=system_prompt,
            conversation_id=conversation_id
        )

        response = convert_to_json(response)
        return {"success": True, "data": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/set_status")
async def set_status_api(
    token: str = Depends(validate_token),
    data: Dict[str, Any] = Depends(validate_required_fields(['username', 'key', 'value']))
):
    """Set status for a specific user
    
    Args:
        username: The username to set status for
        key: The status key to set
        value: The status value to set
    """
    try:
        username = data['username']
        key = data['key']
        value = data['value']
            
        if username not in app.users:
            raise HTTPException(status_code=404, detail="User not found")

        # Get current status from cache
        status = load_user_status(username)
        # Update status
        status[key] = value
        # Save status to both cache and file
        update_user_status(username, key, value)
        
        return {"success": True, "data": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/get_status")
async def get_status_api(
    username: str,
    key: Optional[str] = None,
    token: str = Depends(validate_token)
):
    """Get status for a specific user
    
    Args:
        username: The username to get status for
        key: Optional key to get specific status value. If not specified, returns entire status object
    """
    try:
        if not username:
            raise HTTPException(status_code=400, detail="Missing username parameter")

        if username not in app.users:
            raise HTTPException(status_code=404, detail="User not found")

        status = load_user_status(username)
        
        if key is not None:
            if key not in status:
                return {"success": True, "data": None}
            return {"success": True, "data": status[key]}
            
        return {"success": True, "data": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/get_report")
async def get_report_api(
    date_str: Optional[str] = None,
    language: Optional[str] = "Chinese",
    type: Optional[str] = "news",
    format: Optional[str] = "markdown",
    token: str = Depends(validate_token)
):
    """Get news report
    
    Args:
        date_str: Optional date string in format 'YYYY-MM-DD'. If not specified, returns the latest report.
        language: Optional language for the report (default: "Chinese", alternative: "English").
        type: Optional type of the report (default: "news", alternative: "trading", "trading_short").
        format: Optional output format (default: "markdown", alternative: "json").
    """
    try:
        language = language.lower()
        if language not in ["chinese", "english"]:
            raise HTTPException(status_code=400, detail="Unsupported language. Available options: Chinese, English")

        if format not in ["markdown", "json"]:
            raise HTTPException(status_code=400, detail="Unsupported format. Available options: text, json")

        if date_str is None:
            # Load the latest report
            report = load_report("", language, type)
            if not report or report == "":
                raise HTTPException(status_code=404, detail="Latest report not found")
        else:
            # Load report for specific date
            report = load_report(date_str, language, type)
            if not report or report == "":
                raise HTTPException(status_code=404, detail=f"Report for date {date_str} not found")
        
        # Process different output formats
        if format == "json":
            try:
                # Try to convert Markdown report to structured JSON
                sections = {}
                current_section = ""
                lines = report.split("\n")
                for line in lines:
                    if line.startswith("# "):
                        # Main title
                        title = line[2:].strip()
                        sections["title"] = title
                    elif line.startswith("## "):
                        # Section titles as new blocks
                        current_section = line[3:].strip()
                        sections[current_section] = []
                    elif line.startswith("* ") and current_section:
                        # List items added to current section
                        sections[current_section].append(line[2:].strip())
                    elif line.strip() and current_section and not line.startswith("#"):
                        # Regular text with current section, add to current section
                        if isinstance(sections[current_section], list):
                            sections[current_section].append(line.strip())
                        else:
                            sections[current_section] = line.strip()
                
                return {"success": True, "data": sections}
            except Exception:
                # If parsing fails, return original text with format conversion failure note
                return {"success": True, "data": report, "format_note": "Failed to parse as JSON, returning raw text"}
        else:
            # Default to markdown format
            return {"success": True, "data": report}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check_api(token: str = Depends(validate_token)):
    """Health check endpoint to diagnose system status"""
    try:
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "main_agent": {
                "initialized": app.agent._initialized if app.agent else False,
                "runtime_exists": app.agent._runtime is not None if app.agent else False,
                "runtime_running": getattr(app.agent._runtime, '_running', False) if app.agent and app.agent._runtime else False,
                "host_connection": getattr(app.agent._runtime, '_host_connection', None) is not None if app.agent and app.agent._runtime else False,
            },
            "user_agents": {},
            "grpc_server_url": app.grpc_server_url,
            "total_users": len(app.users),
            "total_agents": len(app.agents),
            "candidates": len(app.candidates)
        }
        
        # Check user agents status
        for username, agent in app.agents.items():
            health_status["user_agents"][username] = {
                "initialized": agent._initialized,
                "runtime_exists": agent._runtime is not None,
                "runtime_running": getattr(agent._runtime, '_running', False) if agent._runtime else False,
                "host_connection": getattr(agent._runtime, '_host_connection', None) is not None if agent._runtime else False,
            }
        
        return {"success": True, "data": health_status}
    except Exception as e:
        print(f"Error in health check: {str(e)}")
        return {"success": False, "error": str(e)}

async def shutdown_app_async():
    """Async cleanup of resources and shutdown of the application"""
    print("Shutting down application...")
    
    # Stop background tasks
    app.running = False
    
    # Close agent resources
    if hasattr(app, 'agent') and app.agent is not None:
        print("Shutting down agent...")
        try:
            await app.agent.stop()
        except Exception as e:
            print(f"Error shutting down main agent: {str(e)}")

    for username in app.agents:
        print("Shutting down agent for " + username + "...")
        try:
            await app.agents[username].stop()
        except Exception as e:
            print(f"Error shutting down agent for {username}: {str(e)}")

    # Shutdown thread pool executors
    print("Shutting down thread pools...")
    try:
        build_executor.shutdown(wait=False)
        refresh_executor.shutdown(wait=False)
    except Exception as e:
        print(f"Error shutting down thread pools: {str(e)}")

    # Cancel the background tasks
    if hasattr(app, 'refresh_task'):
        print("Cancelling refresh task...")
        try:
            app.refresh_task.cancel()
            try:
                await asyncio.wait_for(app.refresh_task, timeout=5.0)
            except asyncio.TimeoutError:
                print("Timeout waiting for refresh task to cancel")
            except asyncio.CancelledError:
                print("Refresh task cancelled successfully")
            except Exception as e:
                print(f"Error waiting for refresh task: {str(e)}")
        except Exception as e:
            print(f"Error cancelling refresh task: {str(e)}")

    if hasattr(app, 'save_task'):
        print("Cancelling save task...")
        try:
            app.save_task.cancel()
            try:
                await asyncio.wait_for(app.save_task, timeout=5.0)
            except asyncio.TimeoutError:
                print("Timeout waiting for save task to cancel")
            except asyncio.CancelledError:
                print("Save task cancelled successfully")
            except Exception as e:
                print(f"Error waiting for save task: {str(e)}")
        except Exception as e:
            print(f"Error cancelling save task: {str(e)}")

    print("Application has been completely shut down")

# Add unified shutdown function
async def graceful_shutdown():
    """Unified shutdown function to avoid multiple shutdown calls"""
    global is_shutting_down
    
    # Ensure shutdown process is executed only once
    if is_shutting_down:
        print("Shutdown already in progress, skipping...")
        return
    
    is_shutting_down = True
    print("Starting graceful shutdown...")
    
    try:
        await shutdown_app_async()
    except Exception as e:
        print(f"Error during graceful shutdown: {str(e)}")
        # Force exit on error
        os._exit(1)

def shutdown_app():
    """Synchronous wrapper for shutdown_app_async"""
    print("Starting shutdown process...")
    
    # Call the async shutdown process through the unified function
    asyncio.run_coroutine_threadsafe(graceful_shutdown(), asyncio.get_event_loop())
    
    # Give some time for the async shutdown process to start
    time.sleep(1)

def signal_handler(sig, frame):
    """Handle termination signals"""
    print(f"Received signal {sig}, gracefully exiting...")
    
    # Set timer for forced exit on timeout
    def force_exit():
        print("Graceful shutdown took too long, forcing exit...")
        os._exit(1)
    
    # Force exit after 15 seconds
    timer = threading.Timer(15.0, force_exit)
    timer.daemon = True
    timer.start()
    
    # Call the synchronous shutdown function
    shutdown_app()
    
    # Don't call sys.exit() immediately to give async shutdown a chance to complete
    # Forced exit will happen via timer or after async shutdown completes

async def initialize(port: int = 5001, bearer_token: str = None) -> None:
    """Initialize"""
    default_system_prompt = """
    You are a digital twin of the user, designed to mimic their personality, knowledge, and communication style. 
    Your responses should be natural and consistent with the user's characteristics.
    
    You have access to the following functions to enhance your capabilities:
    
    1. search_similar_posts(query: str) -> str
       - Purpose: Search for similar posts and content related to given query
       - Use case: When user asks about specific news or topics, find relevant historical posts
       - Returns: Relevant posts and content that match the query
    
    2. get_daily_report(date_str: str = "today", language: str = "chinese", type: str = "news") -> str
       - Purpose: Retrieve pre-generated daily reports summarizing KOL activities
       - Parameters:
         * date_str: "today", "yesterday", or "YYYY-MM-DD" format
         * language: "chinese" or "english"
         * type: "news" (daily summary), "trading" (trading or market analysis), or "trading_short" (concise signals)
       - Use case: When user asks for daily summaries, market analysis, or trading information
       - Returns: Complete report content in specified language and format
    
    Guidelines for using these functions:
    - Use search_similar_posts when user asks about specific news, events, or topics
    - Use get_daily_report when user requests daily summaries, market activities, or trading information
    - Always provide context and explanation when sharing function results
    - Maintain the user's personality and communication style in your responses
    """
    system_prompt = os.getenv("SYSTEM_PROMPT", default_system_prompt)
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Set bearer token from environment variable or command line argument
    app.bearer_token = bearer_token or os.getenv("BEARER_TOKEN")
    if not app.bearer_token:
        raise ValueError("Bearer token must be provided either through --bearer-token argument or BEARER_TOKEN environment variable")

    try:
        users = load_users()
        for username in users:
            app.users[username] = users[username]

    except Exception as e:
        print(f"Error loading users: {str(e)}")
        exit()

    app.agent = FullAgentWrapper(
        agent_cls=CallbackAgent,
        name=membase_id,
        description=system_prompt,
        host_address=app.grpc_server_url,
        functions=[search_similar_posts, get_daily_report]
    )
    
    try:
        await app.agent.initialize()
    except Exception as e:
        print(f"Error initializing agent: {str(e)}")
        exit()

    try:
        await load_user_agents()
    except Exception as e:
        print(f"Error loading user agents: {str(e)}")
        exit()

    # Start the background refresh task and save task as async tasks
    app.refresh_task = asyncio.create_task(refresh_users_task())
    app.save_task = asyncio.create_task(save_users_task())
    print("Background refresh/save tasks started")

    # Start uvicorn server
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    print(f"Starting uvicorn server on port {port}...")
    await server.serve()

if __name__ == "__main__":
    import uvicorn
    parser = argparse.ArgumentParser(description='AIP Personal Agent API Server')
    parser.add_argument('--port', type=int, default=5001, help='Port to run the server on (default: 5001)')
    parser.add_argument('--bearer-token', type=str, default="unibase_personal_agent", help='Bearer token for authentication')
    args = parser.parse_args()
    
    print(f"Initializing TwinX API on port {args.port}")
    
    try:
        # Create new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(initialize(port=args.port, bearer_token=args.bearer_token))
    except KeyboardInterrupt:
        print("Received keyboard interrupt, shutting down...")
        try:
            loop.run_until_complete(graceful_shutdown())
        except Exception as e:
            print(f"Error during shutdown after KeyboardInterrupt: {str(e)}")
    except Exception as e:
        print(f"Error during startup: {str(e)}")
        try:
            loop.run_until_complete(graceful_shutdown())
        except Exception as e:
            print(f"Error during shutdown after startup error: {str(e)}")
    finally:
        try:
            # Cancel all running tasks
            pending = asyncio.all_tasks(loop)
            if pending:
                print(f"Cancelling {len(pending)} pending tasks...")
                for task in pending:
                    task.cancel()
                
                # Wait until all tasks are cancelled with timeout
                try:
                    loop.run_until_complete(asyncio.wait_for(asyncio.gather(*pending, return_exceptions=True), timeout=5.0))
                except asyncio.TimeoutError:
                    print("Timeout waiting for tasks to cancel")
                except Exception as e:
                    print(f"Error waiting for tasks to cancel: {str(e)}")
            
            # Close the loop
            loop.close()
            print("Event loop closed")
        except Exception as e:
            print(f"Error closing event loop: {str(e)}")
        
        print("Application exit complete")
        # Ensure clean exit
        os._exit(0)
    
    