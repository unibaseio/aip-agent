import argparse
import asyncio
import logging
import gradio as gr

from aip_agent.agents.full_agent import FullAgentWrapper
from aip_agent.agents.custom_agent import CallbackAgent

from membase.chain.chain import membase_id

async def main(address: str) -> None:
    full_agent = FullAgentWrapper(
        agent_cls=CallbackAgent,
        name=membase_id,
        description="You are an assistant",
        host_address=address,
        server_names=[]
    )
    await full_agent.initialize()

    async def chatbot_interface(prompt, history):
        return await full_agent.process_query(prompt)

    interface = gr.ChatInterface(
        fn=chatbot_interface,
        type='messages',
        title="💬 AIP Agent Chatbot",
        description="A Gradio chatbot powered by aip-agent: "+ membase_id
    )
    interface.launch(share=False, prevent_thread_lock=True)
    await full_agent.stop_when_signal()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run an aip agent.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    parser.add_argument("--address", type=str, help="Address to connect to", default="13.212.116.103:8081")
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
        logging.getLogger("aip_agent").setLevel(logging.DEBUG)
        logging.getLogger("autogen").setLevel(logging.DEBUG)


    asyncio.run(main(args.address))
