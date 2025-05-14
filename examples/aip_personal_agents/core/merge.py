import glob
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    #base_url="https://api.deepseek.com/v1"
)

model_name = "gpt-4.1-mini"

# combine multiple profiles (oldest to newest) into a single profile
def merge_profiles(merged_text: str):
    print("Merging profiles")
    if not merged_text or not isinstance(merged_text, str):
        raise ValueError("Invalid input: merged_text must be a non-empty string")
        
    # result should be a json object
    # newest to oldest, newest has the highest priority
    prompt = f"""You are a professional profile analyzer. Your task is to merge multiple partial user profile JSONs into a single, comprehensive, and coherent user persona.

Guidelines:
1. Analyze each profile chronologically (newest to oldest)
2. For conflicting information, prioritize the newest data
3. Remove redundant information while preserving unique insights
4. Maintain a consistent JSON structure
5. Ensure all meaningful details are preserved
6. If a field has multiple values, combine them logically
7. Keep the most specific and detailed information

JSON Format Requirements:
1. Output must be a valid JSON object
2. All keys must be enclosed in double quotes
3. All string values must be enclosed in double quotes
4. Use proper JSON escaping for special characters
5. No trailing commas
6. No comments
7. No single quotes
8. No unquoted keys or values
9. Ensure all arrays and objects are properly closed

Input profiles:
==== BEGIN PROFILES ====
{merged_text}
==== END PROFILES ====

Return a single, merged user profile in valid JSON format (no additional text or explanations). The output must be parseable by any standard JSON parser:"""

    
    response = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

if __name__ == "__main__":
    user_name = "elonmusk"
    paths = sorted(glob.glob(f"outputs/{user_name}/{user_name}_profile_batch_*.json"))
    merged_text = "\n\n".join(open(p).read() for p in paths)
    final = merge_profiles(merged_text)
    with open(f"outputs/{user_name}/{user_name}_profile_final.json", "w") as f:
        f.write(final)
