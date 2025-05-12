# Personal API Documentation

## Run

```bash
# start fastapi
uv run -m core.fastapi --port=5001
```

## Environment Variables

- `GRPC_SERVER_URL`: gRPC server URL (default: "13.212.116.103:8081")
- `BEARER_TOKEN`: Authentication token (default: "unibase_personal_agent")

## Basic Information

- Base URL: `http://localhost:5001`
- All responses include a `success` field indicating request status
- All error responses include an `error` field with error description
- Authentication: All endpoints require Bearer token authentication
  - Add `Authorization: Bearer <token>` header to all requests
  - Default token: "unibase_personal_agent"
  - Can be configured via `BEARER_TOKEN` environment variable or `--bearer-token` argument
- Username is known as twitter handle
- All POST requests must use `application/json` format
- Username length cannot exceed 15 characters (Twitter handle limit)

## Response Format

All API responses follow a standard format:

```json
{
  "success": true|false,
  "data": <response_data>|"error_message"
}
```

- `success`: Boolean indicating if the request was successful
- `data`: Response data for successful requests, error message for failed requests

## Error Handling

The API uses standard HTTP status codes:

- 400: Bad Request (Invalid JSON format, missing required fields, username too long)
- 401: Unauthorized (Missing Authorization header)
- 403: Forbidden (Invalid bearer token)
- 404: Not Found (User/profile not found)
- 415: Unsupported Media Type (Content-Type must be application/json)
- 500: Internal Server Error

## API Endpoints

### 1. List All User Information

- **Description**: Get a list of all available users with their complete information
- **Endpoint**: `/api/list_info`
- **Method**: GET
- **Headers**: 
  - `Authorization: Bearer <token>`
- **Parameters**:
  - `sort_by`: Optional sorting field (default: "score")
    - `name`: Sort by username
    - `score`: Sort by total_score
  - `order`: Optional sort order (default: "desc")
    - `asc`: Ascending order
    - `desc`: Descending order
- **Response Example**:

```json
{
  "success": true,
  "data": [
    {
      "username": "user1",
      "summary": {
        // User summary details
        "detailed_analysis": {},
        "personal_brief": "", // 1-2 sentences
        "long_description": "", // 3-5 sentences
        "personal_tags": {
          "keywords": [
            "#Bitcoin",
            "Strategic Reserve",
            "BTC Yield",
          ]
        }
      },
      "xinfo": {
        // Twitter information details
      },
      "scores": {
        "total_score": 67,
        "engagement_score": 22,
        "influence_score": 23,
        "project_score": 0,
        "quality_score": 22,
        "authenticity_factor": 1,
        "detail": {}
      }
    }
  ]
}
```

- **Error Cases**:
  - If invalid sort_by parameter: 400 error with "Invalid sort_by parameter. Must be 'name' or 'score'"
  - If server error occurs: 500 error with error message

### 2. Get Complete User Info

- **Description**: Get complete information of username including profile, summary and xinfo
- **Endpoint**: `/api/get_info`
- **Method**: GET
- **Headers**: 
  - `Authorization: Bearer <token>`
- **Parameters**:
  - `username`: Username (required)
- **Response Example**:

```json
{
  "success": true,
  "data": {
    "username": "user1",
    "xinfo": {
      // Twitter information details
    },
    "summary": {
      "detailed_analysis": {},
      "personal_brief": "",
      "long_description": "",
      "personal_tags": {
        "keywords": []
      }
    },
    "scores": {
      "total_score": 100,
    }
  }
}
```

- **Error Cases**:
  - If user is being built: `{"success": false, "data": "Building..."}`
  - If user not found: 404 error
  - If username parameter missing: 400 error
  - If xinfo not found: 404 error
  - If server error occurs: 500 error with error message
  - If user has no tweets, personal_brief is "No enough information or still in building..."

### 3. List Users

- **Description**: Get a list of all available users
- **Endpoint**: `/api/list_users`
- **Method**: GET
- **Headers**: 
  - `Authorization: Bearer <token>`
- **Response Example**:

```json
{
  "success": true,
  "data": ["user1", "user2", "user3"] // each one is twitter username (also known as a handle)
}
```

