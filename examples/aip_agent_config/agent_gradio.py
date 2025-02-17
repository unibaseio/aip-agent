import asyncio
import gradio as gr

from aip_agent.app import MCPApp
from aip_agent.agents.agent import Agent
from aip_agent.workflows.llm.augmented_llm_openai import OpenAIAugmentedLLM
from aip_agent.workflows.llm.augmented_llm import RequestParams

from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


print("reload local agent")

async def initialize_agent():
    await app.initialize()
    agent = Agent(
        name="aip_agent",
        instruction="you are an assistant",
        server_names=["agent_hub"],
    )
    await agent.initialize()
    llm = await agent.attach_llm(OpenAIAugmentedLLM)
    return agent, llm

async def get_response(prompt, llm):
    response = ""
    response = await llm.generate_str(
        message=prompt, request_params=RequestParams(use_history=True)
    )
    return response

async def chatbot_interface(prompt):
    if not hasattr(chatbot_interface, "agent"):
        chatbot_interface.agent, chatbot_interface.llm = await initialize_agent()

    response = await get_response(prompt, chatbot_interface.llm)
    return response

async def main():
    interface = gr.Interface(
        fn=chatbot_interface,
        inputs="text",
        outputs="text",
        title="💬 AIP Agent Chatbot",
        description="A Gradio chatbot powered by aip-agent"
    )
    interface.launch()

if __name__ == "__main__":
    app = MCPApp(name="aip_app")
    asyncio.run(main())
