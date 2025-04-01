import argparse
import asyncio
import logging
import gradio as gr

from aip_agent.agents.full_agent import FullAgentWrapper
from aip_agent.agents.custom_agent import CallbackAgent

from membase.chain.chain import membase_id

async def main(address: str, gradio_address: str, gradio_port: int) -> None:
    full_agent = FullAgentWrapper(
        agent_cls=CallbackAgent,
        name=membase_id,
        description="You are an assistant",
        host_address=address,
        server_names=["membase"]
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
    interface.launch(share=False, server_port=gradio_port, prevent_thread_lock=True)
    await full_agent.stop_when_signal()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run an aip agent.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    parser.add_argument("--address", type=str, help="Address to connect to", default="13.212.116.103:8081")

    parser.add_argument('--host', default='localhost', help='Host to bind to')
    parser.add_argument('--port', type=int, default=7860, help='Port to listen on')

    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.WARNING)
        logging.getLogger("autogen_core").setLevel(logging.DEBUG)
        file_name = "agent_" + membase_id + ".log"
        handler = logging.FileHandler(file_name)
        logging.getLogger("autogen_core").addHandler(handler)

    asyncio.run(main(args.address, args.host, args.port))
