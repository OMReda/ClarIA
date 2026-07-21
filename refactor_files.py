import re

content = open('backend/api/files.py').read()

# Imports
content = re.sub(r'from backend\.models\.session import Session as SessionModel\n', '', content)
if 'get_current_user' not in content:
    content = content.replace('from backend.core.database import get_async_session', 'from backend.core.database import get_async_session\nfrom backend.core.security import get_current_user, User')

# Auth block replace
auth_block = """    if x_session_id:
        try:
            sid = uuid.UUID(x_session_id)
            if str(file_record.owner_id) != str(sid):
                raise _error("FORBIDDEN", "This file does not belong to your session.", http_status=403)
        except ValueError:
            pass"""
            
new_auth_block = """    if file_record.owner_id != user.sub:
        raise _error("FORBIDDEN", "This file does not belong to you.", http_status=403)"""
        
content = content.replace(auth_block, new_auth_block)

# get_current_session
session_block = """    if not x_session_id:
        return SessionHydrationResponse(files=[], prompts=[])
        
    try:
        sid = uuid.UUID(x_session_id)
    except ValueError:
        return SessionHydrationResponse(files=[], prompts=[])
        
    # Find session files
    result = await db.execute(select(FileModel).where(FileModel.owner_id == sid))"""
    
new_session_block = """    # Find user files
    result = await db.execute(select(FileModel).where(FileModel.owner_id == user.sub))"""
    
content = content.replace(session_block, new_session_block)

# explanation
content = content.replace('"explanation": p.explanation,', '')

open('backend/api/files.py', 'w').write(content)
