import json
import os
from openai import OpenAI

def fix_json_format(result: str):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    prompt = f"""
    Your task is to fix the JSON format issues in the provided string. 
    Do not change any content, values, or structure of the JSON.
    Only fix syntax errors like missing quotes, commas, brackets, etc.
    Return the corrected JSON string that is valid and parseable.

    Input string:
    {result}
    """
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0
    )
    return response.choices[0].message.content

def convert_to_json(result: str)->dict:
    try:
        result = result.replace("```json\n", "").replace("\n```", "")
        json_result = json.loads(result)
        return json_result
    except Exception as e:
        print(f"Error converting to JSON: {e}")
        print(f"Trying to fix JSON format...")
        try:
            fixed_result = fix_json_format(result)
            fixed_result = fixed_result.replace("```json", "").replace("```", "")
            json_result = json.loads(fixed_result)
            return json_result
        except Exception as e:
            print(f"Error fixing JSON format: {e}")
            raise e

