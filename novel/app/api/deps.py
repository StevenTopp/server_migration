from fastapi import Request, HTTPException, status
from app.services.user_manager import USERS_FILE, get_users_db # Just for checking, though session is in memory
# Session storage is currently in-memory in server.py.
# In a modular app, we need a place to store sessions.
# For now, let's keep a global variable in this module or a singleton service.

# To avoid circular imports and complex state management in this refactor,
# we will use a simple in-memory dict here.
SESSIONS = {}

async def get_current_user(request: Request):
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = auth.split(" ")[1]
    username = SESSIONS.get(token)

    if not username:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return username
