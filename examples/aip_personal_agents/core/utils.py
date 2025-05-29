import json
import os
import re
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


def markdown_to_json(result: str) -> dict:
    """
    Convert markdown formatted text to JSON format without using LLM.
    Supports parsing headers, lists, code blocks, and key-value pairs.
    """
    lines = result.strip().split('\n')
    json_data = {}
    current_section = None
    current_list = []
    in_code_block = False
    code_content = []
    code_language = None
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
            
        # Handle code blocks
        if line.startswith('```'):
            if not in_code_block:
                # Starting code block
                in_code_block = True
                code_language = line[3:].strip() if len(line) > 3 else 'text'
                code_content = []
            else:
                # Ending code block
                in_code_block = False
                if current_section:
                    if current_section not in json_data:
                        json_data[current_section] = {}
                    json_data[current_section]['code'] = {
                        'language': code_language,
                        'content': '\n'.join(code_content)
                    }
                else:
                    json_data['code'] = {
                        'language': code_language,
                        'content': '\n'.join(code_content)
                    }
                code_content = []
                code_language = None
            continue
            
        # If inside code block, collect content
        if in_code_block:
            code_content.append(line)
            continue
            
        # Handle headers
        if line.startswith('#'):
            # Save any pending list
            if current_list and current_section:
                if current_section not in json_data:
                    json_data[current_section] = {}
                json_data[current_section]['items'] = current_list
                current_list = []
                
            # Extract header level and text
            header_match = re.match(r'^(#+)\s*(.+)$', line)
            if header_match:
                level = len(header_match.group(1))
                text = header_match.group(2)
                current_section = text.lower().replace(' ', '_')
                
                if current_section not in json_data:
                    json_data[current_section] = {
                        'level': level,
                        'title': text
                    }
            continue
            
        # Handle lists
        if line.startswith(('-', '*', '+')):
            list_item = line[1:].strip()
            current_list.append(list_item)
            continue
            
        # Handle numbered lists
        if re.match(r'^\d+\.\s', line):
            list_item = re.sub(r'^\d+\.\s', '', line)
            current_list.append(list_item)
            continue
            
        # Handle key-value pairs (key: value format)
        if ':' in line and not line.startswith('http'):
            key, value = line.split(':', 1)
            key = key.strip().lower().replace(' ', '_')
            value = value.strip()
            
            if current_section:
                if current_section not in json_data:
                    json_data[current_section] = {}
                json_data[current_section][key] = value
            else:
                json_data[key] = value
            continue
            
        # Handle regular text
        if current_section:
            if current_section not in json_data:
                json_data[current_section] = {}
            if 'content' not in json_data[current_section]:
                json_data[current_section]['content'] = []
            json_data[current_section]['content'].append(line)
        else:
            if 'content' not in json_data:
                json_data['content'] = []
            json_data['content'].append(line)
    
    # Save any remaining list
    if current_list and current_section:
        if current_section not in json_data:
            json_data[current_section] = {}
        json_data[current_section]['items'] = current_list
    
    return json_data


if __name__ == "__main__":
    from core.common import load_report
    report = load_report("2025-05-26", "chinese", "news")
    print(report)
    json_data = markdown_to_json(report)
    print(json_data)