import argparse
import asyncio
import json
import logging
import time

from aip_agent.agents.full_agent import FullAgentWrapper
from aip_agent.agents.custom_agent import CallbackAgent

from membase.chain.chain import membase_id, membase_account, membase_secret
from membase.chain.util import BSC_TESTNET_SETTINGS
from membase.chain.trader import TraderClient

token_address = "0x2e6b3f12408d5441e56c3C20848A57fd53a78931"
tc = TraderClient(BSC_TESTNET_SETTINGS, membase_account, membase_secret, token_address)

def buy_token(amount: int, reason: str):
    """Buy token with the given amount and reason."""
    #print(f"Buy a token with the amount: {amount} and reason: {reason}")
    return tc.buy(amount, reason)

def sell_token(amount: int, reason: str):
    """Sell token with the given amount and reason."""
    #print(f"Sell a token with the amount: {amount} and reason: {reason}")
    return tc.sell(amount, reason)

def do_nothing(reason: str):
    """Do nothing with the given reason."""
    print(f"Do nothing")

def get_trader_info():
    """Get the information of the trader."""
    infos = tc.get_info()
    return infos

async def async_input(prompt: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: input(prompt).strip())

async def main(address: str) -> None:
    """Main Entrypoint."""

    description = "You are a smart trader on dex. You buy low and sell high to make profit.\n"
    
    description += """
    **Context Rules**
    1. Price moves inversely to pool token reserves: more token reserves = lower price
    2. Large swaps create significant price impact (slippage)
    3. High volume suggests momentum; low volume may indicate manipulation risk
    **Task**
    You need to decide whether to buy or sell token based on the information you get.
    You need to decide the amount to buy or sell based on the information you get.
    You need to show the reason for your decision.
    You need to do nothing if the information is not enough to make a decision.
    **Note**
    Any transaction costs transaction gas fee and swap fee.
    """

    full_agent = FullAgentWrapper(
        agent_cls=CallbackAgent,
        name=membase_id,
        description=description,
        host_address=address,
        functions=[buy_token, sell_token, do_nothing, get_trader_info]
    )
    await full_agent.initialize()

    #await full_agent.load_server("weather_mock_server", "grpc")

    servers = await full_agent._mcp_agent.list_servers()
    print(f"servers: {servers}")

    tools = await full_agent._mcp_agent.list_tools()
    print(f"tools: {tools}")

    # stop here until receive a signal to stop
    while True:
        try:
            infos = tc.get_info()
            json_infos = json.dumps(infos)
            print(f"================================================")
            print(f"infos: {json_infos}")
            print(f"================================================")
            response = await full_agent.process_query(json_infos, use_history=False)
            print(f"================================================")
            print("\n" + response)
            print(f"================================================")
        except Exception as e:
            print(f"\nError: {str(e)}")
        finally:
            await asyncio.sleep(60)

    await full_agent.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run an aip agent.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    parser.add_argument("--address", type=str, help="Address to connect to", default="13.212.116.103:8081")

    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.WARNING)
        logging.getLogger("autogen_core").setLevel(logging.DEBUG)
        file_name = "agent_" + membase_id + ".log"
        handler = logging.FileHandler(file_name)
        logging.getLogger("autogen_core").addHandler(handler)

    asyncio.run(main(args.address))
