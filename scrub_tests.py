import re
import glob

for f in glob.glob('tests/backend/test_*.py'):
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Remove `session_id: str` from function arguments
    content = re.sub(r',\s*session_id:\s*str', '', content)
    content = re.sub(r'session_id:\s*str,\s*', '', content)
    content = re.sub(r'session_id:\s*str', '', content)
    
    # Remove `session_id` passed to functions like `_upload_csv(client, session_id)`
    content = re.sub(r',\s*session_id', '', content)
    
    # Remove `headers={"X-Session-ID": ...}` in multiline or single line
    content = re.sub(r',\s*headers=\{"X-Session-ID"[^}]+\}', '', content)
    content = re.sub(r'headers=\{"X-Session-ID"[^}]+\},\s*', '', content)
    content = re.sub(r'headers=\{"X-Session-ID"[^}]+\}', '', content)
    
    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)
