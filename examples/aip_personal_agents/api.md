# Personal API Documentation

## Run

```bash
uv run -m core.api --port=5001
```

## Basic Information

- Base URL: `http://localhost:5001`
- All responses include a `success` field indicating request status
- All error responses include an `error` field with error description
- Authentication: All endpoints require Bearer token authentication
  - Add `Authorization: Bearer <token>` header to all requests
  - Default token: "unibase_personal_agent"
  - Can be configured via `BEARER_TOKEN` environment variable or `--bearer-token` argument

## API Endpoints

### 1. List Users

- **Endpoint**: `/api/list_users`
- **Method**: GET
- **Headers**: 
  - `Authorization: Bearer <token>`
- **Description**: Get a list of all available users
- **Response Example**:

```json
{
  "success": true,
  "data": ["user1", "user2", "user3"]
}
```

- **Error Cases**:
  - If server error occurs: 500 error with error message

### 2. Get User Profile

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
      "personal_tags": {
        "keywords": [
          "#Bitcoin",
          "Strategic Reserve",
          "BTC Yield",
          "Trump administration",
          "regulation"
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

### 3. Get User Info

- **Endpoint**: `/api/get_userinfo`
- **Method**: GET
- **Headers**: 
  - `Authorization: Bearer <token>`
- **Parameters**:
  - `username`: Username (required)
- **Description**: Get user information from external source
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
  - If user info not found: 404 error
  - If username parameter missing: 400 error
  - If server error occurs: 500 error with error message

### 4. Generate User Profile

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
  - If username too long (>50 chars): 400 error
  - If missing username: 400 error
  - If server error occurs: 500 error with error message

### 5. Chat Interface

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

## Error Codes

- 400: Bad Request (Invalid JSON format, missing required fields, username too long)
- 401: Unauthorized (Missing Authorization header)
- 403: Forbidden (Invalid bearer token)
- 404: User Not Found
- 415: Unsupported Media Type (Content-Type must be application/json)
- 500: Internal Server Error

## Notes

1. All POST requests must use `application/json` format
2. Username length cannot exceed 50 characters
3. Profile generation is an asynchronous process and may require waiting time
4. Chat interface supports conversation ID, which will be auto-generated if not provided (format: `membase_id_username`)
5. User profiles are automatically refreshed every 5 minutes
6. The server uses a thread pool with 4 workers for handling background tasks

## System Configuration

- Server runs on port 5001 (configurable via `--port` argument)
- Default server URL: "13.212.116.103:8081" (configurable via `SERVER_URL` environment variable)
- System prompt can be configured via `SYSTEM_PROMPT` environment variable
- Bearer token can be configured via `BEARER_TOKEN` environment variable or `--bearer-token` argument
- Server runs on all interfaces (0.0.0.0) by default
