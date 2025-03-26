import argparse
import asyncio
import json
import logging
import time
import gradio as gr
from datetime import datetime
import sys
from pathlib import Path

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
log_history = []

def update_log(message):
    """Update log and output to both console and file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] {message}"
    log_history.append(log_message)
    print(log_message)

def get_trader_info():
    """Get the information of the trader."""
    infos = tc.get_info()
    return json.dumps(infos, indent=2)

def buy_token(amount: int, reason: str):
    """Buy token with the given amount and reason."""
    result = tc.buy(amount, reason)
    update_log(f"Buy token: amount={amount}, reason={reason}, result={result}")
    return result

def sell_token(amount: int, reason: str):
    """Sell token with the given amount and reason."""
    result = tc.sell(amount, reason)
    update_log(f"Sell token: amount={amount}, reason={reason}, result={result}")
    return result

def do_nothing(reason: str):
    """Do nothing with the given reason."""
    update_log(f"Do nothing: reason={reason}")
    return "No action taken"

def start_trader():
    """Start trading."""
    global state
    state = "running"
    update_log("Start trading")
    return "Trading started"

def stop_trader():
    """Stop trading."""
    global state
    state = "idle"
    update_log("Stop trading")
    return "Trading stopped"

def get_trader_state():
    """Get the state of the trader."""
    global state
    return state

async def process_query(query: str, full_agent):
    """Process a query and update logs."""
    try:
        response = await full_agent.process_query(query, use_history=False)
        update_log(f"Query: \n{query}")
        update_log(f"Response: \n{response}")
        return response
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        update_log(error_msg)
        return error_msg

def create_gradio_interface(full_agent):
    """Create Gradio interface."""
    with gr.Blocks() as demo:
        gr.Markdown("# DEX Trading Agent: " + membase_id)
        
        with gr.Row():
            # left config area
            with gr.Column(scale=1):
                gr.Markdown("## Configuration")
                with gr.Row():
                    start_btn = gr.Button("Start Trading")
                    stop_btn = gr.Button("Stop Trading")
                state_display = gr.Textbox(label="Current State", value=get_trader_state())
                
                with gr.Row():
                    refresh_wallet_btn = gr.Button("Wallet Info")
                    refresh_trade_btn = gr.Button("Trade Info")
                    refresh_logs_btn = gr.Button("Operation Logs")
                history_display = gr.Textbox(label="History Records", value="", lines=10)
                        
            # right log area
            with gr.Column(scale=1):
                gr.Markdown("## Query")
                query_input = gr.Textbox(label="Enter your query", value="analyze the profit", lines=4)
                query_btn = gr.Button("Process Query")
                query_output = gr.Textbox(label="Query Result", lines=10)
                
        
        # event handler
        def start_trader_event(progress=gr.Progress()):
            try:
                progress(0, desc="Starting trader...")
                start_trader()
                progress(1, desc="Trader started")
                return get_trader_state()
            except Exception as e:
                error_msg = f"Error starting trader: {str(e)}"
                update_log(error_msg)
                return "error"
        
        def stop_trader_event(progress=gr.Progress()):
            try:
                progress(0, desc="Stopping trader...")
                stop_trader()
                progress(1, desc="Trader stopped")
                return get_trader_state()
            except Exception as e:
                error_msg = f"Error stopping trader: {str(e)}"
                update_log(error_msg)
                return "error"
        
        def update_trade(progress=gr.Progress()):
            try:
                progress(0, desc="Updating trade info...")
                result = get_trader_info()
                result_dict = json.loads(result)
                progress(1, desc="Trade info updated")
                if "trade_infos" in result_dict:
                    # latest log first
                    trade_info = result_dict["trade_infos"]["infos"][::-1]
                    return json.dumps(trade_info, indent=2)
                else:
                    return "No trade info found"
            except Exception as e:
                return "Error getting trade info: " + str(e) 
        
        def update_wallet(progress=gr.Progress()):
            res = ""
            try:
                progress(0, desc="Updating wallet info...")
                result = get_trader_info()
                # Parse JSON string to dict
                result_dict = json.loads(result)
                progress(1, desc="Wallet info updated")
                if "wallet_infos" in result_dict:
                    # latest one
                    wallet_info = result_dict["wallet_infos"]["infos"][-1]
                    res += f"**Wallet Info:**\n{wallet_info}\n"
                if "token_info" in result_dict:
                    token_info = result_dict["token_info"]["infos"]
                    res += f"**Token Info:**\n{token_info}\n"
                if "liquidity_infos" in result_dict:
                    liquidity_info = result_dict["liquidity_infos"]["infos"][-1]
                    res += f"**Liquidity Info:**\n{liquidity_info}\n"
                return res
            except Exception as e:
                return "Error getting wallet info: " + str(e)
        
        async def handle_query(query, progress=gr.Progress()):
            try:
                progress(0, desc="Processing query...")
                result = await process_query(query, full_agent)
                progress(1, desc="Query processed")
                return result
            except Exception as e:
                error_msg = f"Error processing query: {str(e)}"
                update_log(error_msg)
                return error_msg
        
        # reverse, latest log first
        # latest 16 logs
        def update_logs():
            logs = log_history[-16:][::-1] if log_history else []
            return "\n".join(logs)
        
        # bind events
        start_btn.click(start_trader_event, outputs=state_display)
        stop_btn.click(stop_trader_event, outputs=state_display)
        refresh_trade_btn.click(update_trade, outputs=history_display)
        query_btn.click(handle_query, inputs=query_input, outputs=query_output)
        refresh_logs_btn.click(update_logs, outputs=history_display)
        refresh_wallet_btn.click(update_wallet, outputs=history_display)

        # Initialize logs on load
        demo.load(update_wallet, None, history_display)

    return demo

async def trader_loop(full_agent):
    """Handle auto-query functionality."""
    while True:
        st = get_trader_state()
        update_log(f"State: {st}")
        #print(f"State: {st}")
        if st == "idle":
            await asyncio.sleep(60)
            continue

        try:
            # Get trader information
            infos = tc.get_info()
            json_infos = json.dumps(infos)
            
            # Process the query
            response = await full_agent.process_query(json_infos, use_history=False)
            
            # Log the response
            update_log(f"Response:\n {response}")
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            update_log(error_msg)
        finally:
            await asyncio.sleep(60)

async def main(address: str) -> None:
    """Main Entrypoint."""
    update_log("Starting trader agent...")
    
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

    # Create Gradio interface
    update_log("Creating Gradio interface")
    demo = create_gradio_interface(full_agent)
    demo.queue()

    # Run Gradio interface and auto-query loop in parallel
    update_log("Starting parallel tasks...")
    
    # Start both tasks
    query_task = asyncio.create_task(trader_loop(full_agent))
    
    try:
        # Launch Gradio in a separate thread
        update_log("Starting Gradio server in a separate thread...")
        demo.launch(server_port=7860, prevent_thread_lock=True)
        
        # Wait for the query task
        await query_task
    except (KeyboardInterrupt, Exception) as e:
        update_log(f"Error: {str(e)}")
    finally:
        # Cancel the query task
        update_log("Cancelling query task...")
        query_task.cancel()
        try:
            await query_task
        except asyncio.CancelledError:
            update_log("Query task cancelled successfully")
        
        # Clean up
        update_log("Cleaning up...")
        await full_agent.stop()
        update_log("Cleanup completed")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run an aip agent.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    parser.add_argument("--address", type=str, help="Address to connect to", default="13.212.116.103:8081")

    args = parser.parse_args()

    asyncio.run(main(args.address))
