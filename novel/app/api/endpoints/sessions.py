from fastapi import APIRouter, Depends, HTTPException
from app.services import session_service
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/sessions")
async def get_sessions(username: str = Depends(get_current_user)):
    sessions = session_service.list_user_sessions(username)
    return {"sessions": sessions}

@router.post("/history")
async def get_history(username: str = Depends(get_current_user)):
    history = session_service.get_session_history(username)
    return {"history": history}

@router.post("/switch_session")
async def switch_session(req: dict, username: str = Depends(get_current_user)):
    filename = req.get("filename")
    if not filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    try:
        path = session_service.switch_user_session(username, filename)
        return {"status": "ok", "path": path}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Session file not found")

@router.post("/new_session")
async def new_session(username: str = Depends(get_current_user)):
    result = session_service.create_new_session(username)
    return {"status": "ok", **result}

@router.post("/switch_file")
async def switch_file(req: dict, username: str = Depends(get_current_user)):
    target_path = req.get("target_path")
    if not target_path:
        raise HTTPException(status_code=400, detail="Missing target_path")

    path = session_service.switch_file_path(username, target_path)
    return {"status": "ok", "path": path}
