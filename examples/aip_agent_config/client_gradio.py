import asyncio
import gradio as gr

from aip_agent.app import MCPApp
from aip_agent.agents.agent import Agent
from aip_agent.workflows.llm.augmented_llm_openai import OpenAIAugmentedLLM
from aip_agent.workflows.llm.augmented_llm import RequestParams

from aip_agent.memory.message import Message
from aip_agent.memory.buffered_memory import BufferedMemory

from membase.chain.chain import membase_chain, membase_account, membase_id

from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def initialize_agent():
    await app.initialize()
    agent = Agent(
        name="aip_agent",
        instruction="you are an assistant",
        server_names=["agent_hub"],
    )
    await agent.initialize()
    llm = await agent.attach_llm(OpenAIAugmentedLLM)
    memory = BufferedMemory(persistence_in_remote=True)
    return agent, llm, memory

async def get_response(message, history, llm):
    response = ""
    response = await llm.generate_str(
        message=message, request_params=RequestParams(use_history=True, history=history)
    )
    return response

async def chatbot_interface(prompt, history):
    if not hasattr(chatbot_interface, "agent"):
        chatbot_interface.agent, chatbot_interface.llm, chatbot_interface.memory = await initialize_agent()

    msg = Message(membase_id, prompt, role="user")
    chatbot_interface.memory.add(msg)
    response = await get_response(prompt, history, chatbot_interface.llm)
    msg = Message(membase_id, response, role="user")
    chatbot_interface.memory.add(msg)
    return response

async def main():
    membase_chain.register(membase_id)
    print(f"start agent with account: {membase_account} and id: {membase_id}")
    
    interface = gr.ChatInterface(
        fn=chatbot_interface,
        type='messages',
        title="💬 AIP Agent Chatbot",
        description="A Gradio chatbot powered by aip-agent"
    )
    interface.launch()

if __name__ == "__main__":
    app = MCPApp(name="aip_app")
    asyncio.run(main())
