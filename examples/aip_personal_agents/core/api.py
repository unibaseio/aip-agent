import asyncio
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
import time

from membase.chain.chain import membase_id
from aip_agent.agents.custom_agent import CallbackAgent
from aip_agent.agents.full_agent import FullAgentWrapper
from core.build import load_unfinished_users, load_user, load_users, build_user

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
                build_user(username)
            app.users = load_users()
        except Exception as e:
            print(f"Error refreshing users: {str(e)}")
        time.sleep(300)  # Refresh every 5 minutes

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

@app.route('/api/list_users', methods=['GET'])
def list_users():
    """List all available users"""
    try:
        accounts = list(app.users.keys())
        return jsonify({'success': True, 'data': accounts})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/get_profile', methods=['GET'])
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

@app.route('/api/generate', methods=['POST'])
@validate_json
@validate_required_fields(['username'])
def generate_profile_api():
    """Generate a new profile based on username"""
    try:
        data = request.get_json()
        username = data['username']
        
        if len(username) > 50:  # Add length validation
            return jsonify({'success': False, 'error': 'Username too long'}), 400
            
        if username not in app.users:
            if username not in app.candidates:
                app.candidates.append(username)
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
async def chat():
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
        description = "Your act as " + username + " with the following characteristics: " + profile_str
        
        response = await app.agent.process_query(
            message,
            use_history=False,
            system_prompt=description,
            conversation_id=conversation_id
        )
        return jsonify({'success': True, 'data': response})
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500

async def initialize() -> None:
    """Initialize"""
    server_url = os.getenv("SERVER_URL", "13.212.116.103:8081")
    system_prompt = os.getenv("SYSTEM_PROMPT", "You are an assistant")

    app.agent = FullAgentWrapper(
        agent_cls=CallbackAgent,
        name=membase_id,
        description=system_prompt,
        host_address=server_url,
    )
    
    try:
        await app.agent.initialize()
    except Exception as e:
        print(f"Error initializing agent: {str(e)}")

    app.users = load_users()
    app.candidates = []

    # Start the background refresh task in a separate thread
    executor.submit(refresh_users_task)
    app.run(host='0.0.0.0', port=5001)

if __name__ == "__main__":
    asyncio.run(initialize())