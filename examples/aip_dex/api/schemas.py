from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

# Token related schemas
class TokenResponse(BaseModel):
    name: str
    symbol: str
    contract_address: str
    chain: str
    
    class Config:
        from_attributes = True

# Chat related schemas
class ChatRequest(BaseModel):
    message: str
    include_pools: Optional[bool] = False
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str