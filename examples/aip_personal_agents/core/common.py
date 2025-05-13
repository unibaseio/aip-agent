from datetime import datetime, timedelta
import json
import os
import shutil
from typing import Dict, List

def is_user_exists(user_name: str) -> bool:
    return os.path.exists(f"outputs/{user_name}")

def init_user(user_name: str):
    if not is_user_exists(user_name):
        os.makedirs(f"outputs", exist_ok=True)
        os.makedirs(f"outputs/{user_name}", exist_ok=True)

def is_user_xinfo_exists(user_name: str) -> bool:
    return os.path.exists(f"outputs/{user_name}/{user_name}_info.json")

def is_user_tweets_exists(user_name: str) -> bool:
    return os.path.exists(f"outputs/{user_name}/{user_name}_tweets.json")

def is_user_tweets_exists_at(user_name: str, date_str: str) -> bool:
    return os.path.exists(f"outputs/{user_name}/{user_name}_tweets_{date_str}.json")

def is_user_profile_exists(user_name: str) -> bool:
    return os.path.exists(f"outputs/{user_name}/{user_name}_profile_final.json")

def is_user_summary_exists(user_name: str) -> bool:
    return os.path.exists(f"outputs/{user_name}/{user_name}_summary.json")

def is_user_airdrop_score_exists(user_name: str) -> bool:
    return os.path.exists(f"outputs/{user_name}/{user_name}_airdrop_score.json")

def is_user_finished(user_name: str) -> bool:
    if is_user_profile_exists(user_name):
        if is_user_summary_exists(user_name):
            if is_user_airdrop_score_exists(user_name):
                return True
    return False

def load_usernames():
    print(f"load usernames")
    unfinished_users = []
    finished_users = []
    for file in os.listdir("outputs"):
        if os.path.isdir(f"outputs/{file}"):
            if is_user_finished(file):
                finished_users.append(file)
            else:
                unfinished_users.append(file)
    unfinished_users.sort()
    finished_users.sort()
    print(f"load unfinished users: {unfinished_users}")
    print(f"load finished users: {finished_users}")
    return finished_users, unfinished_users

def load_user_xinfo(user_name: str) -> dict:
    if is_user_xinfo_exists(user_name):
        with open(f"outputs/{user_name}/{user_name}_info.json", 'r', encoding='utf-8') as f:
            content = f.read()
            # Remove the ```json markers if they exist
            content = content.replace('```json\n', '').replace('\n```', '')
            info =  json.loads(content)
            return info
    return {}

def load_user_tweets(user_name: str) -> list:
    """Load existing tweets from local file if it exists."""
    if is_user_tweets_exists(user_name):
        with open(f"outputs/{user_name}/{user_name}_tweets.json", 'r', encoding='utf-8') as f:
            content = f.read()
            # Remove the ```json markers if they exist
            content = content.replace('```json\n', '').replace('\n```', '')
            tweets = json.loads(content)
            return tweets
    return []

def order_tweets(tweets, reverse=False):
    # parse createdAt string to datetime object for proper sorting
    def parse_date(date_str):
        return datetime.strptime(date_str, "%a %b %d %H:%M:%S %z %Y")
    
    return sorted(tweets, key=lambda x: parse_date(x["createdAt"]), reverse=reverse)

def load_user_tweets_within(user_name: str, days: int):
    tweets = load_user_tweets(user_name)
    
    # filter tweets to get latest 3m 
    three_months_ago = datetime.now().astimezone() - timedelta(days=days)
    recent_tweets = [
        tweet for tweet in tweets 
        if datetime.strptime(tweet["createdAt"], "%a %b %d %H:%M:%S %z %Y") > three_months_ago
    ]
    
    return order_tweets(recent_tweets)

def load_user_profile(user_name: str) -> dict:
    if is_user_profile_exists(user_name):
        with open(f"outputs/{user_name}/{user_name}_profile_final.json", 'r', encoding='utf-8') as f:
            content = f.read()
            # Remove the ```json markers if they exist
            content = content.replace('```json\n', '').replace('\n```', '')
            profile = json.loads(content)
            return profile
    return {}

def load_user_summary(user_name: str) -> dict:
    if is_user_summary_exists(user_name):
        with open(f"outputs/{user_name}/{user_name}_summary.json", 'r', encoding='utf-8') as f:
            content = f.read()
            # Remove the ```json markers if they exist
            content = content.replace('```json\n', '').replace('\n```', '')
            summary = json.loads(content)
            return summary
    return {
        "detailed_analysis": {},
        "personal_brief": "No enough information (no tweets) or still in building...",
        "personal_tags": {
            "keywords": []
        }
    }

