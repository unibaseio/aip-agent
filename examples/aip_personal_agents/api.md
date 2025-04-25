# Personal API Documentation

## Run

```
uv run -m core.api
```

## Basic Information

- Base URL: `http://localhost:5001`
- All responses include a `success` field indicating request status
- All error responses include an `error` field with error description

## API Endpoints

### 1. List Users

- **Endpoint**: `/api/list_users`
- **Method**: GET
- **Description**: Get a list of all available users
- **Response Example**:

```json
{
  "success": true,
  "data": ["user1", "user2", "user3"]
}
```

### 2. Get User Profile

- **Endpoint**: `/api/get_profile`
- **Method**: GET
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
      "persoanl_brief": "",
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

### 3. Generate User Profile

- **Endpoint**: `/api/generate`
- **Method**: POST
- **Headers**: `Content-Type: application/json`
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

### 4. Chat Interface

- **Endpoint**: `/api/chat`
- **Method**: POST
- **Headers**: `Content-Type: application/json`
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

## Error Codes

- 400: Bad Request
- 404: User Not Found
- 415: Unsupported Media Type (Content-Type must be application/json)
- 500: Internal Server Error

## Notes

1. All POST requests must use `application/json` format
2. Username length cannot exceed 50 characters
3. Profile generation is an asynchronous process and may require waiting time
4. Chat interface supports conversation ID, which will be auto-generated if not provided

## System Configuration

- Server runs on port 5001
- Default server URL: "13.212.116.103:8081"
- User profiles are automatically refreshed every 5 minutes
- The system uses an AI agent for chat responses, configured with a custom system prompt
