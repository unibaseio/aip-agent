import asyncio
    
from aip_agent.client import AIPClient
from aip_chain.chain import membase_chain, membase_account, membase_id
from aip_agent.agent import Configuration, LLMClient, ChatSession

async def main():
    if len(sys.argv) < 2:
        print("Usage: uv run client.py <URLs of SSE MCP server (i.e. http://localhost:8080/sse)>")
        sys.exit(1)

    membase_chain.register(membase_id)
    print(f"start agent with account: {membase_account} and id: {membase_id}")

    server_url = sys.argv[1]
    tserver_url = sys.argv[2]

    """Initialize and run the chat session."""
    config = Configuration()
    servers = [AIPClient("chroma", server_url), AIPClient("twitter", tserver_url)]
    llm_client = LLMClient(config.llm_api_key)
    chat_session = ChatSession(servers, llm_client)
    await chat_session.start()    

if __name__ == "__main__":
    import sys
    asyncio.run(main())