import argparse
import asyncio
from datetime import datetime
import json
import logging
import os
import gradio as gr

from aip_agent.agents.full_agent import FullAgentWrapper
from aip_agent.agents.custom_agent import CallbackAgent

from membase.chain.chain import membase_id

from core.rag import switch_user, search_similar_posts
from core.post import generate_system_prompt

from core.retrieve import retrieve_tweets
from core.generate import generate_profile
from core.save import save_tweets

default_x_name = ""
description = ""

log_history = []

def update_log(message):
    """Update log and output to both console and file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] {message}"
    log_history.append(log_message)
    print(log_message)

def build_users(x_user: str) -> str:
    """Build user profile and update user status"""
    
    # check if profile already exists
    if os.path.exists(f"outputs/{x_user}_profile_final.json"):
        print(f"Profile for {x_user} already exists")
        return generate_system_prompt(x_user)
    
    # check if tweets need to be retrieved
    if not os.path.exists(f"outputs/{x_user}.json"):
        print(f"Retrieving tweets for {x_user}")
        update_log(f"Retrieving tweets for {x_user}")
        retrieve_tweets(x_user)
    
    # generate profile if tweets exist
    if os.path.exists(f"outputs/{x_user}.json"):
        update_log(f"Generating profile for {x_user}")
        generate_profile(x_user)
    
    # after profile is generated, update user status
    if os.path.exists(f"outputs/{x_user}_profile_final.json"):
        update_log(f"Finished generating profile for {x_user}")
        return generate_system_prompt(x_user)

async def process_query(query: str, full_agent):
    """Process a query and update logs."""
    global description
    try:
        update_log(f"Query: \n{query}")
        #print(f"description: {description}")
        response = await full_agent.process_query(query, use_history=False, system_prompt=description)
        update_log(f"Response: \n{response}")
        return response
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        update_log(error_msg)
        return error_msg

def create_gradio_interface(full_agent):
    """Create Gradio interface."""
    
    with gr.Blocks() as demo:
        gr.Markdown("# Personal Agent: " + membase_id)
        
        with gr.Row():
            # left area
            with gr.Column(scale=1):
                gr.Markdown("## Personal Character")
                gr.Markdown(label="Personal Character", value=description, line_breaks=True)
            
            # right area
            with gr.Column(scale=1):
                gr.Markdown("## Query")
                query_input = gr.Textbox(label="Enter your query", value="Tesla is going to build second factory in Shanghai", lines=4)
                query_btn = gr.Button("Process Query")
                # break line in query output
                query_output = gr.Markdown(label="Query Result", value="", min_height=100, line_breaks=True)

                refresh_logs_btn = gr.Button("Operation Logs")
                history_display = gr.Markdown(label="Operation Logs", value="", min_height=100, line_breaks=True)

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

        # create timer for logs
        timer = gr.Timer(20, active=True) 
        timer.tick(update_logs, outputs=history_display)
        
        # bind event
        query_btn.click(handle_query, inputs=query_input, outputs=query_output, show_progress=True)

        refresh_logs_btn.click(update_logs, outputs=history_display)
        
        # Initialize logs on load and update state
        demo.load(update_logs, None, history_display)

    return demo

async def personal_loop():
    """Handle auto-query functionality."""
    while True:
        await asyncio.sleep(60)
        continue

async def main(address: str, x_account: str) -> None:
    """Main Entrypoint."""
    update_log("Starting personal agent...")

    global description, default_x_name
    if x_account.startswith("@"):
        x_account = x_account[1:]
    default_x_name = x_account
    description = build_users(x_account)

    full_agent = FullAgentWrapper(
        agent_cls=CallbackAgent,
        name=membase_id,
        description=description,
        host_address=address,
        functions=[search_similar_posts]
    )
    await full_agent.initialize()

    # Create Gradio interface
    update_log("Creating Gradio interface")
    demo = create_gradio_interface(full_agent)
    demo.queue()

    # Run Gradio interface and auto-query loop in parallel
    update_log("Starting parallel tasks...")
    
    # Start both tasks
    query_task = asyncio.create_task(personal_loop())
    
    try:
        # Launch Gradio in a separate thread
        update_log("Starting Gradio server in a separate thread...")
        demo.launch(prevent_thread_lock=True, share=False)
        
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
    parser = argparse.ArgumentParser(description="Run an aip personal agent.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    parser.add_argument("--address", type=str, help="Address to connect to", default="13.212.116.103:8081")
    parser.add_argument("--x_account", type=str, help="Your X account name", default="elonmusk")

    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
        logging.getLogger("aip_agent").setLevel(logging.DEBUG)
        logging.getLogger("autogen").setLevel(logging.DEBUG)


    asyncio.run(main(args.address, args.x_account))