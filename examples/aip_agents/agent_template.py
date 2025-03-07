from dotenv import load_dotenv
import os
import asyncio
import os
import time
from aip_agent.agents.full_agent import FullAgentWrapper
from aip_agent.agents.custom_agent import CallbackAgent
from flask import Flask, request
from membase.chain.chain import membase_id

load_dotenv()

app = Flask(__name__)


@app.route("/chat-messages", methods=['POST'])
async def chat_messages() -> any:
    req = request.get_json()
    conversation_id, _, query, _, user = [req[i] for i in (
        'conversation_id', 'inputs', 'query', 'response_mode', 'user')]
    if user is None:
        return {'error': 'invalid user'}
    response = await app.agent.process_query(query, conversation_id=conversation_id)
    return {
        'event': 'message',
        'task_id': '',
        'id': '',
        'message_id': '',
        'conversation_id': conversation_id,  # TODO
        'mode': 'chat',
        'answer': response,
        'metadata': {},
        'created_at': int(time.time())
    }


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
    await app.agent.initialize()
    

if __name__ == "__main__":
    asyncio.run(initialize())
    app.run(host='0.0.0.0', port=5000)