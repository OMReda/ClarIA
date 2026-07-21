import re

content = open('backend/api/websocket.py').read()

# Add import
if 'decode_and_validate_token' not in content:
    content = content.replace('from fastapi import APIRouter, WebSocket, WebSocketDisconnect', 'from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException\nfrom backend.core.security import decode_and_validate_token')

auth_block = """    # ── Read X-Session-ID from query param or header ──────────────────────────
    session_id_raw = (
        websocket.query_params.get("session_id")
        or websocket.headers.get("x-session-id")
    )
    if not session_id_raw:
        await websocket.close(code=4001, reason="Missing session_id")
        return
    try:
        session_uuid = uuid.UUID(session_id_raw)
    except ValueError:
        await websocket.close(code=4001, reason="Invalid session_id")
        return"""

new_auth_block = """    # ── Read token from query param or header ──────────────────────────
    token = (
        websocket.query_params.get("token")
        or websocket.headers.get("Authorization")
    )
    if token and token.startswith("Bearer "):
        token = token.split(" ", 1)[1]
        
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return
        
    try:
        user = decode_and_validate_token(token)
        user_sub = user.sub
    except HTTPException:
        await websocket.close(code=4001, reason="Invalid token")
        return"""
        
content = content.replace(auth_block, new_auth_block)

content = content.replace('file_record.session_id', 'file_record.owner_id')
content = content.replace('str(session_uuid)', 'user_sub')

open('backend/api/websocket.py', 'w').write(content)
