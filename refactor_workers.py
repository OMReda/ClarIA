import re

# refactor tasks.py
content = open('backend/workers/tasks.py').read()
content = re.sub(r'from backend\.models\.session import Session as SessionModel\n', '', content)
content = re.sub(r'# ── Background jobs ───────────────────────────────────────────────────────────.*', '', content, flags=re.DOTALL)
open('backend/workers/tasks.py', 'w').write(content)

# refactor celery_app.py
content = open('backend/workers/celery_app.py').read()
content = re.sub(r'celery_app\.conf\.beat_schedule = \{.*?\}\n', '', content, flags=re.DOTALL)
open('backend/workers/celery_app.py', 'w').write(content)
