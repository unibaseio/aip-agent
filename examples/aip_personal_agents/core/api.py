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
from core.build import get_user_info, load_unfinished_users, load_user, load_users, build_user

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
                if username not in app.candidates:
                    build_user(username)
            app.users = load_users()
            for username in app.users:
                app.xinfo[username] = get_user_info(username)
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
            
        profile = app.users[username]
        if not profile:
            if username in app.candidates:
                return jsonify({'success': False, 'data': "building..."})    
            else:
                return jsonify({'success': False, 'error': 'Profile not found'}), 404
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
            
        xinfo = app.xinfo[username]
        if not xinfo:
            return jsonify({'success': False, 'error': 'Xinfo not found'}), 404
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
        if not conversation_id:
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
                # create a new file in outputs/{username}_tweets.json
                if not os.path.exists(f"outputs/{username}_tweets.json"):
                    with open(f"outputs/{username}_tweets.json", "w") as f:
                        json.dump([], f)

                executor.submit(build_user_sync, username)
                return jsonify({'success': True, 'data': "start building..."})
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
        if not conversation_id:
            conversation_id = membase_id + "_" + username

        if username not in app.users:
            return jsonify({'success': False, 'error': 'User profile not found'}), 404

        profile = app.users[username]["profile"]
        profile_str = json.dumps(profile)
        description ="You are a digital twin of " + username + ", designed to mimic their personality, knowledge, and communication style. Your responses should be natural and consistent with the following characteristics. \n"
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
    )
    
    try:
        await app.agent.initialize()
    except Exception as e:
        print(f"Error initializing agent: {str(e)}")
        exit()

    app.users = load_users()
    app.xinfo = {}

    for username in app.users:
        app.xinfo[username] = get_user_info(username)

    app.candidates = []

    # Start the background refresh task in a separate thread
    executor.submit(refresh_users_task)
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='AIP Personal Agent API Server')
    parser.add_argument('--port', type=int, default=5001, help='Port to run the server on (default: 5001)')
    parser.add_argument('--bearer-token', type=str, default="unibase_personal_agent", help='Bearer token for authentication')
    args = parser.parse_args()
    
    asyncio.run(initialize(port=args.port, bearer_token=args.bearer_token))