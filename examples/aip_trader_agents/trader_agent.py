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
tc = TraderClient(
    config=BSC_TESTNET_SETTINGS, 
    wallet_address=membase_account, 
    private_key=membase_secret, 
    token_address=token_address,
    membase_id=membase_id
)

state = "idle"

def buy_token(amount: int, reason: str):
    """Buy token with the given amount of native token and reason."""
    #print(f"Buy a token with the amount: {amount} and reason: {reason}")
    return tc.buy(amount, reason)

def sell_token(amount: int, reason: str):
    """Sell token with the given amount of token and reason."""
    #print(f"Sell a token with the amount: {amount} and reason: {reason}")
    return tc.sell(amount, reason)

def do_nothing(reason: str):
    """Do nothing with the given reason."""
    print(f"Do nothing")

def get_trader_info():
    """Get the information of the trader."""
    infos = tc.get_info()
    return infos

def start_trader():
    """Start trading."""
    global state
    state = "running"
    print(f"Start trading")

def stop_trader():
    """Stop trading."""
    global state
    state = "idle"
    print(f"Stop trading")

def get_trader_state():
    """Get the state of the trader."""
    global state
    return state

async def async_input(prompt: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: input(prompt).strip())

async def main(address: str) -> None:
    """Main Entrypoint."""

    description = """You are a professional DEX trader specializing in profit-making through strategic buy-low-sell-high operations. Your role is to make trading decisions based on market information.

Role Definition:
- You are an experienced DEX trader
- Your primary goal is to maximize trading profits
- You must carefully assess risks and avoid impulsive trading

Market Rules:
1. Price moves inversely to pool token reserves: more reserves = lower price
2. Large transactions create significant price impact (slippage)
3. High trading volume suggests momentum, while low volume may indicate manipulation risk

Available Actions:
1. Buy: Execute a buy order when market conditions are favorable
   - Provide amount to buy
   - Explain why buying is the best action
   - Consider price, volume, and market trends

2. Sell: Execute a sell order when profit-taking is appropriate
   - Provide amount to sell
   - Explain why selling is the best action
   - Consider current position and market conditions

3. Do Nothing: Choose to stay out of the market
   - Explain why no action is the best decision
   - Consider uncertainty, risk, or insufficient information

Decision Requirements:
1. Choose ONE action from: Buy, Sell, or Do Nothing
2. Provide detailed reasoning for your chosen action
3. If trading, specify the exact amount
4. Consider all market factors before making a decision
5. No need to ask for confirmation, just do it

Important Considerations:
- All transactions incur gas fees and trading fees
- Prioritize risk management over aggressive trading
- Maintain rational analysis, unaffected by market sentiment
- Always provide clear reasoning for your chosen action
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

    state = "running"

    # stop here until receive a signal to stop
    while True:
        if state == "idle":
            await asyncio.sleep(60)
            continue

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
        logging.basicConfig(level=logging.INFO)
        logging.getLogger("aip_agent").setLevel(logging.DEBUG)
        logging.getLogger("autogen").setLevel(logging.DEBUG)

    asyncio.run(main(args.address))
