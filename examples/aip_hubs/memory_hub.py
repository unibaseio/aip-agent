
import argparse
import asyncio
import logging
import os
from typing import Annotated, List

from membase.chain.chain import membase_chain, membase_id, membase_account
from membase.memory.buffered_memory import BufferedMemory
from membase.memory.message import Message
from membase.knowledge.chroma import ChromaKnowledgeBase
from membase.knowledge.document import Document

from autogen_core.tools import FunctionTool, Tool

from aip_agent.agents.tool_agent import ToolAgentWrapper

bm = BufferedMemory(
    membase_account=membase_account,
    auto_upload_to_hub=True,
    )

rag = ChromaKnowledgeBase(
    collection_name="default",
    anonymized_telemetry=False,
)

def add_memory(
        memory_id: Annotated[str, "The memory id"],
        content: Annotated[str, "The content of the memory"],
        metadata: Annotated[dict, "The metadata of the memory"]
        ):
    
    msg = Message(
        name=memory_id,
        content=content,
        metadata=metadata,
        role="user",
    )

    bm.add(msg)

    doc = Document(
        doc_id=memory_id,
        content=content,
        metadata=metadata,
    )

    if rag.exists(memory_id):
        rag.update_documents(doc)
    else:
        rag.add_documents(doc)

def read_memory(
        memory_id: Annotated[str, "The memory id to read"]
        ):
    def name_filter(msg):
        return msg.name == memory_id
    return bm.get(name_filter)

def search_server_config(
        query: Annotated[str, "The query to search for"],
        num_results: Annotated[int, "The number of results to return"] = 5,
        metadata_filter: Annotated[dict, "The metadata filter"] = None,
        content_filter: Annotated[str, "The content filter"] = None,
        ):
    if metadata_filter is None:
        metadata_filter = {}
    metadata_filter["type"] = "tool"
    docs = rag.retrieve(query, top_k=num_results, metadata_filter=metadata_filter, content_filter=content_filter)

    # transform docs to list,with content,metadata, and doc_id
    return [{"server_name": doc.doc_id, "content": doc.content, "metadata": doc.metadata} for doc in docs]

def search_similar(
        query: Annotated[str, "The query to search for"],
        num_results: Annotated[int, "The number of results to return"] = 5,
        metadata_filter: Annotated[dict, "The metadata filter"] = None,
        content_filter: Annotated[str, "The content filter"] = None,
        ):
    docs = rag.retrieve(query, top_k=num_results, metadata_filter=metadata_filter, content_filter=content_filter)

    # transform docs to list,with content,metadata, and doc_id
    return [{"name": doc.doc_id, "content": doc.content, "metadata": doc.metadata} for doc in docs]

async def main(address: str) -> None:
    local_tools: List[Tool] = [
        FunctionTool(
            add_memory,
            name="add_memory",
            description="Add a memory to the memory hub.",
        ),
        FunctionTool(
            read_memory,
            name="read_memory",
            description="Read a memory from the memory hub.",
        ),
        FunctionTool(
            search_similar,
            name="search_similar",
            description="Search for agent/tool servers or memories similar to a query.",
        ),
        FunctionTool(
            search_server_config,
            name="search_server_config",
            description="Search for agent/tool server configuration (server_name, transport, type, tools) similar to a query.",
        ),
    ]

    desc = "This is a membase memory hub, which can manage your agent or tool configuration and memories. \n"
    desc += "You can also manage your agent or tool server configuration and memories. \n"
    desc += "You can register your agent or tool in the hub. \n"
    desc += "You can find agents or tools you want to use. \n"
    desc += "You can add, read, and search for memories. \n"
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
