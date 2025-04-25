import random
import time
import uuid
from membase.chain.util import BSC_MAINNET_SETTINGS
from membase.chain.trader import TraderClient
from membase.storage.hub import hub_client
from membase.memory.buffered_memory import serialize
from membase.memory.message import Message
import names

# Generate random ethereum address
def generate_random_eth_address():
    # Generate 40 random hex characters
    hex_chars = '0123456789abcdef'
    address = ''.join(random.choice(hex_chars) for _ in range(40))
    return f"0x{address}"

# random wallet address
wallet_private_key = "abcd"


#https://pancakeswap.finance/info/v3/tokens
eth = "0x2170Ed0880ac9A755fd29B2688956BD959F933F8"
btcb = "0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c"
hyper = "0xC9d23ED2ADB0f551369946BD377f8644cE1ca5c4"
ept = "0x3Dc8e2d80b6215a1BCcAe4d38715C3520581E77c"
cake = "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82"
sol = "0x570A5D26f7765Ecb712C0924E4De545B89fD43dF"
bro = "0x12b4356c65340fb02cdff01293f95febb1512f3b"
bank = "0x3aee7602b612de36088f3ffed8c8f10e86ebf2bf"
xrp ="0x1d2f0da169ceb9fc7b3144628db156f3f6c60dbe"
banana = "0x3d4f0513e8a29669b960f9dbca61861548a9a760"


tokens = {eth,btcb, hyper, ept, cake, sol, bro, bank, xrp}

bps = []

def test_upload():
    wallet_address = generate_random_eth_address()
    for token_address in tokens:
        membase_id = "trader_" + names.get_first_name() + "_" + names.get_last_name()
        print(f"wallet_address: {wallet_address}, membase_id: {membase_id}")
        bp = TraderClient(BSC_MAINNET_SETTINGS, wallet_address, wallet_private_key, token_address, membase_id)
        bp.start_monitoring(7)
        bps.append(bp)
        time.sleep(2)

    while True:
        for bp in bps:  
            try:
                liquidity_infos = bp.liquidity_memory.get(recent_n=0)
                new_wallet_address = generate_random_eth_address()
                new_membase_id = "agent_trader_" + names.get_first_name() + "_" + str(uuid.uuid4())[:8]
                print(f"new_wallet_address: {new_wallet_address}, new_membase_id: {new_membase_id}")
                conversation_id = str(uuid.uuid4())
                i = 0
                for info in liquidity_infos:
                    msg = Message(new_membase_id, info.content, role="user")
                    msg_serialized = serialize(msg)
                    memory_id = conversation_id + "_" + str(i)
                    hub_client.upload_hub(new_wallet_address, memory_id, msg_serialized)
                    i += 1
            except Exception as e:
                print(e)
        time.sleep(60)


if __name__ == "__main__":
    test_upload()