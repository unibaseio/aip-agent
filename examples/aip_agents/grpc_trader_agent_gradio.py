import argparse
import asyncio
import json
import os
import gradio as gr
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go

from aip_agent.agents.full_agent import FullAgentWrapper
from aip_agent.agents.custom_agent import CallbackAgent

from membase.memory.message import Message

from membase.chain.chain import membase_id, membase_account, membase_secret
from membase.chain.util import BSC_TESTNET_SETTINGS
from membase.chain.trader import TraderClient

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
   - Ensure your trade amount is larger than the minimum requirement
   - For buy orders: amount must be > minimum buy amount
   - For sell orders: amount must be > minimum sell amount
4. Consider all market factors before making a decision
5. No need to ask for confirmation, just do it

Important Considerations:
- All transactions incur gas fees and trading fees
- Prioritize risk management over aggressive trading
- Maintain rational analysis, unaffected by market sentiment
- Always provide clear reasoning for your chosen action
"""

target_token_address = os.getenv('MEMBASE_TARGET_TOKEN', "0x2e6b3f12408d5441e56c3C20848A57fd53a78931")

tc = TraderClient(
    config=BSC_TESTNET_SETTINGS, 
    wallet_address=membase_account, 
    private_key=membase_secret, 
    token_address=target_token_address,
    membase_id=membase_id
)

llm_memory = tc.memory.get_memory()

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
    """Buy token with the given amount of native token and reason."""
    result = tc.buy(amount, reason)
    update_log(f"Buy token: amount={amount}, reason={reason}")
    update_log(f"Buy token result: {result}")
    return result

def sell_token(amount: int, reason: str):
    """Sell token with the given amount of token and reason."""
    result = tc.sell(amount, reason)
    update_log(f"Sell token: amount={amount}, reason={reason}")
    update_log(f"Sell token result: {result}")
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
        update_log(f"Query: \n{query}")
        msg = Message(name=membase_id, role="user", content=query)
        llm_memory.add(msg)

        response = await full_agent.process_query(query, use_history=False)
        
        update_log(f"Response: \n{response}")
        msg = Message(name=membase_id, role="assistant", content=response)
        llm_memory.add(msg)
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
                gr.Markdown("## Wallet Balance")
                wallet_chart = gr.Plot()    
            
                with gr.Row():
                    refresh_wallet_btn = gr.Button("Wallet Info")
                    refresh_trade_btn = gr.Button("Transactions")
                    refresh_memory_btn = gr.Button("LLM Memory")
                    refresh_logs_btn = gr.Button("Operation Logs")
                history_display = gr.Markdown(label="History Records", value="", min_height=100)
     
            # right log area
            with gr.Column(scale=1):
                gr.Markdown("## Background Trade Task")
                with gr.Row():
                    start_btn = gr.Button("Start")
                    stop_btn = gr.Button("Stop")
                state_display = gr.Textbox(label="Current State", value=get_trader_state())

                gr.Markdown("## Query")
                query_input = gr.Textbox(label="Enter your query", value="analyze my profit using trade info", lines=4)
                query_btn = gr.Button("Process Query")
                query_output = gr.Markdown(label="Query Result", value="", min_height=100)

        
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
        
        def update_state():
            return get_trader_state()
        
        def update_trade(progress=gr.Progress()):
            try:
                progress(0, desc="Updating trade info...")
                result = get_trader_info()
                result_dict = json.loads(result)
                progress(1, desc="Trade info updated")
                if "trade_infos" in result_dict:
                    # latest log first
                    trade_info = result_dict["trade_infos"]["infos"][::-1]
                    markdown_content = "## Trade History\n\n"
                    for trade in trade_info:
                        # Tx Hash is clickable link to `https://testnet.bscscan.com/tx/tx hash`
                        tx_hash = trade.get('tx_hash', 'N/A')
                        if tx_hash != 'N/A':
                            markdown_content += f"- **Tx Hash**: [{tx_hash}](https://testnet.bscscan.com/tx/{tx_hash})\n"
                        else:
                            markdown_content += f"- **Tx Hash**: N/A\n"
                        markdown_content += f"  - **Time**: {trade.get('timestamp', 'N/A')}\n"
                        markdown_content += f"  - **Type**: {trade.get('type', 'N/A')}\n"
                        markdown_content += f"  - **Gas Fee**: {trade.get('gas_fee', 'N/A')}\n"
                        markdown_content += f"  - **Price**: {trade.get('strike_price', 'N/A')}\n"
                        markdown_content += f"  - **Token Delta**: {trade.get('token_delta', 'N/A')}\n"
                        markdown_content += f"  - **Native Delta**: {trade.get('native_delta', 'N/A')}\n"
                        markdown_content += f"  - **Reason**: {trade.get('reason', 'N/A')}\n\n"
                    return markdown_content
                else:
                    return "## Trade History\n\nNo trade records found"
            except Exception as e:
                return f"## Error\n\nFailed to get trade info: {str(e)}"
        
        def update_wallet(progress=gr.Progress()):
            try:
                progress(0, desc="Updating wallet info...")
                result = get_trader_info()
                result_dict = json.loads(result)
                progress(1, desc="Wallet info updated")

                markdown_content = "## Wallet Information\n\n"
                if "wallet_infos" in result_dict:
                    wallet_info = result_dict["wallet_infos"]["infos"][-1]
                    markdown_content += f"### Wallet Status\n"
                    markdown_content += f"- **Balance**: {wallet_info.get('native_balance', 'N/A')}\n"
                    markdown_content += f"- **Token Balance**: {wallet_info.get('token_balance', 'N/A')}\n\n"
                    tv = wallet_info.get('total_value')
                    if tv is not None:
                        tv = float(tv) / 10**18
                        markdown_content += f"- **Total Balance**: {tv} BNB\n"
                
                if "token_info" in result_dict:
                    token_info = result_dict["token_info"]["infos"]
                    markdown_content += f"### Token Information\n"
                    markdown_content += f"- **Token Address**: {token_info.get('token_address', 'N/A')}\n"
                    markdown_content += f"- **Total Supply**: {token_info.get('token_total_supply', 'N/A')}\n"
                    markdown_content += f"- **Swap Fee Tier**: {token_info.get('swap_fee_tier', 'N/A')}\n\n"
                
                if "liquidity_infos" in result_dict:
                    liquidity_info = result_dict["liquidity_infos"]["infos"][-1]
                    markdown_content += f"### Liquidity Pool\n"
                    markdown_content += f"- **Token Reserve**: {liquidity_info.get('token_reserve', 'N/A')}\n"
                    markdown_content += f"- **BNB Reserve**: {liquidity_info.get('native_reserve', 'N/A')}\n"
                    markdown_content += f"- **Estimated Price**: {liquidity_info.get('token_price', 'N/A')} BNB\n"
                
                return markdown_content
            except Exception as e:
                return f"## Error\n\nFailed to get wallet info: {str(e)}"

        def update_wallet_chart():
            try:
                infos = tc.get_info(recent_n=64)
                
                fig = go.Figure()
                if "wallet_infos" in infos:
                    wallet_history = []
                    wallet_infos = infos["wallet_infos"]["infos"][1:]
                    for wallet_info in wallet_infos:
                        tv = wallet_info.get('total_value')
                        tb = wallet_info.get('token_balance')
                        if tv is not None and tb is not None:
                            tv = float(tv) / 10**18
                            tb = float(tb) / 10**18
                            wallet_history.append({
                                "timestamp": wallet_info.get('timestamp'),
                                "total_value": tv,
                                "token_balance": tb
                            })
                    
                    if len(wallet_history) > 1:
                        # Calculate ranges with padding
                        total_values = [h["total_value"] for h in wallet_history]
                        token_values = [h["token_balance"] for h in wallet_history]
                        
                        total_min, total_max = min(total_values), max(total_values)
                        token_min, token_max = min(token_values), max(token_values)
                        
                        # Add 10% padding to ranges
                        total_range = total_max - total_min
                        token_range = token_max - token_min
                        
                        total_min -= total_range * 0.30
                        if total_min < 0:
                            total_min = 0
                        total_max += total_range * 0.30
                        token_min -= token_range * 0.25
                        if token_min < 0:
                            token_min = 0
                        token_max += token_range * 0.25
                        
                        # Add total balance trace
                        fig.add_trace(go.Scatter(
                            x=[h["timestamp"] for h in wallet_history],
                            y=[h["total_value"] for h in wallet_history],
                            mode='lines',
                            name='Total Balance (BNB)',
                            line=dict(
                                color='#CBD5E0',  # Light gray color
                                width=2.5,
                                shape='spline',
                                smoothing=1.3,
                                dash='solid'
                            ),
                            yaxis='y'
                        ))

                        # Add token balance trace
                        fig.add_trace(go.Scatter(
                            x=[h["timestamp"] for h in wallet_history],
                            y=[h["token_balance"] for h in wallet_history],
                            mode='lines',
                            name='Token Balance',
                            line=dict(
                                color='#BEE3F8',  # Light blue color
                                width=2.5,
                                shape='spline',
                                smoothing=1.3,
                                dash='solid'
                            ),
                            yaxis='y2'
                        ))
                
                fig.update_layout(
                    yaxis_title='Total Balance (BNB)',
                    yaxis2=dict(
                        title='Token Balance',
                        overlaying='y',
                        side='right',
                        showgrid=False,
                        range=[token_min, token_max]
                    ),
                    yaxis=dict(
                        range=[total_min, total_max],
                        gridcolor='#e2e8f0',
                        showgrid=True
                    ),
                    height=400,
                    margin=dict(l=50, r=50, t=50, b=50),
                    showlegend=True,
                    legend=dict(
                        yanchor="bottom",
                        y=1.02,
                        xanchor="center",
                        x=0.5,
                        orientation="h"  # Horizontal layout
                    ),
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    xaxis=dict(
                        gridcolor='#e2e8f0',
                        showgrid=True
                    )
                )
                
                return fig
            except Exception as e:
                update_log(f"Error updating wallet chart: {str(e)}")
                return None
        
        async def handle_query(query, progress=gr.Progress()):
            try:
                # Set estimated time to 20 seconds
                progress(0, desc="Processing query...", total=20)
                
                # Simulate progress updates
                for i in range(19):
                    await asyncio.sleep(1)
                    progress((i + 1)/20, desc=f"Processing query...")
                    
                result = await process_query(query, full_agent)
                progress(1, desc="Query processed successfully")
                return result
            except Exception as e:
                error_msg = f"Error processing query: {str(e)}"
                update_log(error_msg)
                return error_msg
        
        # reverse, latest log first
        # latest 64 logs
        def update_logs():
            logs = log_history[-64:][::-1] if log_history else []
            markdown_content = "## Operation Logs\n\n"
            for log in logs:
                markdown_content += f"- {log}\n"
            return markdown_content
        
        def update_memory():
            latest_memory = llm_memory.get(recent_n=16)
            latest_memory = latest_memory[::-1]
            markdown_content = "## LLM Conversation History\n\n"
            for m in latest_memory:
                markdown_content += f"### {m.timestamp} {m.role}\n"
                markdown_content += f"{m.content}\n\n"
            return markdown_content
        

        # create timer
        timer = gr.Timer(20, active=True) 
        timer.tick(update_logs, outputs=history_display)
        
        # create wallet chart timer
        wallet_chart_timer = gr.Timer(60, active=True)
        wallet_chart_timer.tick(update_wallet_chart, outputs=wallet_chart)
        
        # bind event
        start_btn.click(start_trader_event, outputs=state_display)
        stop_btn.click(stop_trader_event, outputs=state_display)
        refresh_trade_btn.click(update_trade, outputs=history_display)
        query_btn.click(handle_query, inputs=query_input, outputs=query_output, show_progress=True)
        refresh_memory_btn.click(update_memory, outputs=history_display)
        refresh_wallet_btn.click(update_wallet, outputs=history_display)
        refresh_logs_btn.click(update_logs, outputs=history_display)
        
        # Initialize logs on load and update state
        demo.load(update_logs, None, history_display)
        demo.load(update_state, None, state_display)
        demo.load(update_wallet_chart, None, wallet_chart)

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
            #update_log(f"Response:\n {response}")
            msg = Message(name=membase_id, role="assistant", content=response)
            llm_memory.add(msg)
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            update_log(error_msg)
        finally:
            await asyncio.sleep(60)

async def main(address: str) -> None:
    """Main Entrypoint."""
    update_log("Starting trader agent...")

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
