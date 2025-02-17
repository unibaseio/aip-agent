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

class ChatUI:
    def __init__(self):
        self.agent = None
        self.llm = None
        
    async def initialize(self):
        await app.initialize()
        self.agent = Agent(
            name="aip_agent",
            instruction="you are an assistant",
            server_names=["agent_hub"],
        )
        await self.agent.initialize()
        self.llm = await self.agent.attach_llm(OpenAIAugmentedLLM)

    async def respond(self, message, chat_history):
        if not self.llm:
            await self.initialize()
            
        response = await self.llm.generate_str(
            message=message,
            request_params=RequestParams(use_history=True, history=chat_history)
        )
        chat_history.append((message, response))
        return "", chat_history

async def main():
    chat_ui = ChatUI()
    await chat_ui.initialize()
    
    with gr.Blocks(title="💬 AIP Agent Chatbot") as demo:
        gr.Markdown("# 💬 IAP Agent Chatbot")
        gr.Markdown("A continuous conversation interface powered by iap-agent")
        
        chatbot = gr.Chatbot(height=500)
        msg = gr.Textbox(label="Your Message")
        clear_btn = gr.Button("Clear History")
        
        msg.submit(
            chat_ui.respond,
            [msg, chatbot],
            [msg, chatbot],
            queue=False
        )
        clear_btn.click(
            lambda: [],
            None,
            chatbot,
            queue=False
        )
    
    demo.launch()

if __name__ == "__main__":
    app = MCPApp(name="aip_app")
    asyncio.run(main())