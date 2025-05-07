import json
import os
import sys
from typing import Dict, Any

from openai import OpenAI

from core.post import load_profile

def summarize_profile(user_name: str) -> str:
    profile = load_profile(user_name)
    if profile is None:
        return None
    
    prompt_summary = f"""
    You are a professional social media analyst. 

    Profile Data:
    {profile}

    Based on the above Twitter/X user profile, generate a JSON response with the following structure:

    {{
        "personal_tags": {{
            "keywords": ["AI", "meme", "crypto", "tag4", "tag5"]
        }},
        "personal_brief": "A 3-5 sentence paragraph that accurately reflects their domain, preferences, personality, and distinguishing traits. ",
        "detailed_analysis": {{
            "basic_profile": "Key insights about the user's basic profile",
            "communication_style": "Analysis of how the user communicates",
            ...
        }}
    }}

    Follow these guidelines:

    Requirements:
    1. For Personal Tags:
       - STRICTLY select ONLY from the 'keywords_or_phrases' field in the content_analysis section
       - Choose 5 most significant words/phrases based on frequency and sentiment
       - Merge similar keywords into a single representative tag
       - Format as a simple list of strings

    2. For Personal Summary:
       - Focus on four key aspects in 3-5 sentences:
         1. Personal interests and expertise areas
         2. Frequently discussed topics and themes
         3. Core viewpoints and stances
         4. Distinctive characteristics and sty
       - The tone should be professional and insightful, incorporating subtle stylistic flair only when it aligns with the user's authentic voice. 
       - With a touch of “chuunibyou” flair (e.g., grandiose nicknames like a dragon princess).
       - Avoid exaggerated or unfounded embellishments.

    3. For Detailed Analysis:
       - Each section should be 2-3 sentences

    Special Instructions:
    - Make it feel like a genuine, human observation rather than a formal analysis"
    - Do not use third person pronouns (he, she, they, etc.)
    """

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))    
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt_summary}]
    )
    return response.choices[0].message.content

def summarize(user_name: str):
    print(f"Summarize profile for {user_name}")

    summary = summarize_profile(user_name)
    if summary is None:
        return
    try:
        json.loads(summary)
        with open(f"outputs/{user_name}_summary.json", "w") as f:
            f.write(summary)
    except json.JSONDecodeError as e:
        print(f"Error Summary: Invalid JSON format - {str(e)}")
        raise

if __name__ == "__main__":
    default_x_name = "elonmusk"
    args = sys.argv[1:]
    if len(args) > 0:
        default_x_name = args[0]
    summarize(default_x_name)
