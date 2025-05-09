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
from typing import Optional, List, Dict, Any
from threading import Lock

from membase.chain.chain import membase_id
from aip_agent.agents.custom_agent import CallbackAgent
from aip_agent.agents.full_agent import FullAgentWrapper
from core.build import get_user_xinfo, load_user, load_users, build_user, refresh_user
from core.common import init_user, is_user_exists, load_usernames
from core.rag import search_similar_posts, switch_user
from core.save import save_tweets

app = FastAPI(
    title="TwinX API",
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

# Add after app initialization
app.build_locks = {}  # Store build locks for each user
app.current_builds = 0  # Current number of builds in progress
app.build_lock = Lock()  # Lock for protecting current_builds
app.max_concurrent_builds = 4  # Maximum number of concurrent builds
app.user_locks = {}  # Store locks for each user to prevent concurrent operations

def get_user_lock(username: str) -> Lock:
    """Get or create a lock for a specific user"""
    if username not in app.user_locks:
        app.user_locks[username] = Lock()
    return app.user_locks[username]

def refresh_users_task():
    """Background task to periodically refresh users list"""
    while True:
        try:
            print(f"Refreshing users list at {datetime.now()}")
            finished_users, unfinished_users = load_usernames()
            for username in unfinished_users:
                if username in app.candidates:
                    print(f"Skipping: {username} because it's in candidates")
                    continue
                if username not in app.refresh_counts:
                    app.refresh_counts[username] = 0
                app.refresh_counts[username] += 1
                if app.refresh_counts[username] < 3 or app.refresh_counts[username] % 10 == 0:
                    with get_user_lock(username):
                        build_user(username)

            xinfo = {}
            users_len = len(finished_users)
            if users_len == 0:
                print(f"No users to refresh at {datetime.now()}")
                time.sleep(600)
                continue
            for i, username in enumerate(finished_users):
                if username not in app.candidates:
                    if username not in unfinished_users:
                        with get_user_lock(username):
                            print(f"Refreshing {i}/{users_len} user {username} at {datetime.now()}")
                            refresh_user(username)
                xinfo[username] = get_user_xinfo(username)
                app.users[username] = load_user(username)
            app.xinfo = xinfo
            app.users = load_users()
            print(f"Users list refreshed at {datetime.now()}")
        except Exception as e:
            print(f"Error refreshing users: {str(e)}")
        time.sleep(600)  # Refresh every 10 minutes

def save_users_task():
    """Background task to periodically save users tweets"""
    while True:
        time.sleep(780)  # Refresh every 13 minutes
        try:
            print(f"Saving users tweets at {datetime.now()}")
            app.users = load_users()
            users = list(app.users.keys())
            users.sort()
            for username in users:
                print(f"Saving tweets for {username} at {datetime.now()}")
                with get_user_lock(username):
                    save_tweets(username)
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
async def list_info(
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
            xinfo = {
                "username": username,
            }    

            xinfo["summary"] = app.users[username].get("summary", {})
            xinfo["scores"] = app.users[username].get("scores", {})
            if username in app.xinfo:
                xinfo["xinfo"] = app.xinfo[username]

            res.append(xinfo)   
        
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
async def get_info(username: str, token: str = Depends(validate_token)):
    """Get info by username"""
    try:
        if not username:
            raise HTTPException(status_code=400, detail="Missing username parameter")

        if username not in app.users:
            if username in app.candidates:
                return {"success": False, "data": "Building..."}    
            raise HTTPException(status_code=404, detail="User not found")

        xinfo = app.xinfo[username]
        if not xinfo:
            raise HTTPException(status_code=404, detail="Xinfo not found")
        
        res = {
            "username": username,
            "xinfo": xinfo,
            "summary": app.users[username].get("summary", {}),
            "scores": app.users[username].get("scores", {}),
        }    

        return {"success": True, "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/list_users")
async def list_users(token: str = Depends(validate_token)):
    """List all available users"""
    try:
        accounts = list(app.users.keys())
        accounts.sort()  # Sort the accounts list alphabetically
        return {"success": True, "data": accounts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/get_profile")
async def get_profile(username: str, token: str = Depends(validate_token)):
    """Get a specific profile by username"""
    try:
        if not username:
            raise HTTPException(status_code=400, detail="Missing username parameter")

        if username not in app.users:
            if username in app.candidates:
                return {"success": False, "data": "Building..."} 
            raise HTTPException(status_code=404, detail="User not found")
        
        profile = app.users[username]          
        return {"success": True, "data": profile}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/get_xinfo")
async def get_xinfo(username: str, token: str = Depends(validate_token)):
    """Get x info by username"""
    try:
        if not username:
            raise HTTPException(status_code=400, detail="Missing username parameter")

        if username not in app.xinfo:
            if username in app.candidates:
                return {"success": False, "data": "Building..."} 
            raise HTTPException(status_code=404, detail="User xinfo not found")

        xinfo = app.xinfo[username]        
        return {"success": True, "data": xinfo}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/get_conversation")
async def get_conversation(
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
    # If already building, return directly
    if username in app.build_locks and app.build_locks[username].locked():
        print(f"Build already in progress for {username}")
        return

    # Check if we've reached max concurrent builds
    with app.build_lock:
        if app.current_builds >= app.max_concurrent_builds:
            print(f"Max concurrent builds reached, skipping {username}")
            if username in app.candidates:
                app.candidates.remove(username)
            return
        app.current_builds += 1

    # Get build lock for this user
    if username not in app.build_locks:
        app.build_locks[username] = Lock()
    
    with app.build_locks[username]:
        try:
            print(f"Starting build for {username}")
            build_user(username)
            app.users[username] = load_user(username)
            app.xinfo[username] = get_user_xinfo(username)
            print(f"Successfully completed build for {username}")
        except Exception as e:
            print(f"Error building user {username}: {str(e)}")
        finally:
            if username in app.candidates:
                app.candidates.remove(username)
            with app.build_lock:
                app.current_builds -= 1

@app.post("/api/chat")
async def chat(
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
        profile_str = json.dumps(profile)
        description = "You act as a digital twin of " + username + ", designed to mimic personality, knowledge, and communication style. \n"
        description = description + "You donot need to mention that you are a digital twin. \n"
        description = description + "Your responses should be natural and consistent with the following characteristics: \n"
        description = description + profile_str
        
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

async def initialize(port: int = 5001, bearer_token: str = None) -> None:
    """Initialize"""
    grpc_server_url = os.getenv("GRPC_SERVER_URL", "13.212.116.103:8081")
    system_prompt = os.getenv("SYSTEM_PROMPT", "You are a digital twin of the user, designed to mimic their personality, knowledge, and communication style. Your responses should be natural and consistent with the user's characteristics.")
    
    # Set bearer token from environment variable or command line argument
    app.bearer_token = bearer_token or os.getenv("BEARER_TOKEN")
    if not app.bearer_token:
        raise ValueError("Bearer token must be provided either through --bearer-token argument or BEARER_TOKEN environment variable")

    app.agent = FullAgentWrapper(
        agent_cls=CallbackAgent,
        name=membase_id,
        description=system_prompt,
        host_address=grpc_server_url,
        functions=[search_similar_posts]
    )
    
    try:
        await app.agent.initialize()
    except Exception as e:
        print(f"Error initializing agent: {str(e)}")
        exit()

    try:
        app.users = load_users()
        app.xinfo = {}
        for username in app.users:
            app.xinfo[username] = get_user_xinfo(username)

        app.candidates = []
        app.refresh_counts = {}
    except Exception as e:
        print(f"Error loading users: {str(e)}")
        exit()

    # Start the background refresh task in a separate thread
    refresh_executor.submit(refresh_users_task)
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
    asyncio.run(initialize(port=args.port, bearer_token=args.bearer_token))
    
    