import glob
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    #base_url="https://api.deepseek.com/v1"
)

model_name = "gpt-4o"

# combine multiple profiles (oldest to newest) into a single profile
def merge_profiles(merged_text: str):
    print("Merging profiles")
    # result should be a json object
    # oldest to newest, newest has the highest priority
    prompt = f"""You are a professional profile analyzer. Your task is to merge multiple partial user profile JSONs into a single, comprehensive, and coherent user persona.

Guidelines:
1. Analyze each profile chronologically (oldest to newest)
2. For conflicting information, prioritize the newest data
3. Remove redundant information while preserving unique insights
4. Maintain a consistent JSON structure
5. Ensure all meaningful details are preserved
6. If a field has multiple values, combine them logically
7. Keep the most specific and detailed information

Input profiles:
==== BEGIN ====
{merged_text}
==== END ====

Return a single, merged user profile in JSON format (no additional text or explanations):"""

    
    response = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

if __name__ == "__main__":
    user_name = "elonmusk"
    paths = sorted(glob.glob(f"outputs/{user_name}_profile_batch_*.json"))
    merged_text = "\n\n".join(open(p).read() for p in paths)
    final = merge_profiles(merged_text)
    with open(f"outputs/{user_name}_profile_final.json", "w") as f:
        f.write(final)
