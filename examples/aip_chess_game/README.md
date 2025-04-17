# Chess Game Example

This example demonstrates a chess game implementation with two AIP agents playing against each other, using tools to reason about game state and make moves. The game includes a moderator agent that manages the game flow and player registration.

## Features

- Two AI players (black and white) that can make strategic moves
- A moderator agent to manage game flow and player registration
- Real-time chess board visualization through a web interface
- On-chain task management and reward distribution
- Automatic move validation and game state tracking

## Prerequisites

+ Install uv package manager:
   - Follow the official installation guide: https://docs.astral.sh/uv/getting-started/installation/

## Configuration

Before running the game, you need to set up the following environment variables:

```bash
# For moderator and players
export MEMBASE_TASK_ID="<task_uuid>"  # Same for all participants
export MEMBASE_ID="<membase_uuid>"    # Unique for each participant
export MEMBASE_ACCOUNT="<membase_account>"
export MEMBASE_SECRET_KEY="<membase_secret_key>"
```

## Usage Instructions

### 1. Start the Moderator

The moderator agent will:
- Register on the blockchain
- Create a new task
- Wait for players to join
- Manage the game flow
- Distribute rewards at the end

```bash
# Start the moderator agent
uv run main.py
```

### 2. Start the Players

Each player needs to:
- Register on the blockchain
- Join the task
- Connect to the moderator
- Play their assigned color (black or white)

```bash
# Start a player 
uv run role.py  --moderator=<moderator_membase_id>

# Start another
uv run role.py --moderator=<moderator_membase_id> 

# Game start when two players finish registeration
```

### 3. View the Game

To view the chess board in real-time:
```bash
# Start the web interface
uv run app.py # Access at http://localhost:5000
```

The chess board will automatically update every 3 seconds.

## Game Flow

1. Moderator creates a task and waits for players
2. Players register and join the task
3. Game begins with white making the first move
4. Players take turns making moves
5. Game continues until:
   - Checkmate
   - Stalemate
   - Maximum rounds reached (100)
6. Winner receives the staked reward

## Notes

- The game supports standard chess rules
- Each player has a maximum of 100 moves
- The web interface shows the current board state
- All moves are validated for legality
- Game state is tracked and managed by the moderator
