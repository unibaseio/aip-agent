import argparse
import asyncio
import logging
import os
from typing import Annotated, List
import time

from membase.chain.chain import membase_chain, membase_id, membase_account

from membase.knowledge.chroma import ChromaKnowledgeBase
from membase.knowledge.document import Document

from autogen_core import (
    AgentId,
    try_get_known_serializers_for_type,
)
from aip_agent.grpc import GrpcWorkerAgentRuntime
from aip_agent.message.message import InteractionMessage, FunctionCall, FunctionExecutionResult


rag = ChromaKnowledgeBase(
    persist_directory="./chroma_config_db",
    collection_name="membase_config",
    membase_account=membase_account,
    auto_upload_to_hub=True,
)

# Store failed connection attempts
failed_attempts = {}
grpc_runtime = None

def search_server_config(
        query: Annotated[str, "The query to search for"],
        num_results: Annotated[int, "The number of results to return"] = 10,
        metadata_filter: Annotated[dict, "The metadata filter"] = None,
        content_filter: Annotated[str, "The content filter"] = None,
        ):
    if metadata_filter is None:
        metadata_filter = {}
    #metadata_filter["type"] = "tool"
    metadata_filter["state"] = "running"
    docs = rag.retrieve(query, top_k=num_results, metadata_filter=metadata_filter, content_filter=content_filter)

    # transform docs to list,with content,metadata, and doc_id
    return [{"server_name": doc.doc_id, "description": doc.content, "config": doc.metadata} for doc in docs]

def update_server_state(server_name: str, new_state: str):
    """Update server state in the knowledge base"""
    if rag.exists(server_name):
        # Get current document
        existing_doc = rag.collection.get(ids=[server_name])
        if len(existing_doc["ids"]) > 0:
            doc = existing_doc["documents"][0]
            # Update metadata state
            updated_metadata = doc.metadata.copy()
            updated_metadata["state"] = new_state
            
            updated_doc = Document(
                doc_id=doc.doc_id,
                content=doc.content,
                metadata=updated_metadata,
            )
            rag.update_documents(updated_doc)
            logging.info(f"Updated server {server_name} state to {new_state}")

async def check_server_connectivity(agent_id: str) -> bool:
    """Check if a server is reachable via gRPC connection"""
    try:
        # Create a temporary runtime for connectivity check
        global grpc_runtime
        if grpc_runtime is None:
            return True
        global failed_attempts
        try:
            logging.info(f"Checking connectivity for {agent_id}")
            await asyncio.wait_for(
                grpc_runtime.send_message(
                    InteractionMessage(
                        action="heartbeat",
                        content="ok",
                        source=membase_id,
                    ),
                    AgentId(agent_id, "default"),
                    sender=AgentId(membase_id, "default")
                ),
                timeout=10.0  # 10 seconds timeout
            )
            failed_attempts[agent_id] = 0
            return True
        except asyncio.TimeoutError:
            logging.warning(f"Heartbeat message timed out after 10 seconds for {agent_id}")
            failed_attempts[agent_id] = failed_attempts.get(agent_id, 0) + 1
            if failed_attempts[agent_id] >= 3:
                logging.error(f"Server {agent_id} marked as stopped after 3 failed attempts")
                return False
            return True
        
    except Exception as e:
        logging.warning(f"Connection failed: {e}")
        return False

async def periodic_connectivity_check(check_interval: int = 30):
    """Periodically check connectivity of running servers"""
    global failed_attempts
    
    while True:
        try:
            # Get all running servers
            running_servers = search_server_config("", num_results=1000)
            print(f"running_servers: {len(running_servers)}")

            for server_info in running_servers:
                print(server_info)
                server_name = server_info["server_name"]
                server_config = server_info["config"]
                state = server_config.get("state", "stopped")
                if state != "running":
                    continue
                
                # Check connectivity
                is_connected = await check_server_connectivity(server_name)
                
                if is_connected:
                    logging.info(f"Server {server_name} is healthy")
                else:
                    logging.warning(f"Server {server_name} connection failed. Attempts: {failed_attempts[server_name]}")
                    
                    # Mark as stopped after 3 failed attempts
                    if failed_attempts[server_name] >= 3:
                        update_server_state(server_name, "stopped")
                        logging.error(f"Server {server_name} marked as stopped after 3 failed attempts")
            
            # Wait before next check cycle
            await asyncio.sleep(check_interval)
            
        except Exception as e:
            logging.error(f"Error in connectivity check cycle: {e}")
            await asyncio.sleep(check_interval)

async def main(address: str, enable_periodic_check: bool = True, check_interval: int = 30) -> None:
    global grpc_runtime
    grpc_runtime = GrpcWorkerAgentRuntime(address)
    grpc_runtime.add_message_serializer(try_get_known_serializers_for_type(FunctionCall))
    grpc_runtime.add_message_serializer(try_get_known_serializers_for_type(FunctionExecutionResult))
    grpc_runtime.add_message_serializer(try_get_known_serializers_for_type(InteractionMessage))
    await grpc_runtime.start()

    # Start periodic connectivity check if enabled
    if enable_periodic_check:
        logging.info(f"Starting periodic connectivity check with {check_interval}s interval")
        asyncio.create_task(periodic_connectivity_check(check_interval))
    
    # Keep the main runtime running
    await grpc_runtime.stop_when_signal()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a config check for agent status.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    parser.add_argument("--address", type=str, help="Address to connect to", default="localhost:50060")
    parser.add_argument("--check-interval", type=int, help="Connectivity check interval in seconds", default=300)
    parser.add_argument("--disable-check", type=bool, help="Disable periodic connectivity check", default=False)
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.WARNING)
        logging.getLogger("autogen_core").setLevel(logging.DEBUG)
        file_name = "agent_" + membase_id + ".log"
        handler = logging.FileHandler(file_name)
        logging.getLogger("autogen_core").addHandler(handler)

    asyncio.run(main(args.address, not args.disable_check, args.check_interval))
