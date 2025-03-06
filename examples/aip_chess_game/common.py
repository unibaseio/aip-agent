from pydantic import BaseModel # type: ignore

class Player(BaseModel):
    name: str  # Player name
    type: str  # Player role type: "wolf", "villager", "witch", "seer"
    state: str  # Player state: "alive" or "dead"