import re, json
path = r'c:\Users\Tejas\Desktop\QPilot\backend\services\pipeline.py'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# Make save_json_data async and add websocket broadcast
from_def = 'def save_json_data(session_id: str, filename: str, data: dict) -> str:'
to_def = 'async def save_json_data(session_id: str, filename: str, data: dict) -> str:'
text = text.replace(from_def, to_def)

from_print = 'print(f"💾 Saved: {file_path}")\n    return file_path'
to_print = """
    try:
        await manager.send_log(session_id, "info", f"JSON_DATA:{json.dumps({'file': filename, 'content': data}, default=str)}")
    except Exception as e:
        print(f"Failed to log: {e}")
    print(f"💾 Saved: {file_path}")
    return file_path
"""
text = text.replace(from_print, to_print)

# Add awaits to save_json_data calls
text = re.sub(r'(?<!def )\bsave_json_data\(', 'await save_json_data(', text)

# Fix verdict being UNKNOWN in blueprint_verify_node
text = text.replace('initial_critique.get("overall_rating", {}).get("verdict", "UNKNOWN")', 'initial_critique.get("verdict", "UNKNOWN")')

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)
print('Done modifying pipeline.py')
