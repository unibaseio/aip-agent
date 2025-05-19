import asyncio
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException, Depends, Header, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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

from membase.chain.chain import membase_id
from aip_agent.agents.custom_agent import CallbackAgent
from aip_agent.agents.full_agent import FullAgentWrapper
from core.build import (
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
    update_user_status
)
from core.rag import search_similar_posts, switch_user
from core.save import save_tweets
from core.utils import convert_to_json

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: setup code goes here
    print("Application startup...")
    yield
    # Shutdown: cleanup code goes here
    print("Application shutdown...")
    shutdown_app()

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

# Create security scheme
security = HTTPBearer()

# Create separate thread pool executors
build_executor = ThreadPoolExecutor(max_workers=6)  # For build_user_sync
refresh_executor = ThreadPoolExecutor(max_workers=2)  # For refresh/save_users_task

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
    new_agents = []
    for username in app.users:
        if not is_paying_user(username):  
            continue
        
        if username in app.agents:
            continue

        profile = app.users[username]["profile"]
        if profile is None or profile == {}:
            continue

        print("Initializing agent for " + username + "...")
        app.agents[username] = FullAgentWrapper(
            agent_cls=CallbackAgent,
            name="agent_" + username,
            description=get_description(username, profile),
            host_address=app.grpc_server_url,
            functions=[search_similar_posts]
        )
        new_agents.append(username)
    
    try:
        for username in new_agents:
            await app.agents[username].initialize()
    except Exception as e:
        print(f"Error initializing agent: {str(e)}")
        raise e

async def refresh_users_task():
    """Background task to periodically refresh users list"""
    while app.running:
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
                            build_user(username)
                            app.users[username] = load_user(username)
                        finally:
                            release_user_lock(username)
                    else:
                        print(f"Skipping: {username} because it's locked")

            users_len = len(finished_users)
            if users_len == 0:
                print(f"No users to refresh at {datetime.now()}")
                app.users = load_users()
                await asyncio.sleep(600)
                continue

            # refresh tweets
            for i, username in enumerate(finished_users):
                if username in app.candidates:
                    continue
                # user is paying or is kol for news
                if not is_paying_user(username) and not is_kol_user(username):
                    continue
                if get_user_lock(username):
                    try:
                        print(f"Refreshing tweets for {i}/{users_len} user {username} at {datetime.now()}")
                        refresh_tweets(username)
                    finally:
                        release_user_lock(username)
                else:
                    print(f"Skipping tweets refresh for {username} because it's locked")

            # refresh profile
            for i, username in enumerate(finished_users):
                if username in app.candidates:
                    continue
                # user is paying
                if not is_paying_user(username):
                    continue
                if get_user_lock(username):
                    try:
                        print(f"Refreshing profile for {i}/{users_len} user {username} at {datetime.now()}")
                        refresh_profile(username)
                        app.users[username] = load_user(username)
                    finally:
                        release_user_lock(username)
                else:
                    print(f"Skipping profile refresh for {username} because it's locked")

            app.users = load_users()
            await load_user_agents()
            print(f"Users list refreshed at {datetime.now()}")
        except Exception as e:
            print(f"Error refreshing users: {str(e)}")
        await asyncio.sleep(600)  # Refresh every 10 minutes

def save_users_task():
    """Background task to periodically save users tweets"""
    while app.running:
        time.sleep(780)  # Refresh every 13 minutes
        try:
            print(f"Saving users tweets at {datetime.now()}")
            app.users = load_users()
            users = list(app.users.keys())
            users.sort()
            for username in users:
                print(f"Saving tweets for {username} at {datetime.now()}")
                if get_user_lock(username):
                    try:
                        save_tweets(username)
                    except Exception as e:
                        print(f"Error saving tweets for {username}: {str(e)}")
                    finally:
                        release_user_lock(username)
                else:
                    print(f"Skipping saving tweets for {username} because it's locked")
            print(f"Users tweets saved at {datetime.now()}")
        except Exception as e:
            print(f"Error saving users tweets: {str(e)}")

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
        app.users[username] = load_user(username)
        update_user_status(username, "state", "built")

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
    token: str = Depends(validate_token),
    data: Dict[str, Any] = Depends(validate_required_fields(['username', 'message']))
):
    """Chat with a specific profile using username"""
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
        description = get_description(username, profile)
        
        # Run the async operation synchronously
        response = await app.agent.process_query(
            message,
            use_history=False,
            system_prompt=description,
            conversation_id=conversation_id
        )
        return {"success": True, "data": response}
    except Exception as e:
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

async def shutdown_app_async():
    """Async cleanup of resources and shutdown of the application"""
    print("Shutting down application...")
    
    # Stop background tasks
    app.running = False
    
    # Shutdown thread pool executors
    print("Shutting down thread pools...")
    build_executor.shutdown(wait=False)
    refresh_executor.shutdown(wait=False)
    
    # Close agent resources
    if hasattr(app, 'agent'):
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

    print("Application has been completely shut down")

def shutdown_app():
    """Synchronous wrapper for shutdown_app_async"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're in a running event loop, create a task and wait for it
            future = asyncio.run_coroutine_threadsafe(shutdown_app_async(), loop)
            # Wait for the shutdown to complete with a timeout
            try:
                future.result(timeout=10)  # 10 seconds timeout
            except asyncio.TimeoutError:
                print("Warning: Shutdown timed out after 10 seconds")
        else:
            # If we're not in a running event loop, run until complete
            loop.run_until_complete(shutdown_app_async())
    except Exception as e:
        print(f"Error during shutdown: {str(e)}")

def signal_handler(sig, frame):
    """Handle termination signals"""
    print(f"Received signal {sig}, gracefully exiting...")
    shutdown_app()
    # Give a small delay to allow pending tasks to complete
    time.sleep(1)
    sys.exit(0)


async def initialize(port: int = 5001, bearer_token: str = None) -> None:
    """Initialize"""
    system_prompt = os.getenv("SYSTEM_PROMPT", "You are a digital twin of the user, designed to mimic their personality, knowledge, and communication style. Your responses should be natural and consistent with the user's characteristics.")
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Set bearer token from environment variable or command line argument
    app.bearer_token = bearer_token or os.getenv("BEARER_TOKEN")
    if not app.bearer_token:
        raise ValueError("Bearer token must be provided either through --bearer-token argument or BEARER_TOKEN environment variable")

    try:
        app.users = load_users()

        app.candidates = []
        app.refresh_counts = {}
    except Exception as e:
        print(f"Error loading users: {str(e)}")
        exit()

    app.agent = FullAgentWrapper(
        agent_cls=CallbackAgent,
        name=membase_id,
        description=system_prompt,
        host_address=app.grpc_server_url,
        functions=[search_similar_posts]
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

    # Start the background refresh task in a separate thread
    asyncio.create_task(refresh_users_task())
    refresh_executor.submit(save_users_task)
    print("Background refresh/save task started")

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
        loop.run_until_complete(shutdown_app_async())
    except Exception as e:
        print(f"Error during startup: {str(e)}")
        loop.run_until_complete(shutdown_app_async())
    finally:
        try:
            # Cancel all running tasks
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            
            # Wait until all tasks are cancelled
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            
            # Close the loop
            loop.close()
        except Exception as e:
            print(f"Error closing event loop: {str(e)}")
    
    