# AIP Agent

### What is AIP?

**AIP (Agent Interoperability Protocol)** is the first **Web3-native multi-agent communication standard**, built by Unibase.  
It enables agents to easily connect, share memory, and collaborate across platforms, with secure on-chain identity and access control.

> AIP = MCP + On-chain Identity + Decentralized Memory

---

# ✨ Key Features

- **Cross-Platform Agent Interoperability**  
Seamlessly connects agents and tools across different ecosystems via MCP and gRPC.

- **Decentralized Memory Layer**  
Agents store dialogues, knowledge, and configs in **Membase** for persistent, tamper-proof long-term memory.

- **On-Chain Identity & Access Control**  
Each agent has a blockchain-registered identity and programmable permissioning via smart contracts.

- **Direct LLM Invocation**  
Agents and tools are natively callable by LLMs, enabling complex autonomous workflows.

---

## 🧩 Protocol Comparison

| Feature                            | **MCP** (Anthropic)                     | **A2A** (Google)                      | **AIP** (Unibase) 🚀 |
|------------------------------------|----------------------------------------|--------------------------------------|----------------------|
| **Primary Focus**                  | LLM & tool/data integration            | Agent-to-agent communication         | Full agent interoperability + tool access |
| **Cross-Agent Communication**      | ❌                                     | ✅                                   | ✅                               |
| **Tool Integration**               | ✅                                     | ❌                                   | ✅                               |
| **Agent/Tool Discovery**           | ✅                                     | ❌                                   | ✅ (built-in discovery & registry) |
| **On-Chain Identity & Auth**       | ❌                                     | ❌                                   | ✅ (via ZK + blockchain)         |
| **Built-in Memory Support**        | ❌                                     | ❌                                   | ✅ (via Membase)                 |
| **Protocol Compatibility**         | MCP only                               | A2A only                            | ✅ (MCP + gRPC compatible)       |
| **Decentralization**               | ❌                                     | ❌                                   | ✅ (Web3-native)                 |

---

MCP and A2A each address part of the agent collaboration problem, but only AIP combines **memory, identity, interoperability, and secure access** into a single Web3-native standard.

# 🔥 Quick Start

## 1. Install AIP Agent SDK

```bash
pip install git+https://github.com/unibaseio/aip-agent.git
```

Or clone locally:

```bash
git clone https://github.com/unibaseio/aip-agent.git
cd aip-agent
uv venv
uv sync --dev --all-extras
```

## 2. Set Environment Variables

```bash
export MEMBASE_ID="<your unique agent ID>"
export MEMBASE_ACCOUNT="<your BNB testnet account>"
export MEMBASE_SECRET_KEY="<your secret key>"
```

Make sure your account has some BNB testnet tokens.

## 3. Run an Example Agent

```bash
cd examples/aip_agents
uv run grpc_full_agent_gradio.py
```

🎯 This starts a full-featured AIP agent with:

- Blockchain identity registration
- Memory Hub connection
- Live agent-to-agent or agent-to-tool interaction

---

# ⚙️ Architecture Overview

```
+-----------------+         +-----------------+         +-------------------+
|    LLM          | <-----> |    AIP Agent     | <-----> |     Tools          |
| (Local/Remote)  |         | (Full or Custom) |         | (MCP / gRPC )      |
+-----------------+         +-----------------+         +-------------------+
        |
        | Blockchain: Identity & Permission Management
        |
        v
    Membase: Decentralized Persistent Memory Layer
```

---

# 🛠️ Core Components

| Component        | Description                                              |
|------------------|-----------------------------------------------------------|
| **AIP Protocol**  | Agent communication standard (MCP + On-chain extensions) |
| **Membase**      | Decentralized memory storage for agent long-term memory   |
| **Unibase DA**   | High-performance data availability and storage layer      |

---

# 📚 Use Cases

- **Personalized DeFi Agent**  
  AI agents learn user preferences and help optimize trading and yield strategies.

- **Multi-Agent Gaming**  
  Agents collaborate and compete in real-time strategy or simulation games.

- **Knowledge Mining & Sharing**  
  Users contribute valuable information into decentralized knowledgebases for token incentives.

---

# 🚀 Advanced Examples

| Demo                  | Description                             |
|------------------------|-----------------------------------------|
| Chess Game             | Two AIP agents playing interactive chess |
| Automated Trade Agent  | Trading bots interacting on BNBChain    |
| Personal Social Agent  | Personalized agent based on X(Twitter) data |

Find demos in `/examples` folder.

---

# 🛡 Security and Best Practices

- All identities and permissions are verified on-chain.
- Data is encrypted and synchronized via **Membase**.
- Follow modular coding practices and secure environment management.

---

# 📥 Contributing

We welcome your contributions!

- Fork ➔ Feature branch ➔ PR
- Add documentation and tests if possible.

Join our developer community:  
[Discord] (Coming Soon) | [GitHub Issues](https://github.com/unibaseio/aip-agent/issues)

---

# 📜 License

MIT License. See [LICENSE](./LICENSE) file for details.

---

# 📞 Contact

- Website: [https://www.unibase.com](https://www.unibase.com)
- Support: <support@unibase.com>
- Telegram: [@unibase_ai](https://t.me/unibase_ai)
