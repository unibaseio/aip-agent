import time

import logging
logger = logging.getLogger(__name__)

from aip_chain.chain import membase_chain, membase_id

def buy_auth_onchain(memory_id):
    try:
        if not membase_chain.has_auth(memory_id, membase_id):
            logger.info(f"add agent: {membase_id} to hub memory: {memory_id}")
            membase_chain.buy(memory_id, membase_id)
    except Exception as e:
        logger.warning(f"buy auth fail: {e}")
        raise

def create_auth(timestamp):
    try:
        timestamp = int(timestamp)
    except ValueError:
        raise Exception("Invalid timestamp in create")
    verify_message = f"{timestamp}"
    return membase_chain.sign_message(verify_message)

def verify_auth(task_id, agent_id, timestamp, signature):

    logger.debug(f"auth time: {timestamp}, agent: {agent_id}, sign: {signature}")
   
    if not signature or not timestamp or not agent_id:
        raise Exception("Unauthorized")

    try:
        timestamp = int(timestamp)
    except ValueError:
        raise Exception("Invalid timestamp")
            
    current_time = int(time.time())
    if current_time - timestamp > 300: 
        logger.warning(f"{agent_id} has expired token")
        raise Exception("Token expired")

    if not membase_chain.has_auth(task_id, agent_id):
        logger.warning(f"{agent_id} is not auth on chain")
        raise Exception("No auth on chain")

    agent_address = membase_chain.get_agent(agent_id)
    verify_message = f"{timestamp}"
    if not membase_chain.valid_signature(verify_message, signature, agent_address):
        logger.warning(f"{agent_id} has invalid signature")
        raise Exception("Invalid signature")