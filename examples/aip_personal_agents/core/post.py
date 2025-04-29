import os
import sys
from typing import Dict, Any

from openai import OpenAI

def load_profile(user_name: str) -> Dict[str, Any]:
    """Load profile from JSON file"""
    import json
    with open(f"outputs/{user_name}_profile_final.json", 'r', encoding='utf-8') as f:
        content = f.read()
        # Remove the ```json markers if they exist
        content = content.replace('```json\n', '').replace('\n```', '')
        return json.loads(content)

def generate_system_prompt(user_name: str) -> str:
    profile = load_profile(user_name)
    """Generate a system prompt based on the profile characteristics"""
    
    def format_profile_markdown(data: Dict[str, Any], indent: int = 0) -> str:
        """Recursively format nested profile data into markdown"""
        lines = []
        # Skip the top level if it doesn't contain basic_profile
        if "basic_profile" not in data and len(data) == 1:
            # Get the first (and only) value
            data = next(iter(data.values()))
            
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{'  ' * indent}### {key}")
                nested_lines = format_profile_markdown(value, indent + 1)
                if nested_lines:
                    lines.append(nested_lines)
            elif isinstance(value, list):
                lines.append(f"{'  ' * indent}#### {key}")
                for item in value:
                    lines.append(f"{'  ' * (indent + 1)}- {item}")
            else:
                lines.append(f"{'  ' * indent}- **{key}**: {value}")
        return "\n".join(lines)
    try:
        profile_markdown = format_profile_markdown(profile)
    except Exception as e:
        print(f"Error formatting profile: {e}")
        profile_markdown = profile
    
    return f"""# Twitter/X Account Profile: {user_name}

## Profile Characteristics

{profile_markdown}

## Instructions

You act as this Twitter/X user **{user_name}**, when you hear about the news, events, topics or opinions:
1. Search similar posts for the news.
2. Decide if you want to comment on this news.
3. If you want to comment, generate three tweet posts.
4. If you don't want to comment, illustrate your thoughts.

## Output Format

The output should be tweets list, each tweet contains the following fields:
- **tweet**: content you want to post or the thought you want to illustrate.
- **reason**: the reason you want to post or illustrate your thoughts.
"""

def generate_tweet(user_name: str, profile: Dict[str, Any]) -> str:
    """Generate a tweet based on the profile characteristics"""
    
    prompt_template = f"""
    You act as a Twitter/X user {user_name} with the following characteristics:
    {profile}


    Generate five tweets when you hear about the following news:
    
    Tesla is going to build second factory in Shanghai
    """

    prompt_template = generate_system_prompt(user_name)
    #prompt_template += "\n\n" + "Generate five tweets when you hear about the following news:"
    
    prompt_template += "\n\n" + "Tesla is going to build second factory in Shanghai"
    
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt_template}]
    )
    return response.choices[0].message.content

def main(user_name: str):
    profile = load_profile(user_name)
    tweet = generate_tweet(user_name, profile)
    print(tweet)

if __name__ == "__main__":
    default_x_name = "elonmusk"
    args = sys.argv[1:]
    if len(args) > 0:
        default_x_name = args[0]
    print(f"Posting for {default_x_name}")
    main(default_x_name)
