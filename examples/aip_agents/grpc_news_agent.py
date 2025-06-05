import argparse
import asyncio
import logging
import signal

import requests
import os
from dotenv import load_dotenv

from aip_agent.agents.full_agent import FullAgentWrapper
from aip_agent.agents.custom_agent import CallbackAgent

from membase.chain.chain import membase_id

load_dotenv()
API_KEY = os.getenv("CRYPTOPANIC_API_KEY")

def get_crypto_news(kind: str = "news", num_pages: int = 1) -> str:
  news = fetch_crypto_news(kind, num_pages)
  readable = concatenate_news(news)
  return readable

def fetch_crypto_news_page(kind: str = "news", page: int = 1): 
  try:
    url = "https://cryptopanic.com/api/v1/posts/"
    params = {
      "auth_token": API_KEY,
      "kind": "news",  # news, analysis, videos
      "regions": "en",  
      "page": page      
    }
    response = requests.get(url, params=params)
    return response.json().get("results", [])
  except:
    return []
        
def fetch_crypto_news(kind: str = "news", num_pages: int = 10):
  all_news = []
  for page in range(1, num_pages + 1):
    print(f"Fetching page {page}...")
    news_items = fetch_crypto_news_page(kind, page)
    if not news_items:
      print(f"No more news found on page {page}. Stopping.")
      break
    all_news.extend(news_items)
  return all_news        

def concatenate_news(news_items):
  concatenated_text = ""
  for idx, news in enumerate(news_items):  # 拼接全部新闻
    title = news.get("title", "No Title")
    concatenated_text += f"- {title}\n"
       
  return concatenated_text.strip()

async def main(address: str) -> None:
    """Main Entrypoint."""

    # Create shutdown event
    shutdown_event = asyncio.Event()
    
    def signal_handler(signum, frame):
        logging.info(f"Received signal {signum}, initiating shutdown...")
        shutdown_event.set()
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    description = """
    You are a specialized crypto news assistant that can fetch and analyze the latest cryptocurrency news.
    
    You have access to real-time crypto news from CryptoPanic API and can:
    - Fetch the latest crypto news and market updates
    - Provide summaries of recent developments in the cryptocurrency space
    - Answer questions about specific crypto projects or market trends
    - Help users stay informed about important events in the crypto ecosystem
    
    Use the get_crypto_news function to retrieve current news when users ask about crypto market updates.
    """

    full_agent = FullAgentWrapper(
        agent_cls=CallbackAgent,
        name=membase_id,
        description=description,
        host_address=address,
        functions=[get_crypto_news],
    )
    await full_agent.initialize()

    tools = await full_agent._mcp_agent.list_tools()
    print(f"tools: {tools}")

    logging.info("Agent started successfully. Press Ctrl+C to stop.")
    
    try:
        # Wait for shutdown signal with short polling interval
        while not shutdown_event.is_set():
            try:
                await asyncio.wait_for(shutdown_event.wait(), timeout=0.1)
            except asyncio.TimeoutError:
                continue
    except Exception as e:
        logging.error(f"Unexpected error occurred: {e}")
    finally:
        try:
            logging.info("Stopping agent...")
            await full_agent.stop()
            logging.info("Agent stopped successfully.")
        except Exception as e:
            logging.error(f"Error during shutdown: {e}")
        finally:
            logging.info("Cleanup completed.")
            

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run an aip agent for crypto news.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    parser.add_argument("--address", type=str, help="Address to connect to", default="54.169.29.193:8081")

    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
        logging.getLogger("aip_agent").setLevel(logging.DEBUG)
        logging.getLogger("autogen").setLevel(logging.DEBUG)

    asyncio.run(main(args.address))
