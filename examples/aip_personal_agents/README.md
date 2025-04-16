# AIP Personal Agents

AIP Personal Agents is a personal intelligent agent system that generates personalized agents based on Twitter/X users' historical records. The system analyzes users' tweets to summarize their characteristics and generates content that aligns with their style. Users only need to provide a Twitter username to get started.

## Features

- Support for managing and switching between multiple X accounts
- Automatic tweet fetching and user profile generation
- Real-time query processing
- Operation log recording
- User-friendly web interface

## Installation & Configuration

+ Install uv package manager:
   - Follow the official installation guide: https://docs.astral.sh/uv/getting-started/installation/

+ Configure environment variables:

```bash
# API Keys and Account Information
MEMBASE_ACCOUNT="your_membase_account_address"
MEMBASE_SECRET_KEY="your_membase_private_key"
MEMBASE_ID="your_agent_id"
APIFY_API_TOKEN="your_apify_token"
OPENAI_API_KEY="your_openai_api_key"

# GRADIO Server configuration
GRADIO_SERVER_NAME=127.0.0.1
GRADIO_SERVER_PORT=7860
```

Note: Replace the placeholder values with your actual API keys and account information.

## Usage

### Single User Mode (personal_agent_gradio.py)

The single user mode is designed for focusing on one specific Twitter/X account. It provides a streamlined interface for interacting with a single agent.

#### Features:

- Dedicated interface for one Twitter/X account
- Simplified user experience
- Faster response times
- Ideal for focused analysis of a single account

#### Parameters

- `--verbose`: Enable verbose logging
- `--address`: GRPC server address, default is "13.212.116.103:8081"
- `--x_account`: Your X account name

To start:
```bash
uv run personal_agent_gradio.py --x_account <twitter_username>
```

### Multi User Mode (personal_agent_multiple_gradio.py)

The multi user mode allows managing and switching between multiple Twitter/X accounts. It provides a comprehensive interface for handling multiple agents simultaneously.

#### Features:
- Manage multiple Twitter/X accounts
- Dynamic account switching
- Batch processing capabilities
- Centralized log management
- Real-time account status updates

#### Parameters:

- `--verbose`: Enable verbose logging
- `--address`: GRPC server address, default is "13.212.116.103:8081"

To start:
```bash
uv run personal_agent_multiple_gradio.py
```



### Interface Operations

1. **Adding New Account** (Multi-user mode only)
   - Enter X account name in the left panel
   - Click "Submit" button
   - System will automatically start fetching tweets and generating profile

2. **Switching Accounts** (Multi-user mode only)
   - Select account from dropdown menu
   - System will automatically update personal character description

3. **Query Processing**
   - Enter query in the right panel
   - Click "Process Query" button
   - System will return query results

4. **Viewing Logs**
   - Click "Operation Logs" button to view operation logs
   - Logs are automatically updated, showing recent operations

## Notes

- First-time addition of new accounts requires time for tweet fetching and profile generation
- Ensure stable network connection for proper tweet data retrieval
- Regular log checking is recommended to ensure system normal operation

## File Structure

- `personal_agent_gradio.py`: Single-user mode implementation
- `personal_agent_multiple_gradio.py`: Multi-user mode implementation
- `outputs/`: Directory for storing user tweets and profiles
