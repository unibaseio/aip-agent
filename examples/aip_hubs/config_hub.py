
import argparse
import asyncio
import logging
import os
from typing import Annotated, List

from membase.chain.chain import membase_chain, membase_id, membase_account

from membase.knowledge.chroma import ChromaKnowledgeBase
from membase.knowledge.document import Document

from autogen_core.tools import FunctionTool, Tool

from aip_agent.agents.tool_agent import ToolAgentWrapper


rag = ChromaKnowledgeBase(
    persist_directory="./chroma_config_db",
    collection_name="default",
    anonymized_telemetry=False,
    membase_account=membase_account,
    auto_upload_to_hub=True,
)

def register_server(
        name: Annotated[str, "The agent/tool server name"],
        description: Annotated[str, "The agent/tool server description"],
        config: Annotated[dict, "The agent/tool server config"],
        ):


    doc = Document(
        doc_id=name,
        content=description,
        metadata=config,
    )

    if rag.exists(name):
        rag.update_documents(doc)
    else:
        rag.add_documents(doc)

def search_server_config(
        query: Annotated[str, "The query to search for"],
        num_results: Annotated[int, "The number of results to return"] = 5,
        metadata_filter: Annotated[dict, "The metadata filter"] = None,
        content_filter: Annotated[str, "The content filter"] = None,
        ):
    if metadata_filter is None:
        metadata_filter = {}
    metadata_filter["type"] = "tool"
    metadata_filter["state"] = "running"
    docs = rag.retrieve(query, top_k=num_results, metadata_filter=metadata_filter, content_filter=content_filter)

    # transform docs to list,with content,metadata, and doc_id
    return [{"server_name": doc.doc_id, "description": doc.content, "config": doc.metadata} for doc in docs]

async def main(address: str) -> None:
    local_tools: List[Tool] = [
        FunctionTool(
            register_server,
            name="register_server",
            description="Register a agent/tool server to the config hub.",
        ),
        FunctionTool(
            search_server_config,
            name="search_server_config",
            description="Search for agent/tool servers similar to a query.",
        ),
    ]

    desc = "This is a membase config hub, which can manage your agent or tool configuration. \n"
    desc += "You can register your agent or tool in the hub. \n"
    desc += "You can find agents or tools you want to use. \n"
    tool_agent = ToolAgentWrapper(
        name=os.getenv("MEMBASE_ID"),
        tools=local_tools,
        host_address=address,
        description=desc
    )
    await tool_agent.initialize()
    await tool_agent.stop_when_signal()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a chess game between two agents.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    parser.add_argument("--address", type=str, help="Address to connect to", default="localhost:50060")
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.WARNING)
        logging.getLogger("autogen_core").setLevel(logging.DEBUG)
        file_name = "agent_" + membase_id + ".log"
        handler = logging.FileHandler(file_name)
        logging.getLogger("autogen_core").addHandler(handler)

    asyncio.run(main(args.address))
