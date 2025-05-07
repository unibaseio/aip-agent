import asyncio
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException, Depends, Header, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import json
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
import time
import argparse
from typing import Optional, List, Dict, Any

from membase.chain.chain import membase_id
from aip_agent.agents.custom_agent import CallbackAgent
from aip_agent.agents.full_agent import FullAgentWrapper
from core.build import get_user_xinfo, load_unfinished_users, load_user, load_users, build_user, refresh_user
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

# Background task to refresh users periodically
def refresh_users_task():
    """Background task to periodically refresh users list"""
    while True:
        try:
            print(f"Refreshing users list at {datetime.now()}")
            unfinished_users = load_unfinished_users()
            for username in unfinished_users:
                if username in app.candidates:
                    continue
                if username not in app.refresh_counts:
                    app.refresh_counts[username] = 0
                app.refresh_counts[username] += 1
                if app.refresh_counts[username] < 3:
                    build_user(username)
                if app.refresh_counts[username] % 10 == 0:  # Only build every 10 attempts
                    build_user(username)
            app.users = load_users()
            users = list(app.users.keys())
            xinfo = {}
            for username in users:
                refresh_user(username)
                xinfo[username] = get_user_xinfo(username)
            app.xinfo = xinfo
            print(f"Users list refreshed at {datetime.now()}")
        except Exception as e:
            print(f"Error refreshing users: {str(e)}")
        time.sleep(600)  # Refresh every 10 minutes

# Create a thread pool executor
executor = ThreadPoolExecutor(max_workers=4)

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
async def list_info(token: str = Depends(validate_token)):
    """List all available users and their info"""
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
                # create a new file in outputs/{username}_tweets.json
                if not os.path.exists(f"outputs/{username}_tweets.json"):
                    with open(f"outputs/{username}_tweets.json", "w") as f:
                        json.dump([], f)

                executor.submit(build_user_sync, username)
                return {"success": True, "data": "start building..."}
            else:
                return {"success": True, "data": "building..."}
        else:
            return {"success": True, "data": "already built"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def build_user_sync(username: str):
    """Synchronously build user profile in a thread"""
    try:
        build_user(username)
        app.users[username] = load_user(username)
        app.xinfo[username] = get_user_xinfo(username)
        # conflict write?
        save_tweets(username)
    except Exception as e:
        print(f"Error building user {username}: {str(e)}")
    finally:
        app.candidates.remove(username)

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
    executor.submit(refresh_users_task)
    print("Background refresh task started")

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
    
    