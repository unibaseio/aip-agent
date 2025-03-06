def get_game_prompt(player_role: str) -> str:
    """Get the game prompt for the player role."""  

    prompt = "You are a chess player and you play as: " + player_role + "\n"
    prompt += "You are playing against another player, you need to make the best move to win the game.\n"
    prompt += "You can choose a move from the possible moves.\n"
    prompt += "Please respond with your move in the following format:\n"
    prompt += "thinking: [your detailed thought process]\n"
    prompt += "move: [your move in UCI format (e.g. e2e4, g1f3)]\n"
    prompt += "For example:\n"
    prompt += "thinking: I want to control the center with my pawn\n"
    prompt += "move: e2e4"

    return prompt

def parse_response(response: str) -> tuple[str, str]:
    """Parse the response to extract thinking and move.
    
    Args:
        response: The response string from llm
        
    Returns:
        tuple[str, str]: A tuple containing (thinking, move)
        
    Raises:
        ValueError: If the response format is invalid
    """
    try:
        # 分别寻找thinking和move的内容
        thinking_start = response.find("thinking:") + len("thinking:")
        move_start = response.find("move:") + len("move:")
        
        if thinking_start == -1 or move_start == -1:
            raise ValueError("Invalid response format: missing thinking or move")
            
        # 提取thinking内容（到move:之前）
        thinking = response[thinking_start:response.find("move:")].strip()
        
        # 提取move内容（到结尾）
        move = response[move_start:].strip()
        
        if not thinking or not move:
            raise ValueError("Invalid response format: empty thinking or move")
            
        return thinking, move
        
    except Exception as e:
        raise ValueError(f"Failed to parse response: {str(e)}")