- **Error Cases**:
  - If server error occurs: 500 error with error message

### 4. Get User Profile

- **Description**: Get profile of username
- **Endpoint**: `/api/get_profile`
- **Method**: GET
- **Headers**: 
  - `Authorization: Bearer <token>`
- **Parameters**:
  - `username`: Username (required)
- **Response Example**:

```json
{
  "success": true,
  "data": {
    "profile": {
      // User profile details
    },
    "summary": {
      "detailed_analysis": {},
      "personal_brief": "",
      "long_description": "",
      "personal_tags": {
        "keywords": [
        ]
      }
    }
  }
}
```

- **Error Cases**:
  - If profile is being built: `{"success": false, "data": "building..."}`
  - If user not found: 404 error
  - If username parameter missing: 400 error
  - If server error occurs: 500 error with error message

### 5. Get XInfo

- **Description**: Get twitter information of username
- **Endpoint**: `/api/get_xinfo`
- **Method**: GET
- **Headers**: 
  - `Authorization: Bearer <token>`
- **Parameters**:
  - `username`: Username (required)
- **Response Example**:

```json
{
  "success": true,
  "data": {
    // User information details
    "coverPicture": "https://pbs.twimg.com/profile_banners/44196397/1739948056",
    "createdAt": "Tue Jun 02 20:12:29 +0000 2009",
    "favouritesCount": 141046,
    "followers": 219094983,
    "following": 1106,
    "hasCustomTimelines": true,
    "id": "44196397",
    "isAutomated": false,
    "isBlueVerified": true,
    "isTranslator": false,
    "isVerified": false,
    "location": "",
    "mediaCount": 3775,
    "name": "Elon Musk",
    "pinnedTweetIds": [
        "1911625269003112683"
    ],
    "possiblySensitive": false,
    "profilePicture": "https://pbs.twimg.com/profile_images/1893803697185910784/Na5lOWi5_normal.jpg",
    "status": "",
    "statusesCount": 76951,
    "twitterUrl": "https://twitter.com/elonmusk",
    "type": "user",
    "url": "https://x.com/elonmusk",
    "userName": "elonmusk",
  }
}
```

- **Error Cases**:
  - If user is being built: `{"success": false, "data": "Building..."}`
  - If user info not found: 404 error
  - If username parameter missing: 400 error
  - If server error occurs: 500 error with error message

### 6. Get Conversation History

- **Description**: Get conversation history of username
- **Endpoint**: `/api/get_conversation`
- **Method**: GET
- **Headers**: 
  - `Authorization: Bearer <token>`
- **Parameters**:
  - `username`: Username (required)
  - `conversation_id`: Optional conversation ID (default: ${membase_id}_${username})
  - `recent_n_messages`: Optional number of recent messages to retrieve (default: 128)
- **Response Example**:

```json
{
  "success": true,
  "data": [
    {
      "role": "user",
      "content": "Hello"
    },
    {
      "role": "assistant",
      "content": "Hi there!"
    }
  ]
}
```

- **Error Cases**:
  - If memory not found: 404 error
  - If username parameter missing: 400 error
  - If server error occurs: 500 error with error message

### 7. Generate User Profile

- **Description**: Generate profile for a new username
- **Endpoint**: `/api/generate`
- **Method**: POST
- **Headers**: 
  - `Content-Type: application/json`
  - `Authorization: Bearer <token>`
- **Request Body**:

```json
{
  "username": "username"
}
```

- **Response Example**:

```json
{
  "success": true,
  "data": "start building..." // or "building..." or "already built"
}
```

- **Error Cases**:
  - If username too long (>15 chars): 400 error
  - If missing username: 400 error
  - If server error occurs: 500 error with error message

### 8. Chat Interface

- **Description**: Chat with user personal agent
- **Endpoint**: `/api/chat`
- **Method**: POST
- **Headers**: 
  - `Content-Type: application/json`
  - `Authorization: Bearer <token>`
- **Request Body**:

```json
{
  "username": "username",
  "message": "chat message",
  "conversation_id": "optional, conversation ID"
}
```

- **Response Example**:

```json
{
  "success": true,
  "data": "AI response message"
}
```

