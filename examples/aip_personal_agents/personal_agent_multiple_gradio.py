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

from core.save import save_tweets
from core.build import is_user_finished, load_usernames, build_user

default_x_name = "elonmusk"
description = generate_system_prompt(default_x_name)

log_history = []
users = []

users_candidates = []

def update_log(message):
    """Update log and output to both console and file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] {message}"
    log_history.append(log_message)
    print(log_message)

def add_x_user(x_user: str):
    """Add a new X user to candidates list"""

    # check x_user is a valid x account
    if x_user.startswith("@"):
        x_user = x_user[1:]

    global users, users_candidates

    # check if the user already exists in users or candidates
    if x_user in users:
        return f"X account {x_user} already exists in users list"
    
    if x_user in users_candidates:
        return f"X account {x_user} is already in processing queue"

    # add to candidates list
    users_candidates.append(x_user)
    return f"X account: {x_user} is added into processing queue, wait for building profile"

def build_users(x_user: str):
    """Build user profile and update user status"""
    global users, users_candidates

    is_finished = is_user_finished(x_user)
    if is_finished:
        if x_user in users_candidates:
            users_candidates.remove(x_user)
        if x_user not in users:
            users.append(x_user)
        return

    print(f"Building profile for {x_user}")
    try:
        build_user(x_user)
    except Exception as e:
        update_log(f"Error building profile for {x_user}: {str(e)}")
        return
    finally:
        if x_user in users_candidates:
            users_candidates.remove(x_user)
        if x_user not in users:
            users.append(x_user)

def list_users() -> list[str]:
    """List all users from profile files in the outputs directory and update user status.
    
    Returns:
        list[str]: A list of user names extracted from profile files.
    """
    global users, users_candidates
    try:    
        finished_users, unfinished_users = load_usernames()
        for user_name in finished_users:
            if user_name in users_candidates:
                users_candidates.remove(user_name)
        users = finished_users
        return users
    except Exception as e:
        logging.error(f"Error listing users: {str(e)}")
        return []

def switch_x_user(x_user: str) -> str:
    """Switch to a different X user"""
    global current_x_user, description
    current_x_user = x_user
    switch_user(x_user)
    description = generate_system_prompt(x_user)
    update_log(f"Switched to X account {x_user}")
    return description

async def process_query(query: str, full_agent):
    """Process a query and update logs."""
    global description
    try:
        update_log(f"Query: \n{query}")
        print(f"description: {description}")
        response = await full_agent.process_query(query, use_history=False, system_prompt=description)
        update_log(f"Response: \n{response}")
        return response
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        update_log(error_msg)
        return error_msg

def submit_new_account(x_user: str) -> str:
    """Submit a new X account"""
    if not x_user:
        return "Please enter a valid X account name"
    
    res = add_x_user(x_user)
    update_log(res)
    return res

def create_gradio_interface(full_agent):
    """Create Gradio interface."""
    
    with gr.Blocks() as demo:
        gr.Markdown("# Personal Agent: " + membase_id)
        
        with gr.Row():
            # left area
            with gr.Column(scale=1):
                # add a textbox to add x user, submit 
                add_x_user_input = gr.Textbox(label="Add X Account", value="")
                add_x_user_btn = gr.Button("Submit")
                add_x_user_output = gr.Textbox(label="Status", value="", interactive=False)
                add_x_user_btn.click(
                    fn=submit_new_account,
                    inputs=add_x_user_input,
                    outputs=add_x_user_output
                )

                gr.Markdown("## X Account")
                # update personal character when x account is changed
                x_user_display = gr.Dropdown(label="X Account", choices=users, value=default_x_name)
                gr.Markdown("## Personal Character")
                system_prompt_display = gr.Markdown(label="Personal Character", value=description, line_breaks=True)   
                
                def update_dropdown_choices():
                    list_users()  # Update the global users list
                    return gr.update(choices=users)
                
                x_user_display.change(switch_x_user, inputs=x_user_display, outputs=system_prompt_display)
            
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
        
        # create timer for dropdown update
        dropdown_timer = gr.Timer(10, active=True)
        dropdown_timer.tick(update_dropdown_choices, outputs=x_user_display)
        
        # bind event
        query_btn.click(handle_query, inputs=query_input, outputs=query_output, show_progress=True)

        refresh_logs_btn.click(update_logs, outputs=history_display)
        
        # Initialize logs on load and update state
        demo.load(update_logs, None, history_display)

    return demo

async def personal_loop():
    """Handle auto-query functionality."""
    while True:
        list_users()

        # build first user
        if len(users_candidates) > 0:
            # build first user
            user_candidate = users_candidates[0]
            update_log(f"Building profile for {user_candidate}")
            build_users(user_candidate)
            list_users()
            update_log(f"Finished building profile for {user_candidate}")
            update_log(f"Saving tweets in chroma db for {user_candidate}")
            try:
                save_tweets(user_candidate)
                update_log(f"Finished saving tweets in chroma db for {user_candidate}")
            except Exception as e:
                update_log(f"Error saving tweets in chroma db for {user_candidate}: {str(e)}")

        await asyncio.sleep(60)
        continue

async def main(address: str) -> None:
    """Main Entrypoint."""
    update_log("Starting personal agent...")

    list_users()

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
    parser = argparse.ArgumentParser(description="Run an aip agent.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    parser.add_argument("--address", type=str, help="GRPC server address", default="13.212.116.103:8081")

    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
        logging.getLogger("aip_agent").setLevel(logging.DEBUG)
        logging.getLogger("autogen").setLevel(logging.DEBUG)

    asyncio.run(main(args.address))