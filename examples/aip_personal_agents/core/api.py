import asyncio
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
import time
import argparse

from membase.chain.chain import membase_id
from aip_agent.agents.custom_agent import CallbackAgent
from aip_agent.agents.full_agent import FullAgentWrapper
from core.build import get_user_xinfo, load_unfinished_users, load_user, load_users, build_user, refresh_profile, refresh_tweets
from core.rag import search_similar_posts, switch_user
from core.save import save_tweets
from core.common import init_user, is_user_exists

app = Flask(__name__)
CORS(app)

# Background task to refresh users periodically
def refresh_users_task():
    """Background task to periodically refresh users list"""
    while True:
        try:
            print(f"Refreshed users list at {datetime.now()}")
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
                refresh_profile(username)
                xinfo[username] = get_user_xinfo(username)
            app.xinfo = xinfo
        except Exception as e:
            print(f"Error refreshing users: {str(e)}")
        time.sleep(600)  # Refresh every 10 minutes

# Create a thread pool executor
executor = ThreadPoolExecutor(max_workers=4)

def validate_json(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Content-Type must be application/json'}), 415
        try:
            request.get_json()
        except Exception as e:
            return jsonify({'success': False, 'error': 'Invalid JSON format'}), 400
        return f(*args, **kwargs)
    return decorated_function

def validate_required_fields(required_fields):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            data = request.get_json()
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return jsonify({
                    'success': False,
                    'error': f'Missing required fields: {", ".join(missing_fields)}'
                }), 400
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'success': False, 'error': 'Missing Authorization header'}), 401
        
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
            
        if token != app.bearer_token:
            return jsonify({'success': False, 'error': 'Invalid bearer token'}), 403
            
        return f(*args, **kwargs)
    return decorated_function

@app.route('/api/list_info', methods=['GET'])
@validate_token
def list_info():
    """List all available users and their info"""
    try:
        res = []
        for username in app.users:
            xinfo = {
                "username": username,
            }    

            xinfo["summary"] = app.users[username].get("summary", {})
            if username in app.xinfo:
                xinfo["xinfo"] = app.xinfo[username]

            res.append(xinfo)   
        return jsonify({'success': True, 'data': res})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/get_info', methods=['GET'])
@validate_token
def get_info():
    """Get info by username"""
    try:
        username = request.args.get('username')
        if not username:
            return jsonify({'success': False, 'error': 'Missing username parameter'}), 400

        if username not in app.users:
            if username in app.candidates:
                return jsonify({'success': False, 'data': "Building..."})    
            return jsonify({'success': False, 'error': 'User not found'}), 404

        xinfo = app.xinfo[username]
        if not xinfo:
            return jsonify({'success': False, 'error': 'Xinfo not found'}), 404
        
        res = {
            "username": username,
            "xinfo": xinfo,
            "summary": app.users[username].get("summary", {}),
        }    

        return jsonify({'success': True, 'data': res})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/list_users', methods=['GET'])
@validate_token
def list_users():
    """List all available users"""
    try:
        accounts = list(app.users.keys())
        return jsonify({'success': True, 'data': accounts})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/get_profile', methods=['GET'])
@validate_token
def get_profile():
    """Get a specific profile by username"""
    try:
        username = request.args.get('username')
        if not username:
            return jsonify({'success': False, 'error': 'Missing username parameter'}), 400

        if username not in app.users:
            if username in app.candidates:
                return jsonify({'success': False, 'data': "Building..."}) 
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        profile = app.users[username]          
        return jsonify({'success': True, 'data': profile})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/get_xinfo', methods=['GET'])
@validate_token
def get_xinfo():
    """Get x info by username"""
    try:
        username = request.args.get('username')
        if not username:
            return jsonify({'success': False, 'error': 'Missing username parameter'}), 400

        if username not in app.xinfo:
            if username in app.candidates:
                return jsonify({'success': False, 'data': "Building..."}) 
            return jsonify({'success': False, 'error': 'User xinfo not found'}), 404

        xinfo = app.xinfo[username]        
        return jsonify({'success': True, 'data': xinfo})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/get_conversation', methods=['GET'])
