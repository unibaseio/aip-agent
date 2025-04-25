import json
import os
from typing import Any, Dict, List

from core.generate import generate_profile
from core.retrieve import retrieve_tweets
from core.summary import summarize
from core.save import save_tweets

def load_unfinished_users() -> Any:
    print(f"load unfinished users")
    users = []
    for file in os.listdir("outputs"):
        if file.endswith(".json"):
            # Remove '_profile_final.json' suffix to get the user name
            if file.endswith("_profile_final.json"):
                continue
            if file.endswith("_summary.json"):
                continue
            user_name = file[:-len(".json")]
            users.append(user_name) 
    return users

def load_user(user_name: str) -> Any:
    print(f"load user: {user_name}")
    with open(f"outputs/{user_name}_profile_final.json", 'r', encoding='utf-8') as f:
        content = f.read()
        # Remove the ```json markers if they exist
        content = content.replace('```json\n', '').replace('\n```', '')
        profile =  json.loads(content)
    if os.path.exists(f"outputs/{user_name}_summary.json"):
        with open(f"outputs/{user_name}_summary.json", 'r', encoding='utf-8') as f:
            content = f.read()
            content = content.replace('```json\n', '').replace('\n```', '')
            summary = json.loads(content)
    else:
        summary = {}
    return {"profile": profile, "summary": summary}

# user dict: name -> summary
def load_users() -> Dict[str, Any]:
    users = {}
    for file in os.listdir("outputs"):
        if file.endswith("_profile_final.json"):
            # Remove '_profile_final.json' suffix to get the user name
            user_name = file[:-len("_profile_final.json")]
            if user_name:  # Ensure we don't add empty names
                users[user_name] = load_user(user_name)
    return users

def build_user(user_name: str):
    print(f"build user: {user_name}")

    # check if profile already exists
    if os.path.exists(f"outputs/{user_name}_summary.json"):
        print(f"Profile for {user_name} already exists")
        return 
    
    # check if tweets need to be retrieved
    if not os.path.exists(f"outputs/{user_name}.json"):
        print(f"Retrieving tweets for {user_name}")
        retrieve_tweets(user_name)
        save_tweets(user_name)
    
    # generate profile if tweets exist
    if not os.path.exists(f"outputs/{user_name}_profile_final.json"):
        print(f"Generating profile for {user_name}")
        generate_profile(user_name)
    
    # after profile is generated, summarize
    if not os.path.exists(f"outputs/{user_name}_summary.json"):
        print(f"Summary profile for {user_name}")
        res = summarize(user_name)
        with open(f"outputs/{user_name}_summary.json", "w") as f:
            f.write(res)