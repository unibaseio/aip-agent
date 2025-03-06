# Chess Game Example

An example with two chess player agents that executes its own tools to demonstrate tool use and reflection on tool use.

## Prerequisites

First, you need a shell with AutoGen core and required dependencies installed.

```bash
pip install "chess"
```

## Running the example

- MEMBASE_TASK_ID is same
- MEMBASE_ID is different with each other
- MEMBASE_ACCOUNT have balance in bnb testnet

```bash
# start game moderator, wait for palyers
# moderator register and create task onchain
# when game finish, moderator finish task, winner get the staking money
export MEMBASE_TASK_ID="<this task uuid>"
export MEMBASE_ID="<membase uuid>"
export MEMBASE_ACCOUNT="<membase account>"
export MEMBASE_SECRET_KEY="<membase secret key>"
python main.py --verbose

# start two player
# player register and staking to join this task
export MEMBASE_ID="<membase uuid>"
export MEMBASE_TASK_ID="<this task uuid>"
export MEMBASE_ACCOUNT="<membase account>"
export MEMBASE_SECRET_KEY="<membase secret key>"
python role.py --verbose --moderator=<moderator membase_id> --role=<black/white>

# start web browser in localhost:5000, show chess board
python app.py
```