def load_user_airdrop_score(user_name: str) -> dict:
    if is_user_airdrop_score_exists(user_name):
        with open(f"outputs/{user_name}/{user_name}_airdrop_score.json", 'r', encoding='utf-8') as f:
            content = f.read()
            # Remove the ```json markers if they exist
            content = content.replace('```json\n', '').replace('\n```', '')
            airdrop_score = json.loads(content)
            # ignore project_score, 75->100
            #total_score = (engagement_score + influence_score + project_score + quality_score
            total_score = (airdrop_score["engagement_score"] + airdrop_score["influence_score"] + airdrop_score["quality_score"]) *4 / 3
            factor = 1.0
            if airdrop_score.get("factor"):
                factor = airdrop_score["factor"]
            if airdrop_score.get("authenticity_factor"):
                factor = airdrop_score["authenticity_factor"]
            
            airdrop_score["total_score"] = round(total_score*factor, 2)
            return airdrop_score
    return {}

def write_user_tweets(user_name: str, tweets: List[Dict]):
    """Save tweets to local file."""
    if len(tweets) == 0:
        return
    # format to day
    date_str = datetime.now().strftime("%Y-%m-%d")
    with open(f"outputs/{user_name}/{user_name}_tweets_{date_str}.json", "w", encoding='utf-8') as f:
        json.dump(tweets, f)
    # copy to outputs/{user_name}.json
    shutil.copy(f"outputs/{user_name}/{user_name}_tweets_{date_str}.json", f"outputs/{user_name}/{user_name}_tweets.json")

def write_user_xinfo(user_name: str, xinfo: dict):
    with open(f"outputs/{user_name}/{user_name}_info.json", 'w', encoding='utf-8') as f:
        f.write(json.dumps(xinfo, ensure_ascii=False))

def write_user_profile(user_name: str, profile: dict):
    with open(f"outputs/{user_name}/{user_name}_profile_final.json", 'w', encoding='utf-8') as f:
        f.write(json.dumps(profile, ensure_ascii=False))

def write_user_summary(user_name: str, summary: dict):
    with open(f"outputs/{user_name}/{user_name}_summary.json", 'w', encoding='utf-8') as f:
        f.write(json.dumps(summary, ensure_ascii=False))

def write_user_airdrop_score(user_name: str, airdrop_score: dict):
    with open(f"outputs/{user_name}/{user_name}_airdrop_score.json", 'w', encoding='utf-8') as f:
        f.write(json.dumps(airdrop_score, ensure_ascii=False))

def remove_user_profile(user_name: str):
    if is_user_profile_exists(user_name):
        os.remove(f"outputs/{user_name}/{user_name}_profile_final.json")

def format_files():
    # Get all files in outputs directory
    files = [f for f in os.listdir("outputs") if os.path.isfile(os.path.join("outputs", f))]
    
    # Find all _tweets.json files and extract usernames
    usernames = set()
    for file in files:
        if file.endswith("_tweets.json"):
            username = file[:-len("_tweets.json")]
            usernames.add(username)
    
    # Create directories and move files for each username
    for username in usernames:
        # Create directory if it doesn't exist
        user_dir = os.path.join("outputs", username)
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)
        
        # Move all files starting with username to the directory
        for file in files:
            if file.startswith(username):
                src = os.path.join("outputs", file)
                dst = os.path.join(user_dir, file)
                print(f"Moving {file} to {username} directory")
                os.rename(src, dst)

def is_user_status_exists(user_name: str) -> bool:
    return os.path.exists(f"outputs/{user_name}/status.json")

def load_user_status(user_name: str) -> dict:
    if is_user_status_exists(user_name):
        with open(f"outputs/{user_name}/status.json", 'r', encoding='utf-8') as f:
            content = f.read()
            # Remove the ```json markers if they exist
            content = content.replace('```json\n', '').replace('\n```', '')
            status = json.loads(content)
            return status
    return {}

def write_user_status(user_name: str, status: dict):
    with open(f"outputs/{user_name}/status.json", 'w', encoding='utf-8') as f:
        f.write(json.dumps(status, ensure_ascii=False))

if __name__ == "__main__":
    format_files()