- **Error Cases**:
  - If user profile not found: 404 error
  - If missing required fields: 400 error
  - If server error occurs: 500 error with error message

### 9. Set User Status

- **Description**: Set status for a specific user
- **Endpoint**: `/api/set_status`
- **Method**: POST
- **Headers**: 
  - `Content-Type: application/json`
  - `Authorization: Bearer <token>`
- **Request Body**:

```json
{
  "username": "username",
  "key": "status_key",
  "value": "status_value"
}
```

- **Example Status Keys**:
  - `PayingUser`: Boolean value indicating if the user is a paying user
    - `true`: User has paid for premium features
    - `false`: Default value, user is using free features
- **Response Example**:

```json
{
  "success": true,
  "data": {
    "PayingUser": true,
    "other_key": "other_value"
  }
}
```

- **Error Cases**:
  - If user not found: 404 error
  - If missing required fields: 400 error
  - If server error occurs: 500 error with error message

### 10. Get User Status

- **Description**: Get status for a specific user
- **Endpoint**: `/api/get_status`
- **Method**: GET
- **Headers**: 
  - `Authorization: Bearer <token>`
- **Parameters**:
  - `username`: Username (required)
  - `key`: Optional key to get specific status value. If not specified, returns entire status object
- **Response Example**:

```json
// When key is specified
{
  "success": true,
  "data": "status_value"
}

// When key is not specified, all status key/value is returned
{
  "success": true,
  "data": {
    "one_key": "one_value",
    "other_key": "other_value"
  }
}
```

- **Error Cases**:
  - If user not found: 404 error
  - If username parameter missing: 400 error
  - If server error occurs: 500 error with error message

## System Configuration

- Server runs on port 5001 (configurable via `--port` argument)
- Default grpc server URL: "13.212.116.103:8081" (configurable via `GRPC_SERVER_URL` environment variable)
- System prompt can be configured via `SYSTEM_PROMPT` environment variable
- Bearer token can be configured via `BEARER_TOKEN` environment variable or `--bearer-token` argument
- Server runs on all interfaces (0.0.0.0) by default
- Thread pool size is fixed at 4 workers for background tasks
- User profile refresh interval is set to 10 minutes

## Rate Limiting

Currently, there are no explicit rate limits implemented. However, it's recommended to:

- Space out requests appropriately
- Handle 500 errors gracefully
- Implement retry logic with exponential backoff

## Best Practices

1. Error Handling
   - Always check the `success` field in responses
   - Implement proper error handling for all status codes
   - Use appropriate retry mechanisms for transient errors

2. Authentication
   - Store bearer token securely
   - Rotate tokens periodically
   - Never expose tokens in client-side code

3. Profile Generation
   - Handle "Building..." status appropriately
   - Implement polling mechanism for profile status
   - Cache generated profiles when possible

4. Conversation Management
   - Use consistent conversation IDs
   - Implement proper message history management
   - Handle conversation limits appropriately

## Examples

### Python Example

```python
import requests

BASE_URL = "http://localhost:5001"
TOKEN = "your_bearer_token"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# List all users
response = requests.get(f"{BASE_URL}/api/list_users", headers=headers)
users = response.json()["data"]

# Get user info
username = "example_user"
response = requests.get(f"{BASE_URL}/api/get_info?username={username}", headers=headers)
user_info = response.json()["data"]

# Chat with user
chat_data = {
    "username": username,
    "message": "Hello!",
    "conversation_id": "optional_conversation_id"
}
response = requests.post(f"{BASE_URL}/api/chat", headers=headers, json=chat_data)
chat_response = response.json()["data"]
```

### cURL Example

```bash
# List all users
curl -X GET "http://localhost:5001/api/list_users" \
     -H "Authorization: Bearer your_bearer_token"

# Get user info
curl -X GET "http://localhost:5001/api/get_info?username=example_user" \
     -H "Authorization: Bearer your_bearer_token"

# Chat with user
curl -X POST "http://localhost:5001/api/chat" \
     -H "Authorization: Bearer your_bearer_token" \
     -H "Content-Type: application/json" \
     -d '{"username": "example_user", "message": "Hello!"}'
```