@validate_token
def get_conversation():
    """Get conversation by username"""
    try:
        username = request.args.get('username')
        if not username:
            return jsonify({'success': False, 'error': 'Missing username parameter'}), 400

        conversation_id = request.args.get('conversation_id')
        if conversation_id is None or conversation_id == "":
            conversation_id = membase_id + "_" + username
        
        recent_n_messages = request.args.get('recent_n_messages')
        if not recent_n_messages:
            recent_n_messages = 128
        else:
            try:
                recent_n_messages = int(recent_n_messages)
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 400

        user_memory = app.agent._memory.get_memory(conversation_id)
        if not user_memory:
            return jsonify({'success': False, 'error': 'memory not found'}), 404
        app.agent._memory.load_from_hub(conversation_id)

        messages = user_memory.get(recent_n=recent_n_messages)
        res = []
        for msg in messages:
            res.append({
                "role": msg.role,
                "content": msg.content
            })

        return jsonify({'success': True, 'data': res})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/generate', methods=['POST'])
@validate_json
@validate_required_fields(['username'])
@validate_token
def generate_profile_api():
    """Generate a new profile based on username"""
    try:
        data = request.get_json()
        username = data['username']
        
        if len(username) > 15:  # Add length validation (twitter username is no longer than 15 characters) 
            return jsonify({'success': False, 'error': 'Username too long'}), 400
            
        if username not in app.users:
            if username not in app.candidates:
                app.candidates.append(username)
                # create a new directory in outputs/{username}
                # if the directory exists, it means the user is already built
                if not is_user_exists(username):
                    init_user(username)
                    executor.submit(build_user_sync, username)
                    return jsonify({'success': True, 'data': "start building..."})
                else:
                    return jsonify({'success': True, 'data': "building..."})
            else:
                return jsonify({'success': True, 'data': "building..."})
        else:
            return jsonify({'success': True, 'data': "already built"})
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500

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

@app.route('/api/chat', methods=['POST'])
@validate_json
@validate_required_fields(['username', 'message'])
@validate_token
def chat():
    """Chat with a specific profile using username"""
    try:
        data = request.get_json()
        username = data['username']
        message = data['message']
            
        conversation_id = data.get('conversation_id', None)
        if conversation_id is None or conversation_id == "":
            conversation_id = membase_id + "_" + username

        if username not in app.users:
            return jsonify({'success': False, 'error': 'User profile not found'}), 404

        # TODO: may change due to another task
        switch_user(username)
        profile = app.users[username]["profile"]
        profile_str = json.dumps(profile)
        description = "You act as a digital twin of " + username + ", designed to mimic personality, knowledge, and communication style. \n"
        description = description + "You donot need to mention that you are a digital twin. \n"
        description = description + "Your responses should be natural and consistent with the following characteristics. \n"
        description = description + profile_str
        
        # Run the async operation synchronously
        response = asyncio.run(app.agent.process_query(
            message,
            use_history=False,
            system_prompt=description,
            conversation_id=conversation_id
        ))
        return jsonify({'success': True, 'data': response})
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500

async def initialize(port: int = 5001, bearer_token: str = None) -> None:
    """Initialize"""
    grpc_server_url = os.getenv("GRPC_SERVER_URL", "54.169.29.193:8081")
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
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='AIP Personal Agent API Server')
    parser.add_argument('--port', type=int, default=5001, help='Port to run the server on (default: 5001)')
    parser.add_argument('--bearer-token', type=str, default="unibase_personal_agent", help='Bearer token for authentication')
    args = parser.parse_args()
    
    asyncio.run(initialize(port=args.port, bearer_token=args.bearer_token))