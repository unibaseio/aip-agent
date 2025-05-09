import json
import os
import sys
from typing import Dict, Any

from openai import OpenAI

from core.common import write_user_summary, load_user_profile

def summarize_profile(user_name: str) -> str:
    profile = load_user_profile(user_name)
    if profile is None or profile == {}:
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
        "personal_brief": "A 1-2 sentence summary that captures their key interests, expertise, and personality traits.",
        "long_description": "A 3-5 sentence detailed description that covers their domain expertise, preferences, personality, and distinguishing characteristics.",
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

    2. For Personal Brief:
       - Write a concise 1-2 sentence summary that captures:
         1. Key interests and expertise areas
         2. Most notable personality traits
         3. The most important thing the user is doing
       - Keep it focused and impactful
       - The tone should be professional and insightful
       - The brief should be concise and to the point

    3. For Long Description:
       - Write a detailed 3-5 sentence description covering:
         1. Personal interests and expertise areas
         2. Frequently discussed topics and themes
         3. Core viewpoints and stances
         4. Distinctive characteristics and style
       - The tone should be professional and insightful, incorporating subtle stylistic flair only when it aligns with the user's authentic voice
       - With a touch of "chuunibyou" flair (e.g., grandiose nicknames like a dragon princess)
       - Avoid exaggerated or unfounded embellishments

    4. For Detailed Analysis:
       - Each section should be 2-3 sentences

    Special Instructions:
    - Make it feel like a genuine, human observation rather than a formal analysis
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
        if not summary or not isinstance(summary, str):
            raise ValueError(f"Invalid summary result: {summary}")
        
        content = summary.replace('```json\n', '').replace('\n```', '')
        summary_dict = json.loads(content)
        write_user_summary(user_name, summary_dict)
        print(f"Successfully summarized profile for {user_name}")
    except json.JSONDecodeError as e:
        print(f"Error Summary: Invalid JSON format - {str(e)}")
        print("Raw content:", summary)
        raise
    except ValueError as e:
        print(f"Error Summary: {str(e)}")
        print("Raw content:", summary)
        raise

if __name__ == "__main__":
    default_x_name = "elonmusk"
    args = sys.argv[1:]
    if len(args) > 0:
        default_x_name = args[0]
    summarize(default_x_name)
