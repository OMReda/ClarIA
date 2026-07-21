import re

content = open('backend/api/prompts.py').read()

# Add imports
if 'get_current_user' not in content:
    content = content.replace('from backend.core.database import get_async_session', 'from backend.core.database import get_async_session\nfrom backend.core.security import get_current_user, User')

# Remove _require_session_id
require_session_block = """def _require_session_id(x_session_id: Optional[str]) -> str:
    if not x_session_id:
        raise _error("MISSING_SESSION_ID", "X-Session-ID header is required.", http_status=401)
    try:
        uuid.UUID(x_session_id)
    except ValueError:
        raise _error("INVALID_SESSION_ID", "X-Session-ID must be a valid UUID.")
    return x_session_id"""
content = content.replace(require_session_block, '')

# Replace parameters
content = content.replace('x_session_id: Optional[str] = Header(None),', 'user: User = Depends(get_current_user),')
content = content.replace('session_id = _require_session_id(x_session_id)', '')

# Replace ownership check
content = content.replace('str(file_record.session_id) != session_id', 'str(file_record.owner_id) != str(user.sub)')

# Replace rate limiter param
content = content.replace('check_and_increment(session_id)', 'check_and_increment(user.sub)')

# Remove explanation
content = content.replace('    explanation: Optional[str] = None\n', '')
content = content.replace('        explanation=prompt.explanation,\n', '')

open('backend/api/prompts.py', 'w').write(content)
